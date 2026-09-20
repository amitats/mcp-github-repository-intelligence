import ast
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from models import Dependency, ApiEndpoint, ExternalCall, TestAnalysis, RepositoryFacts
from scanner import detect_languages, repository_structure

NON_CORE = {"tests","test","examples","example","docs","doc","benchmarks","benchmark"}

def read(path):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def rel(path, root):
    return str(path.relative_to(root)).replace("\\","/")

def scope_for(path, root):
    parts={x.lower() for x in path.relative_to(root).parts[:-1]}
    if parts & {"examples","example"}: return "example"
    if parts & {"tests","test"}: return "test"
    if parts & {"docs","doc"}: return "documentation"
    return "core"

def req(item, scope, src):
    s=str(item).split(";")[0].strip()
    m=re.match(r"^\s*([A-Za-z0-9_.@/\-]+)\s*(.*)$", s)
    return Dependency(m.group(1),m.group(2).strip(),scope,src) if m else None

def parse_dependencies(root, files):
    out=[]
    meta={}
    runtime=[]
    for p in files:
        n=p.name.lower()
        s=scope_for(p,root)
        if n=="pyproject.toml":
            try: d=tomllib.loads(read(p))
            except Exception: continue
            pr=d.get("project",{}) or {}
            base="core" if s=="core" else s
            for x in pr.get("dependencies",[]) or []:
                q=req(x,base,rel(p,root))
                if q: out.append(q)
            for group, vals in (pr.get("optional-dependencies",{}) or {}).items():
                sc=f"optional:{group}" if s=="core" else s
                for x in vals or []:
                    q=req(x,sc,rel(p,root))
                    if q: out.append(q)
            if s=="core":
                if pr.get("requires-python"): runtime.append(f"Python {pr['requires-python']}")
                meta.update({
                    "name":pr.get("name",""),
                    "description":pr.get("description",""),
                    "scripts":pr.get("scripts",{}) or {}
                })
        elif n.startswith("requirements") and n.endswith(".txt"):
            sc=s
            if sc=="core" and any(x in n for x in ["dev","test"]): sc="development"
            for line in read(p).splitlines():
                line=line.strip()
                if not line or line.startswith(("#","-","http://","https://","git+")): continue
                q=req(line,sc,rel(p,root))
                if q: out.append(q)
        elif n=="package.json":
            try: d=json.loads(read(p))
            except Exception: continue
            mapping=[("dependencies","core"),("devDependencies","development"),
                     ("peerDependencies","peer"),("optionalDependencies","optional")]
            for key, sc0 in mapping:
                sc=sc0 if s=="core" else s
                for name,ver in (d.get(key,{}) or {}).items():
                    out.append(Dependency(name,str(ver),sc,rel(p,root)))
            if s=="core":
                for k,v in (d.get("engines",{}) or {}).items():
                    runtime.append(f"{k} {v}")
                if not meta:
                    meta={"name":d.get("name",""),"description":d.get("description",""),"scripts":d.get("scripts",{}) or {}}
        elif n=="go.mod" and s=="core":
            text=read(p)
            m=re.search(r"^module\s+(.+)$",text,re.M)
            if m: meta.setdefault("name",m.group(1).strip().split("/")[-1])
            gm=re.search(r"^go\s+([0-9.]+)$",text,re.M)
            if gm: runtime.append(f"Go {gm.group(1)}")
            for name,ver in re.findall(r"^\s*([A-Za-z0-9_.\-/]+)\s+(v[0-9][^\s]*)",text,re.M):
                out.append(Dependency(name,ver,"core",rel(p,root)))
        elif n=="pom.xml":
            try:
                rx=ET.parse(p).getroot()
                ns=rx.tag.split("}")[0]+"}" if rx.tag.startswith("{") else ""
                for dep in rx.findall(f".//{ns}dependency"):
                    g=dep.findtext(f"{ns}groupId","")
                    a=dep.findtext(f"{ns}artifactId","")
                    v=dep.findtext(f"{ns}version","")
                    ds=dep.findtext(f"{ns}scope","core")
                    if a:
                        out.append(Dependency(f"{g}:{a}" if g else a,v,(ds or "core") if s=="core" else s,rel(p,root)))
            except Exception: pass

    seen=set(); clean=[]
    for d in out:
        k=(d.name.lower(),d.current_version,d.scope,d.source_file)
        if k not in seen:
            seen.add(k); clean.append(d)
    groups={}
    for d in clean:
        groups.setdefault(d.scope,[]).append(d)
    for k in groups:
        groups[k].sort(key=lambda x:x.name.lower())
    return groups, sorted(set(runtime)), meta

def core_dep_names(groups):
    out=set()
    for scope,deps in groups.items():
        if scope in {"example","test","documentation","development"}: continue
        out |= {d.name.lower().replace("_","-") for d in deps}
    return out

def technology_stack(root, files, groups, runtime, meta):
    deps=core_dep_names(groups)
    paths={rel(p,root).lower() for p in files}
    names={p.name.lower() for p in files}
    fw=[]
    for dep,label in {
        "flask":"Flask","django":"Django","fastapi":"FastAPI","express":"Express",
        "react":"React","next":"Next.js","@angular/core":"Angular",
        "spring-boot-starter-web":"Spring Boot","github.com/gin-gonic/gin":"Gin","gin-gonic/gin":"Gin"
    }.items():
        if dep in deps: fw.append(label)
    pname=str(meta.get("name","")).lower()
    if pname=="flask": fw.append("Flask")
    if pname=="django": fw.append("Django")

    db=[]
    for dep,label in {"sqlalchemy":"SQLAlchemy","psycopg":"PostgreSQL","psycopg2":"PostgreSQL",
                      "pymongo":"MongoDB","go.mongodb.org/mongo-driver":"MongoDB","redis":"Redis","mysqlclient":"MySQL"}.items():
        if dep in deps: db.append(label)

    cloud=[]
    for dep,label in {"boto3":"AWS","botocore":"AWS","azure-identity":"Azure",
                      "google-cloud-storage":"Google Cloud"}.items():
        if dep in deps: cloud.append(label)

    containers=[]
    if "dockerfile" in names or any(x.endswith("/dockerfile") for x in paths): containers.append("Docker")
    if any("docker-compose" in x or x.endswith(("compose.yaml","compose.yml")) for x in paths): containers.append("Docker Compose")

    iac=[]
    if any(x.endswith(".tf") and not x.startswith(("examples/","tests/","docs/")) for x in paths): iac.append("Terraform")
    if "chart.yaml" in names or any(x.endswith("/chart.yaml") for x in paths): iac.append("Helm")
    if any(("k8s/" in x or "kubernetes/" in x) and x.endswith((".yaml",".yml")) for x in paths): iac.append("Kubernetes")

    cicd=[]
    if any(x.startswith(".github/workflows/") for x in paths): cicd.append("GitHub Actions")
    if "jenkinsfile" in names: cicd.append("Jenkins")
    if ".gitlab-ci.yml" in names: cicd.append("GitLab CI")

    all_deps={d.name.lower() for vals in groups.values() for d in vals}
    testing=[]
    for dep,label in {"pytest":"pytest","pytest-cov":"pytest-cov","jest":"Jest","mocha":"Mocha","testify":"Testify"}.items():
        if any(dep in x for x in all_deps): testing.append(label)

    obs=[]
    for dep,label in {"opentelemetry-api":"OpenTelemetry","opentelemetry-sdk":"OpenTelemetry",
                      "prometheus-client":"Prometheus","github.com/prometheus/client-golang":"Prometheus","sentry-sdk":"Sentry"}.items():
        if dep in deps: obs.append(label)

    return {
        "languages":detect_languages(files),
        "frameworks":sorted(set(fw)),
        "runtime":runtime,
        "databases":sorted(set(db)),
        "cloud_platforms":sorted(set(cloud)),
        "containers":sorted(set(containers)),
        "kubernetes_helm_terraform":sorted(set(iac)),
        "ci_cd":sorted(set(cicd)),
        "testing_tools":sorted(set(testing)),
        "monitoring_observability":sorted(set(obs)),
        "important_core_libraries":sorted(deps)[:80]
    }

def analyze_tests(root,files,groups):
    t=TestAnalysis()
    all_deps={d.name.lower() for vals in groups.values() for d in vals}
    for dep,label in {"pytest":"pytest","pytest-cov":"pytest-cov","jest":"Jest","mocha":"Mocha","github.com/stretchr/testify":"Testify","testify":"Testify"}.items():
        if any(dep in x for x in all_deps): t.frameworks.append(label)
    for p in files:
        r=rel(p,root).lower()
        parts=r.split("/")
        n=p.name.lower()
        if ("tests" in parts or "test" in parts or n.startswith("test_") or
            n.endswith(("_test.py",".test.js",".test.ts",".spec.js",".spec.ts","_test.go"))):
            t.test_files.append(rel(p,root))
    t.test_files=sorted(set(t.test_files))
    if t.test_files: t.test_categories.append("Automated tests detected")
    if any("integration" in x.lower() for x in t.test_files): t.test_categories.append("Integration tests")
    if any("e2e" in x.lower() for x in t.test_files): t.test_categories.append("End-to-end tests")

    for p in files:
        n=p.name.lower()
        if n=="coverage.xml":
            try:
                rate=ET.parse(p).getroot().attrib.get("line-rate")
                if rate is not None:
                    t.coverage_percentage=round(float(rate)*100,2)
                    t.coverage_source=rel(p,root)
                    t.coverage_status="Actual coverage result found"
                    break
            except Exception: pass
        elif n=="coverage.json":
            try:
                data=json.loads(read(p)); pct=data.get("totals",{}).get("percent_covered")
                if pct is not None:
                    t.coverage_percentage=round(float(pct),2)
                    t.coverage_source=rel(p,root)
                    t.coverage_status="Actual coverage result found"
                    break
            except Exception: pass
    return t

def product_source(p,root):
    r=rel(p,root).lower(); parts=set(r.split("/")); name=p.name.lower()
    if scope_for(p,root)!="core": return False
    if parts & {"mocks","mock","fixtures","fixture","testdata","test-data","__mocks__"}: return False
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go") or ".test." in name or ".spec." in name: return False
    return True

def internal_apis(root,files):
    out=[]
    for p in files:
        if not product_source(p,root): continue
        if p.suffix.lower()==".py":
            try: tree=ast.parse(read(p))
            except Exception: continue
            for node in ast.walk(tree):
                if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
                for dec in node.decorator_list:
                    if not isinstance(dec,ast.Call): continue
                    name=""
                    if isinstance(dec.func,ast.Attribute): name=dec.func.attr.lower()
                    if name not in {"get","post","put","delete","patch","route"}: continue
                    endpoint=""
                    if dec.args and isinstance(dec.args[0],ast.Constant) and isinstance(dec.args[0].value,str):
                        endpoint=dec.args[0].value
                    methods=[name.upper()] if name!="route" else ["ROUTE"]
                    for kw in dec.keywords:
                        if kw.arg=="methods" and isinstance(kw.value,(ast.List,ast.Tuple)):
                            methods=[e.value.upper() for e in kw.value.elts if isinstance(e,ast.Constant) and isinstance(e.value,str)]
                    for m in methods:
                        if endpoint: out.append(ApiEndpoint(m,endpoint,node.name,p.stem,rel(p,root)))
        elif p.suffix.lower()==".go":
            text=read(p)
            # Common direct Go routers plus custom routing pipelines using Get/Post/...
            for m in re.finditer(r'\.(GET|POST|PUT|DELETE|PATCH|OPTIONS|Get|Post|Put|Delete|Patch|Options|HandleFunc)\(\s*"([^"]+)"\s*(?:,\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*))?',text):
                raw=m.group(1); method=raw.upper()
                if method=="HANDLEFUNC": method="ROUTE"
                handler=m.group(4) or ""
                out.append(ApiEndpoint(method,m.group(2),handler,p.stem,rel(p,root)))
        elif p.suffix.lower()==".java":
            text=read(p)
            for m in re.finditer(r'@(Get|Post|Put|Delete|Patch)Mapping\(\s*["\']([^"\']+)["\']',text):
                out.append(ApiEndpoint(m.group(1).upper(),m.group(2),"",p.stem,rel(p,root)))
    # Swagger/OpenAPI is authoritative endpoint documentation when present.
    for p in files:
        low=rel(p,root).lower()
        if low.endswith(("swagger/swagger.json","swagger.json","openapi.json")):
            try:
                data=json.loads(read(p))
                for endpoint,ops in (data.get("paths",{}) or {}).items():
                    if not isinstance(ops,dict): continue
                    for method,op in ops.items():
                        if method.upper() not in {"GET","POST","PUT","DELETE","PATCH","OPTIONS","HEAD"}: continue
                        op=op if isinstance(op,dict) else {}
                        handler=str(op.get("operationId","") or "")
                        out.append(ApiEndpoint(method.upper(),endpoint,handler,"swagger",rel(p,root)))
            except Exception:
                pass
    uniq={(x.method,x.endpoint,x.handler,x.source_file):x for x in out}
    return list(uniq.values())

def external_calls(root,files):
    out=[]
    for p in files:
        if not product_source(p,root): continue
        text=read(p)
        if p.suffix.lower()==".py":
            try: tree=ast.parse(text)
            except Exception: continue
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call): continue
                full=""
                if isinstance(node.func,ast.Attribute):
                    if isinstance(node.func.value,ast.Name): full=f"{node.func.value.id}.{node.func.attr}"
                    else: full=node.func.attr
                tech=method=""
                if full.startswith(("requests.","httpx.")):
                    tech=full.split(".")[0]; method=full.split(".")[-1].upper()
                elif full.startswith("boto3."):
                    tech="AWS SDK (boto3)"; method=full.split(".")[-1]
                if tech:
                    target=""
                    if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                        target=node.args[0].value
                    out.append(ExternalCall(p.stem,tech,target,method,rel(p,root),f"Detected {full}"))
        elif p.suffix.lower() in {".js",".ts",".jsx",".tsx"}:
            for m in re.finditer(r'fetch\(\s*["\']([^"\']+)["\']',text):
                out.append(ExternalCall(p.stem,"fetch",m.group(1),"HTTP",rel(p,root),"fetch() call"))
            for m in re.finditer(r'axios\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']',text):
                out.append(ExternalCall(p.stem,"axios",m.group(2),m.group(1).upper(),rel(p,root),"axios call"))
        elif p.suffix.lower()==".go":
            # net/http request construction / client calls
            for m in re.finditer(r'http\.NewRequest(?:WithContext)?\(\s*"([A-Z]+)"\s*,\s*([^,\n]+)',text):
                out.append(ExternalCall(p.stem,"Go net/http",m.group(2).strip(),m.group(1),rel(p,root),"http.NewRequest call"))
            if "github.com/google/go-github" in text or "github.com/github" in text and "Client" in text:
                out.append(ExternalCall(p.stem,"GitHub client library","GitHub API","SDK",rel(p,root),"GitHub client usage detected"))
    uniq={(x.technology,x.target,x.method,x.source_file):x for x in out}
    return list(uniq.values())

def artifacts(root,files):
    result={k:[] for k in ["configuration","docker","kubernetes_helm","terraform","ci_cd","api_specs","documentation"]}
    for p in files:
        r=rel(p,root); low=r.lower(); n=p.name.lower()
        if n in {".env.example",".env.sample","config.yaml","config.yml","application.yaml","application.yml",
                 "application.properties","settings.py"} or "/config/" in f"/{low}/":
            result["configuration"].append(r)
        if n=="dockerfile" or "docker-compose" in low or n in {"compose.yaml","compose.yml"}: result["docker"].append(r)
        if n=="chart.yaml" or "helm/" in low or "charts/" in low or "k8s/" in low or "kubernetes/" in low: result["kubernetes_helm"].append(r)
        if p.suffix.lower()==".tf": result["terraform"].append(r)
        if low.startswith(".github/workflows/") or n in {"jenkinsfile",".gitlab-ci.yml"} or "azure-pipelines" in low: result["ci_cd"].append(r)
        if "openapi" in n or "swagger" in n or n.endswith(".raml"): result["api_specs"].append(r)
        if low.startswith(("docs/","documentation/")) or n.startswith("readme"): result["documentation"].append(r)
    return {k:sorted(set(v))[:120] for k,v in result.items()}

def readme_summary(root,files):
    c=[p for p in files if p.name.lower() in {"readme.md","readme.rst","readme.txt","readme"} and len(p.relative_to(root).parts)==1]
    if not c:return ""
    text=read(c[0]); out=[]; code=False
    for raw in text.splitlines():
        s=raw.strip()
        if s.startswith("```"): code=not code; continue
        if code or not s or s.startswith(("#","![","[!",".. image::")): continue
        s=re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",s)
        s=re.sub(r"[`*_>#]","",s).strip()
        if len(s)>25: out.append(s)
        if sum(map(len,out))>1000: break
    return " ".join(out)[:1200]

def classify(meta,stack,files,root):
    name=str(meta.get("name","")).lower()
    desc=str(meta.get("description","")).lower()
    paths={rel(p,root).lower() for p in files}
    if name in {"flask","django","fastapi"} or any(x in desc for x in ["framework","library","sdk"]):
        return "Framework / Library Repository"
    if any(x.startswith("cmd/") for x in paths) and any(x.startswith("pkg/") or x.startswith("internal/") for x in paths):
        return "Application / Service Repository"
    if stack["kubernetes_helm_terraform"] and not stack["languages"]:
        return "Infrastructure Repository"
    return "Application / Service / Library Repository"

def run_static_analysis(root,files,source,repo_name):
    groups,runtime,meta=parse_dependencies(root,files)
    stack=technology_stack(root,files,groups,runtime,meta)
    return RepositoryFacts(
        source=source,
        source_type="GitHub" if source.startswith(("http://","https://","git@")) else "Local",
        repository_name=repo_name,
        repository_kind=classify(meta,stack,files,root),
        project_description=str(meta.get("description","")),
        file_count=len(files),
        languages=detect_languages(files),
        technology_stack=stack,
        dependencies_by_scope=groups,
        tests=analyze_tests(root,files,groups),
        internal_apis=internal_apis(root,files),
        external_calls=external_calls(root,files),
        artifacts=artifacts(root,files),
        important_files=sorted({
            rel(p,root) for p in files
            if len(p.relative_to(root).parts)==1 and p.name.lower() in {
                "readme.md","readme.rst","pyproject.toml","requirements.txt","package.json",
                "go.mod","pom.xml","dockerfile","chart.yaml",".pre-commit-config.yaml"
            }
        } | {rel(p,root) for p in files if rel(p,root).startswith(".github/workflows/")})[:120],
        repository_structure=repository_structure(root,files),
        readme_summary=readme_summary(root,files)
    )
