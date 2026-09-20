import ast
import json
import re
from collections import defaultdict, Counter, deque
from pathlib import Path
from models import ArchitectureFacts

EXCLUDED={"tests","test","examples","example","docs","doc","benchmarks","benchmark"}

def read(p):
    try:return p.read_text(encoding="utf-8",errors="ignore")
    except Exception:return ""

def rel(p,root):return str(p.relative_to(root)).replace("\\","/")

def core(p,root):
    return not bool(set(rel(p,root).lower().split("/")) & EXCLUDED)

def _module_from_python_path(r):
    x=r
    if x.endswith(".py"): x=x[:-3]
    if x.endswith("/__init__"): x=x[:-9]
    if x.startswith("src/"): x=x[4:]
    return x.replace("/",".")

def python_symbols(root,files):
    modules={}
    classes=[]
    funcs=[]
    internal_imports=[]
    calls=[]
    entry=[]
    module_names=set()
    pyfiles=[p for p in files if p.suffix.lower()==".py" and core(p,root)]
    for p in pyfiles:
        module_names.add(_module_from_python_path(rel(p,root)))

    for p in pyfiles:
        r=rel(p,root); mod=_module_from_python_path(r)
        try:tree=ast.parse(read(p))
        except Exception:continue
        modules[mod]=r
        class_methods=defaultdict(set)
        module_funcs=set()
        for node in tree.body:
            if isinstance(node,ast.ClassDef):
                for c in node.body:
                    if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef)):
                        class_methods[node.name].add(c.name)
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                module_funcs.add(node.name)

        for node in ast.walk(tree):
            if isinstance(node,ast.ClassDef):
                classes.append({"symbol":f"{mod}.{node.name}","name":node.name,"module":mod,"source_file":r})
            elif isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                # find containing class by lineno range
                owner=None
                for c in tree.body:
                    if isinstance(c,ast.ClassDef) and getattr(c,"lineno",0)<=node.lineno<=getattr(c,"end_lineno",10**9):
                        owner=c.name;break
                sym=f"{mod}.{owner+'.' if owner else ''}{node.name}"
                funcs.append({"symbol":sym,"name":node.name,"class":owner or "","module":mod,"source_file":r})
                for child in ast.walk(node):
                    if not isinstance(child,ast.Call):continue
                    target=""
                    if isinstance(child.func,ast.Name):
                        if child.func.id in module_funcs: target=f"{mod}.{child.func.id}"
                    elif isinstance(child.func,ast.Attribute):
                        if isinstance(child.func.value,ast.Name) and child.func.value.id in {"self","cls"} and owner:
                            if child.func.attr in class_methods.get(owner,set()):
                                target=f"{mod}.{owner}.{child.func.attr}"
                    if target:
                        calls.append({"from":sym,"to":target,"source_file":r})
            elif isinstance(node,ast.Import):
                for a in node.names:
                    internal_imports.append((mod,a.name))
            elif isinstance(node,ast.ImportFrom):
                if node.module: internal_imports.append((mod,node.module))

        txt=read(p)
        if p.name in {"__main__.py","main.py","app.py","server.py"} or 'if __name__ == "__main__"' in txt or "if __name__ == '__main__'" in txt:
            entry.append({"type":"Python executable entry point","symbol":mod,"source_file":r})

    # resolve local imports loosely
    resolved=[]
    for a,b in internal_imports:
        for m in module_names:
            if b==m or m.startswith(b+".") or b.startswith(m+"."):
                resolved.append({"from":a,"to":m})
                break
    return {
        "modules":modules,"classes":classes[:200],"functions":funcs[:300],
        "module_relationships":resolved[:250],"call_edges":calls[:250],"entry_points":entry[:40]
    }

def go_symbols(root,files):
    packages=defaultdict(list); imports=[]; funcs=[]; entry=[]; calls=[]
    gofiles=[p for p in files if p.suffix.lower()==".go" and core(p,root) and not ({x.lower() for x in p.relative_to(root).parts} & {"test","tests","mock","mocks","fixtures","examples","testdata"}) and not p.name.lower().endswith("_test.go")]
    repo_module=""
    gomod=next((p for p in files if p.name=="go.mod" and len(p.relative_to(root).parts)==1),None)
    if gomod:
        m=re.search(r"^module\s+(.+)$",read(gomod),re.M)
        if m:repo_module=m.group(1).strip()

    for p in gofiles:
        r=rel(p,root); txt=read(p)
        pm=re.search(r"^\s*package\s+(\w+)",txt,re.M)
        pkg=pm.group(1) if pm else "unknown"
        dirkey=str(Path(r).parent).replace("\\","/")
        packages[dirkey].append(r)
        for impblock in re.findall(r'import\s*\((.*?)\)',txt,re.S):
            for im in re.findall(r'"([^"]+)"',impblock):
                if repo_module and im.startswith(repo_module):
                    target=im[len(repo_module):].lstrip("/") or "."
                    imports.append({"from":dirkey,"to":target})
        for im in re.findall(r'import\s+"([^"]+)"',txt):
            if repo_module and im.startswith(repo_module):
                target=im[len(repo_module):].lstrip("/") or "."
                imports.append({"from":dirkey,"to":target})
        for fm in re.finditer(r'func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\(',txt):
            name=fm.group(1); sym=f"{dirkey}:{name}"
            funcs.append({"symbol":sym,"name":name,"package":dirkey,"source_file":r})
        if pkg=="main" and re.search(r'\bfunc\s+main\s*\(',txt):
            entry.append({"type":"Go executable entry point","symbol":f"{dirkey}:main","source_file":r})
    # package-level relationship is more reliable than regex function call graph for generic Go
    uniq={(x["from"],x["to"]):x for x in imports}
    return {
        "packages":dict(packages),"functions":funcs[:300],
        "package_relationships":list(uniq.values())[:300],"call_edges":calls,
        "entry_points":entry[:50],"module_path":repo_module
    }

def js_symbols(root,files):
    entry=[]; modules=[]; imports=[]
    package_jsons=[p for p in files if p.name.lower()=="package.json" and core(p,root)]
    for p in package_jsons:
        try:d=json.loads(read(p))
        except Exception:continue
        base=str(p.parent.relative_to(root)).replace("\\","/")
        if base==".":base=""
        for k in ["main","module","browser"]:
            if d.get(k):
                entry.append({"type":f"Node package {k}","symbol":str(d[k]),"source_file":rel(p,root)})
        for name,cmd in (d.get("scripts",{}) or {}).items():
            if name in {"start","serve","dev"}:
                entry.append({"type":f"npm script: {name}","symbol":cmd,"source_file":rel(p,root)})
    for p in files:
        if p.suffix.lower() not in {".js",".jsx",".ts",".tsx"} or not core(p,root):continue
        r=rel(p,root);modules.append(r)
        txt=read(p)
        for m in re.finditer(r'(?:from\s+|require\()\s*["\']([^"\']+)["\']',txt):
            target=m.group(1)
            if target.startswith("."):
                imports.append({"from":r,"to":target})
    return {"modules":modules[:250],"module_relationships":imports[:250],"entry_points":entry[:40]}

def structural_components(root,files,py,go,js):
    top=Counter()
    for p in files:
        if not core(p,root):continue
        r=p.relative_to(root)
        if len(r.parts)>1:top[r.parts[0]]+=1

    components=[]
    for name,count in top.most_common(15):
        purpose=[]
        lname=name.lower()
        if lname=="cmd":purpose.append("Executable command entry points")
        if lname in {"src","lib"}:purpose.append("Primary source implementation")
        if lname=="pkg":purpose.append("Reusable application/library packages")
        if lname=="internal":purpose.append("Internal implementation packages")
        if lname=="api":purpose.append("API layer")
        if lname in {"ui","web","frontend"}:purpose.append("User interface / web frontend")
        if lname in {"config","configs"}:purpose.append("Configuration")
        if lname in {"scripts","tools"}:purpose.append("Build/operational tooling")
        components.append({
            "name":name,
            "responsibility":"; ".join(purpose) if purpose else "Top-level source/component area; semantic responsibility refined by local LLM",
            "evidence":[f"{count} analyzed core files under {name}/"]
        })

    # Python package module as component for src/pkg layout
    py_groups=Counter()
    for mod,r in py.get("modules",{}).items():
        parts=r.split("/")
        if parts and parts[0]=="src" and len(parts)>1:py_groups[parts[1]]+=1
    for name,count in py_groups.items():
        if not any(c["name"]==name for c in components):
            components.append({"name":name,"responsibility":"Primary Python package","evidence":[f"{count} Python modules"]})
    return components[:20]

def architecture_style(repo_kind,components,py,go,js):
    names={c["name"].lower() for c in components}
    if "Framework / Library" in repo_kind:
        return "Modular framework / library architecture"
    if go.get("entry_points") and ({"pkg","internal"} & names):
        return "Modular service / CLI architecture with executable entry points and reusable packages"
    if {"ui","web","frontend"} & names and ({"cmd","server","api","pkg","internal"} & names):
        return "Multi-component application architecture with frontend and backend/service components"
    if py.get("entry_points"):
        return "Modular Python application architecture"
    if js.get("entry_points"):
        return "Modular JavaScript/TypeScript application architecture"
    return "Modular repository architecture"

def _production_arch_node(name):
    low=str(name or "").lower().replace("\\","/")
    parts=set(low.split("/"))
    if parts & {"test","tests","mock","mocks","fixtures","fixture","examples","example","testdata"}: return False
    if low.endswith("_test.go") or ".test." in low or ".spec." in low: return False
    return True

def relationships(py,go,js):
    out=[]
    for x in py.get("module_relationships",[])[:80]:
        if _production_arch_node(x["from"]) and _production_arch_node(x["to"]): out.append({"from":x["from"],"to":x["to"],"relationship":"imports/depends on"})
    for x in go.get("package_relationships",[])[:100]:
        if _production_arch_node(x["from"]) and _production_arch_node(x["to"]): out.append({"from":x["from"],"to":x["to"],"relationship":"imports/depends on"})
    for x in js.get("module_relationships",[])[:50]:
        if _production_arch_node(x["from"]) and _production_arch_node(x["to"]): out.append({"from":x["from"],"to":x["to"],"relationship":"imports/depends on"})
    return out[:150]

def derive_flows(py,go,js,relationships):
    flows=[]
    # Python method call chains: build from nodes with outgoing edges and no incoming, capped.
    edges=py.get("call_edges",[])
    if edges:
        adj=defaultdict(list); incoming=Counter()
        for e in edges:
            adj[e["from"]].append(e["to"]);incoming[e["to"]]+=1
        roots=[n for n in adj if incoming[n]==0]
        for root in roots[:4]:
            chain=[root];seen={root};cur=root
            for _ in range(8):
                nxt=next((x for x in adj.get(cur,[]) if x not in seen),None)
                if not nxt:break
                chain.append(nxt);seen.add(nxt);cur=nxt
            if len(chain)>=2:
                flows.append({
                    "name":f"Python control flow from {root.split('.')[-1]}",
                    "entry_point":root,
                    "steps":chain,
                    "evidence":["Static AST self/local function call graph"]
                })
    # Go package flow from executable package through import graph.
    rels=go.get("package_relationships",[])
    if go.get("entry_points") and rels:
        adj=defaultdict(list)
        for e in rels:adj[e["from"]].append(e["to"])
        for ep in go["entry_points"][:4]:
            pkg=ep["symbol"].split(":")[0]
            steps=[pkg]
            q=deque([(pkg,0)]);seen={pkg}
            while q and len(steps)<10:
                cur,depth=q.popleft()
                if depth>=3:continue
                for nxt in adj.get(cur,[])[:4]:
                    if nxt not in seen:
                        seen.add(nxt);steps.append(nxt);q.append((nxt,depth+1))
            flows.append({
                "name":f"Go execution/package flow from {pkg}",
                "entry_point":ep["source_file"],
                "steps":steps,
                "evidence":["Static Go package import graph"]
            })
    # JS entry -> module relationships structural
    if js.get("entry_points"):
        for ep in js["entry_points"][:3]:
            flows.append({
                "name":f"JavaScript/TypeScript entry flow: {ep['type']}",
                "entry_point":ep["symbol"],
                "steps":[ep["symbol"],"Application modules/components"],
                "evidence":[ep["source_file"]]
            })
    return flows[:8]

def analyze_architecture(root,files,repo_kind,artifacts):
    py=python_symbols(root,files)
    go=go_symbols(root,files)
    js=js_symbols(root,files)
    comps=structural_components(root,files,py,go,js)
    rels=relationships(py,go,js)
    flows=derive_flows(py,go,js,rels)
    entries=py.get("entry_points",[])+go.get("entry_points",[])+js.get("entry_points",[])
    style=architecture_style(repo_kind,comps,py,go,js)

    config_files=artifacts.get("configuration",[])
    if config_files:
        config_model=f"Repository contains explicit configuration artifacts: {', '.join(config_files[:12])}."
    else:
        config_model="Configuration is primarily code/package-metadata driven; no dedicated configuration files were conclusively detected."

    deploy=[]
    if artifacts.get("docker"):deploy.append("Docker")
    if artifacts.get("kubernetes_helm"):deploy.append("Kubernetes/Helm")
    if artifacts.get("terraform"):deploy.append("Terraform-managed infrastructure")
    deployment=", ".join(deploy) if deploy else "No repository-owned deployment model was conclusively detected."

    extension=[]
    # generic extension evidence
    for c in py.get("classes",[]):
        if c["name"].lower() in {"blueprint","plugin","extension","middleware","provider"}:
            extension.append(c["symbol"])
    for p in files:
        r=rel(p,root).lower()
        if core(p,root) and any(x in r for x in ["plugin","extension","middleware","provider","toolset"]):
            extension.append(rel(p,root))
    extension=sorted(set(extension))[:25]

    data_flow=[]
    if entries:
        data_flow.append("Execution begins at the detected repository entry point(s): " + ", ".join(x["source_file"] for x in entries[:8]) + ".")
    if rels:
        data_flow.append("Entry modules/packages delegate work through repository-local imports and package dependencies.")
    if flows:
        data_flow.append("Static call/import analysis identified concrete execution paths shown in Detailed Code Flows below.")
    if artifacts.get("configuration"):
        data_flow.append("Configuration artifacts influence component initialization and runtime behavior.")
    data_flow.append("Core components process requests/commands/events through repository modules and return results to the caller or downstream integration.")
    if not entries:
        data_flow.insert(0,"No single executable entry point was found; this repository is likely consumed as a library/framework or exposes multiple integration entry points.")

    explanation=(
        f"The repository follows a {style.lower()}. "
        f"Static analysis identified {len(comps)} major structural component areas, "
        f"{len(entries)} executable/package entry points, and {len(rels)} repository-local dependency relationships. "
        "The architecture below is generated from source layout, imports, symbols, package metadata and executable entry points; "
        "the local LLM is used only to explain these facts in repository-specific language."
    )

    layers=[]
    for c in comps:
        layers.append({"name":c["name"],"description":c["responsibility"],"evidence":c["evidence"]})

    return ArchitectureFacts(
        architecture_style=style,
        architecture_explanation=explanation,
        layers_modules=layers,
        entry_points=entries[:30],
        major_components=comps,
        component_relationships=rels,
        configuration_model=config_model,
        extension_points=extension,
        deployment_model=deployment,
        data_control_flow=data_flow,
        detailed_code_flows=flows,
        evidence=[
            f"Python modules analyzed: {len(py.get('modules',{}))}",
            f"Go packages analyzed: {len(go.get('packages',{}))}",
            f"JS/TS modules analyzed: {len(js.get('modules',[]))}",
            f"Repository-local relationships detected: {len(rels)}"
        ]
    ), {"python":py,"go":go,"javascript_typescript":js}
