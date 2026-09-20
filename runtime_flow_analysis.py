"""Compact production runtime evidence extractor used by the detailed code-flow LLM pass.

Goal: make the LLM explain already-proven runtime facts instead of reading tens of
thousands of characters of raw source. The extractor is intentionally conservative.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

PROD_EXCLUDE = {"test","tests","mock","mocks","fixture","fixtures","example","examples","testdata","vendor","node_modules","generated"}
HTTP_METHODS = {"Get":"GET","Post":"POST","Put":"PUT","Patch":"PATCH","Delete":"DELETE","Options":"OPTIONS","Head":"HEAD",
                "GET":"GET","POST":"POST","PUT":"PUT","PATCH":"PATCH","DELETE":"DELETE","OPTIONS":"OPTIONS","HEAD":"HEAD"}


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def production_file(path: Path, root: Path) -> bool:
    r = rel(path, root).lower()
    parts = set(r.split("/"))
    name = path.name.lower()
    if parts & PROD_EXCLUDE:
        return False
    if name.endswith("_test.go") or name.startswith("test_") or ".test." in name or ".spec." in name:
        return False
    return True


def _balanced_body(text: str, brace_pos: int) -> tuple[str, int]:
    depth = 0
    in_str = False
    quote = ""
    esc = False
    for i in range(brace_pos, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
            continue
        if ch in {'"', "'", '`'}:
            in_str = True; quote = ch; continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace_pos+1:i], i+1
    return text[brace_pos+1:], len(text)


def _find_go_func_open(text: str, start: int) -> int:
    """Find the function body opening brace, skipping braces used by interface{} in return types."""
    paren = 0
    in_str = False
    quote = ""
    esc = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == quote: in_str = False
            i += 1; continue
        if ch in {'"', "'", '`'}:
            in_str = True; quote = ch; i += 1; continue
        if ch == '(': paren += 1
        elif ch == ')': paren = max(0, paren-1)
        elif ch == '{' and paren == 0:
            # interface{} / struct{} may appear in the return type. Skip an empty brace pair.
            j = i + 1
            while j < len(text) and text[j].isspace(): j += 1
            if j < len(text) and text[j] == '}':
                i = j + 1; continue
            return i
        i += 1
    return -1


def _go_functions(root: Path, files: list[Path]) -> dict[str, dict[str, Any]]:
    funcs: dict[str, dict[str, Any]] = {}
    # Locate function declarations first; determine body brace with a small scanner so interface{} return types work.
    head = re.compile(r'func\s*(?:\(\s*([^)]*?)\s*\)\s*)?([A-Za-z_]\w*)\s*\(', re.S)
    for p in files:
        if p.suffix.lower() != ".go" or not production_file(p, root):
            continue
        text = read(p); r = rel(p, root)
        pm = re.search(r'^\s*package\s+(\w+)', text, re.M); pkg = pm.group(1) if pm else p.parent.name
        for m in head.finditer(text):
            receiver_raw, name = m.group(1), m.group(2)
            brace = _find_go_func_open(text, m.end())
            if brace < 0: continue
            body, body_end = _balanced_body(text, brace)
            # Avoid consuming a later function due to malformed match.
            sig = text[m.start():brace].strip().replace("\n", " ")
            if len(sig) > 1200: continue
            receiver = ""
            if receiver_raw:
                bits = receiver_raw.replace("*", " ").split()
                if len(bits) >= 2: receiver = bits[-1]
            symbol = f"{receiver}.{name}" if receiver else name
            key = f"{r}:{symbol}"
            funcs[key] = {"file":r,"package":pkg,"receiver":receiver,"name":name,"symbol":symbol,
                          "signature":re.sub(r'\s+', ' ', sig),"body":body}
    return funcs

def _calls_from_body(body: str) -> list[str]:
    calls=[]
    # object.Method(...) / package.Function(...)
    for m in re.finditer(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(', body):
        calls.append(f"{m.group(1)}.{m.group(2)}")
    # local function calls
    for m in re.finditer(r'(?<!\.)\b([A-Za-z_]\w*)\s*\(', body):
        name=m.group(1)
        if name not in {"if","for","switch","return","go","defer","make","new","append","len","cap","copy","delete","panic","recover","print","println"}:
            calls.append(name)
    # stable unique
    out=[]; seen=set()
    for x in calls:
        if x not in seen:
            seen.add(x); out.append(x)
    return out[:80]


def _go_routes(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    """Resolve Gin/custom RoutingPipeline groups + routes + handler references."""
    routes=[]
    for p in files:
        if p.suffix.lower() != ".go" or not production_file(p, root): continue
        text=read(p); r=rel(p,root)
        # Map function parameter names to group prefixes when caller supplies NewRoutingPipeline(engine.Group("prefix"))
        group_by_register={}
        for m in re.finditer(r'(register[A-Za-z0-9_]+)\s*\(\s*pipeline\.NewRoutingPipeline\(\s*engine\.Group\(\s*"([^"]*)"\s*\)\s*\)', text):
            group_by_register[m.group(1)] = m.group(2)
        # Extract each register* function body and route calls.
        for fm in re.finditer(r'func\s+(register[A-Za-z0-9_]+)\s*\([^)]*\)\s*\{', text):
            fname=fm.group(1); body,_=_balanced_body(text,fm.end()-1); prefix=group_by_register.get(fname,"")
            for rm in re.finditer(r'\b(?:routingPipeline|rp)\.(Get|Post|Put|Patch|Delete|Options|Head|GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s*\(\s*"([^"]+)"\s*,\s*([A-Za-z_]\w*)\.([A-Za-z_]\w*)', body):
                method=HTTP_METHODS.get(rm.group(1),rm.group(1).upper()); path=rm.group(2)
                full=(prefix.rstrip("/")+"/"+path.lstrip("/")) if prefix else path
                if not full.startswith("/"): full="/"+full
                routes.append({"method":method,"path":full,"handler_object":rm.group(3),"handler":rm.group(4),"source_file":r,"register_function":fname})
        # direct Gin routes as fallback
        for rm in re.finditer(r'\.(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\(\s*"([^"]+)"\s*,\s*([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))?',text):
            routes.append({"method":rm.group(1),"path":rm.group(2),"handler_object":rm.group(3),"handler":rm.group(4) or rm.group(3),"source_file":r,"register_function":""})
    uniq={}
    for x in routes:
        uniq[(x["method"],x["path"],x["handler"])]=x
    return list(uniq.values())


def _swagger_routes(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    for p in files:
        low=rel(p,root).lower()
        if low.endswith(("swagger/swagger.json","swagger.json","openapi.json")):
            try:
                d=json.loads(read(p)); out=[]
                for path, ops in (d.get("paths",{}) or {}).items():
                    if not isinstance(ops,dict): continue
                    for method,op in ops.items():
                        if method.upper() not in {"GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"}: continue
                        op=op if isinstance(op,dict) else {}
                        out.append({"method":method.upper(),"path":path,"summary":op.get("summary","") or str(op.get("description",""))[:220],
                                    "operation_id":op.get("operationId",""),"source_file":rel(p,root)})
                return out[:120]
            except Exception: pass
    return []


def _important_calls(function: dict[str, Any]) -> list[str]:
    body=function.get("body","")
    return _calls_from_body(body)


def _function_matches(funcs: dict[str,dict[str,Any]], method_name: str, layer: str = "") -> list[dict[str,Any]]:
    vals=[v for v in funcs.values() if v["name"]==method_name]
    if layer:
        vals.sort(key=lambda v: (0 if f"/{layer}/" in f"/{v['file'].lower()}" else 1, len(v["file"])))
    return vals


def _pick_function(funcs: dict[str,dict[str,Any]], method: str, layer: str, receiver_hint: str = ""):
    vals=_function_matches(funcs, method, layer)
    if receiver_hint:
        hint=receiver_hint.lower()
        vals.sort(key=lambda v: (0 if hint in v.get("receiver","").lower() else 1,
                                 0 if f"/{layer}/" in f"/{v['file'].lower()}" else 1,
                                 len(v["file"])))
    return vals[0] if vals else None


def _call_records(body: str) -> list[dict[str,str]]:
    out=[]; seen=set()
    for m in re.finditer(r'\b([A-Za-z_]\w*)\.([A-Za-z_]\w*)\s*\(', body):
        rec={"receiver":m.group(1),"method":m.group(2),"call":f"{m.group(1)}.{m.group(2)}"}
        key=rec["call"]
        if key not in seen: seen.add(key); out.append(rec)
    return out


def _layer_for_receiver(receiver: str) -> tuple[str,str]:
    low=receiver.lower()
    if "service" in low or "usecase" in low: return "usecase","Service"
    if "repo" in low or "repository" in low: return "repository","Repo"
    if low in {"dal","dao"} or "dal" in low or "dao" in low: return "dal","DAL"
    return "",""


def _brief_conditions(body: str, limit=10) -> list[str]:
    rows=[]
    for line in body.splitlines():
        st=line.strip()
        if st.startswith("if ") or st.startswith("switch ") or st.startswith("case "):
            st=re.sub(r'\s+', ' ', st)
            if len(st)>220: st=st[:217]+"..."
            if st not in rows: rows.append(st)
            if len(rows)>=limit: break
    return rows


def _resolve_layer_chain(funcs: dict[str,dict[str,Any]], handler: str) -> dict[str,Any]:
    """Build ordered handler -> usecase/service -> repository -> DAL -> DB evidence."""
    chain=[]; validations=[]; branches=[]; dbops=[]; helpers=[]
    hf=_pick_function(funcs,handler,"handler","Handler")
    if hf:
        calls=_call_records(hf["body"])
        chain.append({"layer":"handler","file":hf["file"],"symbol":hf["symbol"],"calls":[x["call"] for x in calls[:30]]})
        validations.extend(_brief_conditions(hf["body"],8))
        # Same-handler helpers like validateCreateTimelineEvent / parseGetTimelineEvent.
        for c in calls:
            if c["receiver"].lower() in {"mh","sh","rh","h","handler"} and (c["method"].lower().startswith(("validate","parse","bind"))):
                helper=_pick_function(funcs,c["method"],"handler","Handler")
                if helper:
                    helpers.append({"file":helper["file"],"symbol":helper["symbol"],"conditions":_brief_conditions(helper["body"],8)})
                    validations.extend(_brief_conditions(helper["body"],8))
        # Find the principal service/usecase call from handler.
        service_call=next((c for c in calls if "service" in c["receiver"].lower() or "usecase" in c["receiver"].lower()),None)
    else:
        service_call=None

    sf=None
    if service_call:
        sf=_pick_function(funcs,service_call["method"],"usecase","Service") or _pick_function(funcs,service_call["method"],"service","Service")
    if sf:
        scalls=_call_records(sf["body"])
        chain.append({"layer":"usecase/service","file":sf["file"],"symbol":sf["symbol"],"calls":[x["call"] for x in scalls[:35]]})
        validations.extend(_brief_conditions(sf["body"],10))
        branches.extend([x for x in _brief_conditions(sf["body"],10) if x.startswith(("switch ","case "))])
        # Follow repository calls in the order they appear. Include multiple repos for read/archive flows.
        repo_calls=[c for c in scalls if "repo" in c["receiver"].lower() or "repository" in c["receiver"].lower()]
        # Expand one same-service helper because archive/orchestration methods often delegate
        # their persistence work to a private helper such as performArchiveTimelineEvents.
        for hc in [c for c in scalls if c["receiver"].lower() in {"ms","s","svc","service"}][:4]:
            helper=_pick_function(funcs,hc["method"],"usecase","Service") or _pick_function(funcs,hc["method"],"service","Service")
            if helper and helper["symbol"] != sf["symbol"]:
                hcalls=_call_records(helper["body"])
                chain.append({"layer":"usecase/service helper","file":helper["file"],"symbol":helper["symbol"],"calls":[x["call"] for x in hcalls[:35]]})
                validations.extend(_brief_conditions(helper["body"],8))
                repo_calls.extend([c for c in hcalls if "repo" in c["receiver"].lower() or "repository" in c["receiver"].lower()])
        for rc in repo_calls[:8]:
            rf=_pick_function(funcs,rc["method"],"repository","Repo")
            if not rf: continue
            rcalls=_call_records(rf["body"])
            chain.append({"layer":"repository","file":rf["file"],"symbol":rf["symbol"],"calls":[x["call"] for x in rcalls[:28]]})
            # Follow explicit DAL call(s).
            for dc in [c for c in rcalls if c["receiver"].lower() in {"dal","dao"} or "dal" in c["receiver"].lower()][:4]:
                df=_pick_function(funcs,dc["method"],"dal","DAL")
                if not df: continue
                dcalls=_call_records(df["body"])
                chain.append({"layer":"dal","file":df["file"],"symbol":df["symbol"],"calls":[x["call"] for x in dcalls[:22]]})
                for c in dcalls:
                    if c["method"] in {"Find","FindOne","InsertOne","UpdateOne","DeleteOne","BulkWrite","CountDocuments","Ping","Connect","Decode"}:
                        dbops.append(c["call"])
    # If route itself is health/metrics and service chain is shallow, handler may directly call dependencies.
    if hf and not sf:
        for c in _call_records(hf["body"]):
            layer,hint=_layer_for_receiver(c["receiver"])
            if layer:
                ff=_pick_function(funcs,c["method"],layer,hint)
                if ff:
                    chain.append({"layer":layer,"file":ff["file"],"symbol":ff["symbol"],"calls":_calls_from_body(ff["body"])[:25]})

    # Stable de-duplicate chain entries.
    uniq=[]; seen=set()
    for x in chain:
        k=(x["file"],x["symbol"])
        if k not in seen: seen.add(k); uniq.append(x)
    vals=[]
    for x in validations:
        if x not in vals: vals.append(x)
    return {"chain":uniq[:18],"validations":vals[:14],"branches":branches[:8],"helper_validations":helpers[:5],"database_operations":list(dict.fromkeys(dbops))[:12]}

def _startup(funcs: dict[str,dict[str,Any]]) -> list[dict[str,Any]]:
    # main and Run provide the highest-value startup evidence.
    out=[]
    for target in ("main","Run"):
        for f in _function_matches(funcs,target,("cmd/main.go","cmd/app/"))[:2]:
            out.append({"file":f["file"],"symbol":f["symbol"],"calls":_important_calls(f)[:60]})
    return out


def _shutdown_evidence(funcs: dict[str,dict[str,Any]]) -> list[dict[str,Any]]:
    out=[]
    for f in funcs.values():
        b=f["body"]
        if "signal.Notify" in b or ".Shutdown(" in b or "SIGTERM" in b:
            out.append({"file":f["file"],"symbol":f["symbol"],"signals":re.findall(r'syscall\.(SIG[A-Z]+)',b),
                        "calls":[x for x in _important_calls(f) if "Shutdown" in x or "signal.Notify" in x or "WithTimeout" in x][:10]})
    return out[:6]



def _lifecycle_evidence(funcs: dict[str,dict[str,Any]]) -> list[dict[str,Any]]:
    names={"ConnectDB","NewHTTPServer","RegisterHandlersAndMiddleware","registerMiddleware","Run","Shutdown"}
    out=[]
    for f in funcs.values():
        if f["name"] not in names: continue
        low=f["file"].lower()
        if not any(x in low for x in ("cmd/","server/","handler/","service/","dal/connection")): continue
        out.append({"file":f["file"],"symbol":f["symbol"],"calls":_important_calls(f)[:45],"conditions":_brief_conditions(f["body"],8)})
    order={"ConnectDB":1,"NewHTTPServer":2,"RegisterHandlersAndMiddleware":3,"registerMiddleware":4,"Run":5,"Shutdown":6}
    out.sort(key=lambda x:(order.get(x["symbol"].split(".")[-1],99),x["file"]))
    return out[:20]

def build_runtime_evidence(root: Path, files: list[Path], facts) -> dict[str,Any]:
    funcs=_go_functions(root,files)
    routes=_go_routes(root,files)
    swagger=_swagger_routes(root,files)

    # Merge Swagger summaries into source routes without using docs as runtime implementation.
    swagger_map={(x["method"],x["path"]):x for x in swagger}
    flow_families=[]
    for route in routes:
        if route["method"] == "OPTIONS": continue
        sf=swagger_map.get((route["method"],route["path"]),{})
        flow=_resolve_layer_chain(funcs,route["handler"])
        flow_families.append({**route,"summary":sf.get("summary",""),"operation_id":sf.get("operation_id",""),**flow})

    # Include Swagger-only endpoint facts if source-route resolver couldn't match them.
    route_keys={(x["method"],x["path"]) for x in flow_families}
    for x in swagger:
        if (x["method"],x["path"]) not in route_keys:
            flow_families.append({**x,"handler":"","handler_object":"","register_function":"","chain":[],"validations":[],"branches":[],"database_operations":[]})

    return {
        "repository":facts.repository_name,
        "runtime_entry_points":facts.architecture_facts.entry_points[:10],
        "startup":_startup(funcs),
        "lifecycle":_lifecycle_evidence(funcs),
        "configuration_files":facts.artifacts.get("configuration",[])[:12],
        "routes":flow_families[:60],
        "shutdown":_shutdown_evidence(funcs),
        "deployment_model":facts.architecture_facts.deployment_model,
        "databases":facts.technology_stack.get("databases",[]),
        "frameworks":facts.technology_stack.get("frameworks",[]),
        "observability":facts.technology_stack.get("monitoring_observability",[]),
        "external_calls":[{"caller":x.caller,"technology":x.technology,"target":x.target,"method":x.method,"source_file":x.source_file,"evidence":x.evidence} for x in facts.external_calls[:30]],
    }


def enrich_facts_from_runtime(root: Path, files: list[Path], facts):
    """Reconcile report facts with stronger runtime extraction without changing report schema."""
    from models import ApiEndpoint
    ev=build_runtime_evidence(root,files,facts)
    routes=[]
    for x in ev.get("routes",[]):
        method=x.get("method",""); path=x.get("path","")
        if not method or not path or method=="OPTIONS": continue
        routes.append(ApiEndpoint(method,path,x.get("handler","") or x.get("operation_id","") or "",
                                  "HTTP route",x.get("source_file","") or "swagger/swagger.json"))
    if routes:
        uniq={(x.method,x.endpoint,x.handler):x for x in routes}
        facts.internal_apis=list(uniq.values())
    # Cross-section consistency.
    facts.tests.frameworks=sorted(set(facts.tests.frameworks))
    for label in facts.technology_stack.get("testing_tools",[]):
        if label not in facts.tests.frameworks: facts.tests.frameworks.append(label)
    facts.tests.frameworks=sorted(set(facts.tests.frameworks))
    return ev


def runtime_fallback_flow(evidence: dict[str,Any]) -> list[dict[str,Any]]:
    """Detailed deterministic fallback from the compact runtime model."""
    steps=[]
    entries=evidence.get("runtime_entry_points",[]) or []
    startup=evidence.get("startup",[]) or []
    if startup:
        first=startup[0]
        steps.append({"step":1,"group":"Application Startup Flow","title":"Start the application",
                      "explanation":f"Execution starts in {first.get('file')} at {first.get('symbol')}. The startup function then delegates into the application bootstrap code shown below.",
                      "code":[f"{first.get('file')}:{first.get('symbol')}"]+first.get('calls',[])[:8],
                      "result":"Control moves into application initialization.","evidence":[first.get('file',"")]})
    if evidence.get("configuration_files"):
        steps.append({"step":len(steps)+1,"group":"Application Startup Flow","title":"Load runtime configuration",
                      "explanation":"The application uses the detected configuration files during startup. Configuration values control later runtime initialization; values not proven from source are not guessed.",
                      "code":evidence.get("configuration_files",[])[:10],"result":"Validated runtime settings are available to the bootstrap code.","evidence":evidence.get("configuration_files",[])[:10]})
    if len(startup)>1:
        run=startup[1]
        calls=run.get("calls",[])
        steps.append({"step":len(steps)+1,"group":"Application Startup Flow","title":"Build application dependencies and start the server",
                      "explanation":"The main bootstrap creates the runtime dependencies in code order. The detected calls include logging/metrics setup, database/client connection, repository/use-case/handler construction, HTTP server creation and service start where present.",
                      "code":[f"{run.get('file')}:{run.get('symbol')}"]+calls[:22],"result":"The service is initialized and ready to receive runtime work.","evidence":[run.get('file',"")]})

    for route in evidence.get("routes",[]):
        method=route.get("method",""); path=route.get("path",""); handler=route.get("handler","")
        if not method or not path or method=="OPTIONS": continue
        group_title=(route.get("summary") or handler or path).strip()
        chain=route.get("chain",[]) or []
        chain_symbols=[f"{x.get('file')}:{x.get('symbol')}" for x in chain]
        validations=route.get("validations",[])[:5]
        dbops=route.get("database_operations",[])[:8]
        explanation=f"A {method} request to `{path}` is routed to `{handler or 'the documented operation'}`."
        if chain:
            explanation += " Production control then follows the proven handler/service/repository/data-access chain in the code list below."
        if validations:
            explanation += " The handler or business layer validates request/business conditions before continuing."
        if dbops:
            explanation += " The flow reaches the detected database operations: " + ", ".join(f"`{x}`" for x in dbops) + "."
        steps.append({"step":len(steps)+1,"group":f"{group_title} Flow","title":f"Process {method} {path}","explanation":explanation,
                      "code":[f"{method} {path}"]+chain_symbols[:16],"result":"The processed result returns through the application layers to the HTTP response path.",
                      "evidence":[route.get("source_file","")]+[x.get("file","") for x in chain[:8]]})

    if evidence.get("shutdown"):
        sd=evidence["shutdown"][0]
        steps.append({"step":len(steps)+1,"group":"Application Shutdown Flow","title":"Gracefully stop the service",
                      "explanation":"The application waits for the detected operating-system termination signals and invokes the graceful shutdown path so active work can finish before process exit.",
                      "code":[f"{sd.get('file')}:{sd.get('symbol')}"]+sd.get("signals",[])+sd.get("calls",[]),"result":"The HTTP service shuts down and the application exits.","evidence":[sd.get("file","")]})
    overview={"step":0,"title":"Flow overview","explanation":"The repository runtime starts from its executable entry point, loads configuration and infrastructure dependencies, registers production routes, and starts the service. Each request then follows the statically resolved handler -> use case/service -> repository -> DAL/client path where such a chain is proven. Persistence operations are shown only when directly detected in source. The service closes through its graceful shutdown path when one is present.","code":[],"result":"The detailed ordered flow starts below.","evidence":["Deterministic production runtime extraction"]}
    return [overview]+steps[:40]
