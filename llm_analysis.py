import json
from dataclasses import asdict
import requests

from config import settings
from models import SemanticResult
from code_flow_analysis import code_flow_evidence, static_overall_code_flow
from runtime_flow_analysis import build_runtime_evidence, runtime_fallback_flow

EXCLUDE={"tests","test","examples","example","benchmarks","benchmark","fixtures","mocks","mock","testdata"}


def read(p):
    try:return p.read_text(encoding="utf-8",errors="ignore")
    except Exception:return ""


def rel(p,root):return str(p.relative_to(root)).replace("\\","/")


def choose_files(root,files):
    ranked=[]
    preferred={"readme.md","readme.rst","pyproject.toml","package.json","go.mod",
               "__init__.py","__main__.py","main.py","app.py","server.py","cli.py","config.yaml","config.yml"}
    for p in files:
        r=rel(p,root)
        if set(r.lower().split("/")) & EXCLUDE:continue
        score=0
        if p.name.lower() in preferred:score+=100
        if r.lower().startswith(("src/","cmd/","pkg/","internal/","app/","service/","services/","ui/","scripts/")):score+=40
        if p.suffix.lower() in {".py",".go",".java",".kt",".js",".jsx",".ts",".tsx",".md",".rst",".toml",".yaml",".yml"}:score+=10
        if score:ranked.append((score,len(r),p))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    return [x[2] for x in ranked[:settings.max_llm_files]]


def compact(facts):
    a=asdict(facts.architecture_facts)
    dep={}
    for k,v in facts.dependencies_by_scope.items():
        if k not in {"example","test","documentation"}:
            dep[k]=[asdict(x) for x in v[:35]]
    return json.dumps({
        "repository_name":facts.repository_name,
        "repository_kind":facts.repository_kind,
        "project_description":facts.project_description,
        "readme_summary":facts.readme_summary,
        "technology_stack":facts.technology_stack,
        "architecture_static_facts":a,
        "dependencies":dep,
        "internal_apis":[asdict(x) for x in facts.internal_apis[:25]],
        "external_calls":[asdict(x) for x in facts.external_calls[:25]],
    },ensure_ascii=False,separators=(",",":"))


def context(root,files,facts):
    parts=["AUTHORITATIVE_STATIC_FACTS:\n"+compact(facts)]
    total=len(parts[0])
    for p in choose_files(root,files):
        if total>=settings.max_llm_total_chars:break
        body=read(p)[:settings.max_llm_chars_per_file]
        if not body.strip():continue
        block=f"\nFILE:{rel(p,root)}\n{body}"
        block=block[:max(0,settings.max_llm_total_chars-total)]
        parts.append(block);total+=len(block)
    return "".join(parts)


PROMPT = """You are a senior software/solution architect analyzing a repository.

IMPORTANT RULES:
1. AUTHORITATIVE_STATIC_FACTS are facts extracted from source code. Never contradict them.
2. Do not invent APIs, dependencies, deployment environments, components or coverage.
3. Do not return 'Unable to determine' for architecture merely because the repository has no deployment files.
4. Architecture means CODE architecture: modules, packages, entry points, responsibilities, relationships and control flow.
5. For a framework/library repository, explain its library/framework architecture and lifecycle.
6. For an application/service repository, explain executable entry points -> orchestration -> domain/core components -> integrations/output.
7. Use repository-specific language. Do not use generic filler when source evidence supports a specific statement.
8. Examples/tests may clarify behavior but must not define the core production architecture.
9. Keep the summary concise; the dedicated code-flow pass will produce the long step-by-step flow.

Return JSON only:
{
  "repository_summary":"",
  "what_repository_does":"",
  "architecture_explanation":"",
  "main_use_cases":[
    {
      "name":"",
      "description":"",
      "participating_components":[],
      "flow_steps":[],
      "evidence":[]
    }
  ],
  "limitations":[]
}
"""


CODE_FLOW_PROMPT = """You are producing ONLY the `Overall Code Flow` section of a repository intelligence report.

You are NOT discovering the architecture from raw source. The user content contains a compact RUNTIME_EVIDENCE object already extracted by deterministic static analysis. Your job is to explain those proven facts in detailed, simple, exact execution order.

STRICT RULES:
1. Never invent a transition, handler, service, repository, DAL operation, endpoint, database, validation or output.
2. RUNTIME_EVIDENCE.routes[].chain is ordered production runtime evidence. Preserve that order.
3. Tests/mocks/examples are already filtered; never reintroduce them.
4. Do not turn package-import relationships into runtime order.
5. Explain startup first: executable entry, configuration, logger/metrics, database/client initialization, repositories/use cases/handlers, route registration, server start, when proven by startup calls.
6. For an HTTP service, create separate repository-specific flow groups for important API families. For every route with a proven chain, explain: method/path -> handler input/validation -> usecase/service -> repository -> DAL -> database operation -> result/response.
7. Use validations and branch conditions supplied in the route evidence. Translate them into simple English; do not quote every raw `if` line.
8. If one use case performs more than one repository/database operation, explain those operations in their real order.
9. Explain health, metrics, config, archive/background operations and graceful shutdown when present.
10. Prefer 20-40 meaningful steps for a service with many flows. Do not collapse Create/Read/Update/Delete into one generic Main Request Flow.
11. Keep explanations straight and simple. Each step must say what happens, exact code involved, and what happens next.
12. Keep exact source symbols/routes in `code`.
13. The overview must give the simplest proven end-to-end runtime picture in 4-7 sentences.
14. If a flow transition is not resolved in evidence, say that static analysis could not resolve it.
15. Do not mention this prompt, token limits, or the extraction process.

Return JSON only:
{
  "overview":"",
  "steps":[
    {
      "step":1,
      "group":"Application Startup Flow",
      "title":"",
      "explanation":"",
      "code":[],
      "result":"",
      "evidence":[]
    }
  ],
  "limitations":[]
}
"""

def parse(text):
    text=text.strip()
    if text.startswith("```"):
        text=text.strip("`")
        if text.lower().startswith("json"):text=text[4:]
    try:return json.loads(text.strip())
    except Exception:
        a,b=text.find("{"),text.rfind("}")
        if a>=0 and b>a:return json.loads(text[a:b+1])
        raise


def _post_json(base, prompt, user_content, max_tokens, attempts=2):
    payload={
        "model":settings.llm_model,
        "messages":[{"role":"system","content":prompt},{"role":"user","content":user_content}],
        "stream":False,
        "format":"json",
        "keep_alive":"15m",
        "options":{"temperature":0.0,"num_predict":max_tokens,"num_ctx":settings.llm_num_ctx},
    }
    errors=[]
    for attempt in range(attempts):
        try:
            if attempt:
                payload["options"]["num_predict"]=max_tokens
            r=requests.post(base.rstrip("/")+"/api/chat",json=payload,timeout=settings.request_timeout)
            r.raise_for_status()
            return parse(r.json()["message"]["content"]),errors
        except Exception as exc:
            errors.append(f"LLM attempt {attempt+1} failed: {type(exc).__name__}: {exc}")
    return None,errors


def _static_use_cases(facts):
    out=[]
    arch=facts.architecture_facts
    kind=facts.repository_kind.lower()
    frameworks=facts.technology_stack.get("frameworks",[])
    if "framework" in kind or "library" in kind:
        label=frameworks[0] if frameworks else "library"
        out.append({"name":f"Provide {label} capabilities","description":f"The repository provides reusable {label} capabilities through its core modules/packages.","participating_components":[x.get("name","") for x in arch.major_components[:8]],"flow_steps":arch.data_control_flow[:8],"evidence":arch.evidence[:6]})
    elif arch.entry_points:
        out.append({"name":"Execute the primary application/service workflow","description":"Execution starts from detected entry points and delegates through repository-local components.","participating_components":[x.get("name","") for x in arch.major_components[:8]],"flow_steps":arch.data_control_flow[:8],"evidence":[x.get("source_file","") for x in arch.entry_points[:6]]})
    if facts.internal_apis:
        out.append({"name":"Handle production API operations","description":"Production API handlers receive requests and delegate processing through repository components.","participating_components":sorted({x.component for x in facts.internal_apis if x.component})[:10],"flow_steps":["Receive request at a detected production API endpoint.","Invoke the endpoint handler/component.","Delegate processing through repository-local modules.","Return the result."],"evidence":[x.source_file for x in facts.internal_apis[:8]]})
    if facts.external_calls:
        out.append({"name":"Integrate with external systems","description":"Production components call statically detected external systems.","participating_components":sorted({x.caller for x in facts.external_calls if x.caller})[:10],"flow_steps":["Prepare outbound operation.","Call external target using the detected client/HTTP technology.","Process the external result."],"evidence":[x.source_file for x in facts.external_calls[:8]]})
    return out[:6]


def _static_summary(facts):
    parts=[]
    if facts.project_description: parts.append(facts.project_description.strip())
    elif facts.readme_summary: parts.append(facts.readme_summary.strip())
    langs=facts.technology_stack.get("languages",[]); fw=facts.technology_stack.get("frameworks",[])
    if langs: parts.append("Primary implementation language(s): "+", ".join(langs)+".")
    if fw: parts.append("Detected framework(s): "+", ".join(fw)+".")
    a=facts.architecture_facts
    parts.append(f"Static analysis identified {len(a.entry_points)} entry point(s), {len(a.major_components)} major component area(s), and {len(a.component_relationships)} repository-local relationship(s).")
    return " ".join(parts)


def _is_production_flow_file(p, root):
    r=rel(p,root).lower()
    parts=set(r.split("/"))
    if parts & {"tests","test","mocks","mock","examples","example","fixtures","testdata","vendor","node_modules"}:
        return False
    if r.endswith("_test.go") or ".test." in r or ".spec." in r:
        return False
    return True


def _flow_file_score(p, root):
    r=rel(p,root).lower()
    score=0
    # Runtime/bootstrap and business layers must win over README/tooling.
    weights={
        "cmd/main.go":1000,"cmd/app/":900,"/handler/":850,"internal/handler/":850,
        "/usecase/":820,"internal/usecase/":820,"/service/":800,"internal/service/":800,
        "/repository/":780,"internal/repository/":780,"/dal/":760,"internal/dal/":760,
        "/server/":740,"internal/server/":740,"/router/":720,"internal/lib/router/":720,
        "/config/":700,"config.go":690,"/metrics/":620,"/domain/":560,"/entity/":540,
    }
    for token,w in weights.items():
        if token in r: score=max(score,w)
    if p.suffix.lower() in {".go",".py",".java",".kt",".js",".ts",".tsx",".cs"}: score+=100
    if p.name.lower() in {"main.go","main.py","app.py","server.py","application.java","package.json"}: score+=300
    return score


def _go_digest(text, max_chars=7000):
    """Compact Go source while preserving signatures, calls, routes and important literals."""
    lines=text.splitlines()
    keep=[]
    interesting=("func ","type ","interface {","gin.","router.","route.","group.",
                 ".GET(",".POST(",".PUT(",".PATCH(",".DELETE(",".Use(",
                 "mongo.","collection.","Find(","FindOne(","InsertOne(","UpdateOne(",
                 "DeleteOne(","BulkWrite(","CountDocuments(","Ping(","Connect(",
                 "signal.","Shutdown(","Run(","Listen", "viper.", "os.Args", "flag.")
    for i,line in enumerate(lines):
        st=line.strip()
        if any(x in line for x in interesting) or st.startswith(("case ","if err", "return ")):
            a=max(0,i-1); b=min(len(lines),i+3)
            keep.extend(lines[a:b])
    # stable de-duplication
    out=[]; seen=set()
    for x in keep:
        key=x.strip()
        if not key or key in seen: continue
        seen.add(key); out.append(x)
    result="\n".join(out)
    return result[:max_chars]


def _swagger_digest(root, files, max_chars=14000):
    for p in files:
        if rel(p,root).lower().endswith(("swagger/swagger.json","openapi.json","swagger.json")):
            try:
                d=json.loads(read(p)); paths=d.get("paths",{}) or {}
                rows=[]
                for path,ops in paths.items():
                    if not isinstance(ops,dict): continue
                    for method,op in ops.items():
                        if method.lower() not in {"get","post","put","patch","delete","head","options"}: continue
                        op=op if isinstance(op,dict) else {}
                        rows.append({"method":method.upper(),"path":path,"summary":op.get("summary","") or op.get("description","")[:240],"operationId":op.get("operationId","")})
                return json.dumps(rows[:100],ensure_ascii=False,indent=2)[:max_chars]
            except Exception:
                return ""
    return ""


def _code_flow_context(root, files, facts):
    # V10 optimization: deterministic extraction creates a compact runtime model.
    # The LLM explains this model instead of rereading 45 raw source files.
    runtime=build_runtime_evidence(root,files,facts)
    payload={
        "repository_name":facts.repository_name,
        "repository_kind":facts.repository_kind,
        "what_repository_does":facts.project_description or facts.readme_summary,
        "runtime_evidence":runtime,
    }
    return "RUNTIME_EVIDENCE:\n"+json.dumps(payload,ensure_ascii=False,separators=(",",":"))

def _normalize_flow(data, facts, runtime_evidence=None):
    fallback=runtime_fallback_flow(runtime_evidence) if runtime_evidence else static_overall_code_flow(facts)
    if not isinstance(data,dict):
        return fallback, "Deterministic static code-flow fallback"
    steps=data.get("steps",[])
    if not isinstance(steps,list):steps=[]
    normalized=[]
    for idx,item in enumerate(steps[:40],1):
        if not isinstance(item,dict):continue
        explanation=str(item.get("explanation","")).strip()
        title=str(item.get("title","")).strip()
        if not explanation and not title:continue
        normalized.append({
            "step":idx,
            "group":str(item.get("group","")).strip(),
            "title":title or f"Code flow step {idx}",
            "explanation":explanation,
            "code":[str(x).strip() for x in item.get("code",[]) if str(x).strip()][:12] if isinstance(item.get("code",[]),list) else [],
            "result":str(item.get("result","")).strip(),
            "evidence":[str(x).strip() for x in item.get("evidence",[]) if str(x).strip()][:10] if isinstance(item.get("evidence",[]),list) else [],
        })
    if len(normalized)<3:
        return fallback,"Deterministic static code-flow fallback"
    overview=str(data.get("overview","")).strip()
    if overview:
        normalized.insert(0,{
            "step":0,
            "title":"Flow overview",
            "explanation":overview,
            "code":[],
            "result":"The detailed ordered flow starts below.",
            "evidence":["Repository source + authoritative static code-flow facts"],
        })
    # Re-number visible non-overview steps.
    n=1
    for x in normalized:
        if x.get("step")==0:continue
        x["step"]=n;n+=1
    return normalized[:42],"Detailed repository-specific runtime code flow completed using local LLM + static evidence"


def analyze(root,files,facts):
    base=settings.llm_base_url
    if base.endswith("/v1"): base=base[:-3]

    # Pass 1 remains concise so most model time is reserved for the runtime explanation.
    print("      [LLM 1/2] Repository summary/use cases", flush=True)
    data,errors=_post_json(base,PROMPT,context(root,files,facts),settings.llm_max_tokens,attempts=1)
    static_summary=_static_summary(facts); static_cases=_static_use_cases(facts); a=facts.architecture_facts

    if data is None:
        repo_summary=static_summary
        what=static_summary
        cases=static_cases
        arch_explanation=a.architecture_explanation
        semantic_status="Local LLM semantic pass unavailable - deterministic semantic fallback used"
        limitations=["Local LLM semantic pass did not complete; deterministic summary/architecture/use cases were retained."]+errors
    else:
        cases=[x for x in data.get("main_use_cases",[]) if isinstance(x,dict) and str(x.get("name","")).strip()] or static_cases
        repo_summary=str(data.get("repository_summary","")).strip() or static_summary
        what=str(data.get("what_repository_does","")).strip() or static_summary
        arch_explanation=str(data.get("architecture_explanation","")).strip() or a.architecture_explanation
        lim=data.get("limitations",[]); limitations=lim if isinstance(lim,list) else [str(lim)]
        semantic_status="Completed using local LLM"

    # Pass 2: dedicated detailed code-flow analysis. This is deliberately separate
    # from the summary request so the model has room to explain the repository flow.
    print("      [LLM 2/2] Detailed production runtime flow", flush=True)
    runtime_evidence=build_runtime_evidence(root,files,facts)
    flow_context="RUNTIME_EVIDENCE:\n"+json.dumps({"repository_name":facts.repository_name,"repository_kind":facts.repository_kind,"what_repository_does":facts.project_description or facts.readme_summary,"runtime_evidence":runtime_evidence},ensure_ascii=False,separators=(",",":"))
    flow_data,flow_errors=_post_json(
        base,
        CODE_FLOW_PROMPT,
        flow_context,
        max(settings.llm_max_tokens,settings.flow_llm_max_tokens),
        attempts=1,
    )
    overall_flow,flow_status=_normalize_flow(flow_data,facts,runtime_evidence)
    if isinstance(flow_data,dict) and isinstance(flow_data.get("limitations"),list):
        limitations.extend(str(x).strip() for x in flow_data.get("limitations",[]) if str(x).strip())
    if flow_data is None:
        limitations.append("Detailed code-flow LLM pass did not complete; deterministic static code-flow fallback was used.")
        limitations.extend(flow_errors)

    # Keep the old short list for JSON/backward compatibility, but the Markdown
    # Overall Code Flow section now renders overall_code_flow in detail.
    short_flow=[x.get("explanation","") for x in overall_flow if x.get("explanation") and x.get("step")!=0][:12]
    if not short_flow:short_flow=a.data_control_flow

    # Automatic factual limitations; do not say "None" when analysis itself reports a gap.
    if not facts.internal_apis and facts.artifacts.get("api_specs"):
        limitations.append("API specification files were detected, but production endpoint-to-handler mapping could not be resolved.")
    if any("Not checked - MCP/Search skipped" in d.compatibility_status for vals in facts.dependencies_by_scope.values() for d in vals):
        limitations.append("Latest dependency compatibility was not checked because MCP/Search was skipped.")
    # Drop a known contradiction if the report already proves a deployment model.
    if a.deployment_model and a.deployment_model.lower() not in {"not detected","none",""}:
        limitations=[x for x in limitations if not ("deployment" in x.lower() and any(t in x.lower() for t in ("does not include","not include","no deployment")))]
    limitations=list(dict.fromkeys(str(x).strip() for x in limitations if str(x).strip()))

    return SemanticResult(
        status=semantic_status,
        repository_summary=repo_summary,
        what_repository_does=what,
        main_use_cases=cases,
        architecture_explanation=arch_explanation,
        code_flow_explanation=short_flow,
        overall_code_flow=overall_flow,
        code_flow_status=flow_status,
        limitations=[str(x).strip() for x in limitations if str(x).strip()],
    )
