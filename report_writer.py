import json
from dataclasses import asdict
from pathlib import Path

def table(headers,rows):
    if not rows:return "_Not detected._"
    out=["| "+" | ".join(headers)+" |","| "+" | ".join(["---"]*len(headers))+" |"]
    for row in rows:
        out.append("| "+" | ".join(str(x if x not in [None,""] else "Not available").replace("|","\\|").replace("\n"," ") for x in row)+" |")
    return "\n".join(out)

def doc(f,s):
    a=asdict(f.architecture_facts)
    return {
        "01_repository_summary":{
            "title":"Repository Summary","source":f.source,"source_type":f.source_type,
            "repository_name":f.repository_name,"repository_type":f.repository_kind,
            "what_repository_does":s.what_repository_does,
            "repository_summary":s.repository_summary,
            "local_llm_status":s.status
        },
        "02_technology_stack":{"title":"Technology Stack",**f.technology_stack},
        "03_repository_scan_and_artifacts":{
            "title":"Repository Scan and Engineering Artifacts",
            "files_analyzed":f.file_count,"important_files":f.important_files,
            "artifacts":f.artifacts,"repository_structure":f.repository_structure
        },
        "04_main_components_and_code_structure":{
            "title":"Main Components and Code Structure",
            "major_components":a["major_components"],
            "layers_modules":a["layers_modules"],
            "entry_points":a["entry_points"],
            "relationships":a["component_relationships"],
            "symbols":f.symbols
        },
        "05_code_architecture":{
            "title":"Detailed Code Architecture",
            "architecture_style":a["architecture_style"],
            "architecture_explanation":s.architecture_explanation or a["architecture_explanation"],
            "layers_modules":a["layers_modules"],
            "entry_points":a["entry_points"],
            "major_components":a["major_components"],
            "component_relationships":a["component_relationships"],
            "configuration_model":a["configuration_model"],
            "extension_points":a["extension_points"],
            "deployment_model":a["deployment_model"],
            "architecture_evidence":a["evidence"]
        },
        "06_detailed_code_flow":{
            "title":"Overall Code Flow",
            "code_flow_status":s.code_flow_status,
            "overall_code_flow":s.overall_code_flow,
            "short_code_flow_explanation":s.code_flow_explanation,
            "static_data_control_flow":a["data_control_flow"],
            "detailed_static_code_flows":a["detailed_code_flows"]
        },
        "07_dependencies_and_compatibility":{
            "title":"Dependencies and Compatibility",
            "dependencies_by_scope":{k:[asdict(x) for x in v] for k,v in f.dependencies_by_scope.items()}
        },
        "08_tests_and_coverage":{
            "title":"Tests and Coverage","frameworks":f.tests.frameworks,
            "test_categories":f.tests.test_categories,"test_file_count":len(f.tests.test_files),
            "test_files":f.tests.test_files,"coverage_status":f.tests.coverage_status,
            "coverage_percentage":f.tests.coverage_percentage,
            "coverage_source":f.tests.coverage_source or "Not available"
        },
        "09_internal_apis":{"title":"Production Internal APIs","scope_note":"Test/mock/example routes are excluded.","apis":[asdict(x) for x in f.internal_apis]},
        "10_external_api_and_integration_calls":{
            "title":"Production External API and Integration Calls","scope_note":"Test/mock/example calls are excluded.","calls":[asdict(x) for x in f.external_calls]
        },
        "11_main_use_cases":{"title":"Main Use Cases","use_cases":s.main_use_cases},
        "12_analysis_limitations":{"title":"Analysis Limitations","limitations":s.limitations or ["None reported"]}
    }

def write_md(path,f,s):
    a=f.architecture_facts
    L=["# Repository Intelligent Analysis Report","",
       "## 1. Repository Summary","",
       f"- **Repository:** {f.repository_name}",f"- **Source:** {f.source}",
       f"- **Source Type:** {f.source_type}",f"- **Repository Type:** {f.repository_kind}",
       f"- **Files Analyzed:** {f.file_count}",f"- **Local LLM Status:** {s.status}","",
       "### What the Application / Repository Does","",
       s.what_repository_does or "Unable to determine from repository evidence","",
       "### Repository Summary","",s.repository_summary or "Unable to determine from repository evidence","",
       "## 2. Technology Stack",""]
    for k,v in f.technology_stack.items():
        L.append(f"- **{k.replace('_',' ').title()}:** {', '.join(v) if v else 'Not detected'}")

    L += ["","## 3. Repository Scan and Engineering Artifacts","",
          f"- **Important files:** {', '.join(f.important_files) if f.important_files else 'Not detected'}",""]
    for k,v in f.artifacts.items():
        L.append(f"- **{k.replace('_',' ').title()}:** {', '.join(v) if v else 'Not detected'}")

    L += ["","## 4. Main Components and Code Structure",""]
    for c in a.major_components:
        L += [f"### {c.get('name','Component')}",c.get("responsibility",""),
              f"**Evidence:** {', '.join(c.get('evidence',[]))}",""]
    if not a.major_components:L += ["No components detected.",""]

    L += ["## 5. Code Architecture","",
          f"- **Architecture Style:** {a.architecture_style}",
          f"- **Architecture Explanation:** {s.architecture_explanation or a.architecture_explanation}","",
          "### Layers / Modules",""]
    if a.layers_modules:
        L += [table(["Layer / Module","Description","Evidence"],
                    [[x.get("name"),x.get("description"),", ".join(x.get("evidence",[]))] for x in a.layers_modules]),""]
    else:L += ["Not detected.",""]

    L += ["### Entry Points","",
          table(["Type","Symbol / Command","Source File"],
                [[x.get("type"),x.get("symbol"),x.get("source_file")] for x in a.entry_points]),"",
          "### Major Components","",
          table(["Component","Responsibility","Evidence"],
                [[x.get("name"),x.get("responsibility"),", ".join(x.get("evidence",[]))] for x in a.major_components]),"",
          "### Component Relationships","",
          table(["From","To","Relationship"],
                [[x.get("from"),x.get("to"),x.get("relationship")] for x in a.component_relationships]),"",
          "### Configuration Model","",a.configuration_model,"",
          "### Extension Points",""]
    if a.extension_points:
        L += [f"- {x}" for x in a.extension_points]
    else:L.append("No explicit extension points were statically identified.")
    L += ["", "### Deployment Model","",a.deployment_model,"",
          "### Architecture Data / Control Flow",""]
    for i,x in enumerate(a.data_control_flow,1):L.append(f"{i}. {x}")

    L += ["","## 6. Overall Code Flow","",
          f"- **Code Flow Analysis Status:** {s.code_flow_status}","",
          "This section explains the repository flow in simple execution order. It separates the main runtime from independent automation/tooling paths and only uses code/source evidence found in the repository.",""]

    if s.overall_code_flow:
        current_group=""
        for item in s.overall_code_flow:
            step=item.get("step")
            title=item.get("title","Code Flow Step")
            if step==0:
                L += ["### Flow Overview","",item.get("explanation","").strip(),""]
                continue
            group=str(item.get("group","")).strip()
            if group and group != current_group:
                L += [f"### {group}",""]
                current_group=group
            L += [f"#### Step {step}: {title}","",item.get("explanation","").strip()]
            code=item.get("code",[]) or []
            if code:
                L += ["","**Code / files involved:**"]
                for x in code:L.append(f"- `{x}`")
            result=item.get("result","").strip()
            if result:L += ["",f"**What happens next:** {result}"]
            evidence=item.get("evidence",[]) or []
            if evidence:L += ["",f"**Evidence:** {', '.join(str(x) for x in evidence)}"]
            L.append("")
    else:
        merged=s.code_flow_explanation or a.data_control_flow
        for i,x in enumerate(merged,1):L.append(f"{i}. {x}")

    L += ["### Static Call / Module Paths","",
          "The paths below are the exact callable/import chains that static analysis could prove. They support the simplified flow above.",""]
    if a.detailed_code_flows:
        for flow in a.detailed_code_flows:
            L += [f"#### {flow.get('name','Flow')}",
                  f"- **Entry Point:** {flow.get('entry_point','Not available')}",
                  "- **Ordered Static Flow:**"]
            for i,x in enumerate(flow.get("steps",[]),1):L.append(f"  {i}. `{x}`")
            L += [f"- **Evidence:** {', '.join(flow.get('evidence',[]))}",""]
    else:
        L += ["No complete callable chain was statically provable for this repository.",""]

    L += ["## 7. Dependencies and Compatibility","",
          "Dependencies are grouped by scope. Example/test/documentation dependencies do not contaminate the core technology stack.",""]
    for scope,deps in f.dependencies_by_scope.items():
        L += [f"### {scope.replace('_',' ').title()} Dependencies","",
              table(["Dependency","Current Version / Constraint","Source","Latest Version","Compatibility","Notes"],
                    [[d.name,d.current_version,d.source_file,d.latest_version,d.compatibility_status,d.compatibility_notes] for d in deps]),""]

    L += ["## 8. Tests and Coverage","",
          f"- **Testing frameworks:** {', '.join(f.tests.frameworks) if f.tests.frameworks else 'Not detected'}",
          f"- **Test files detected:** {len(f.tests.test_files)}",
          f"- **Coverage status:** {f.tests.coverage_status}",
          f"- **Coverage percentage:** {f.tests.coverage_percentage if f.tests.coverage_percentage is not None else 'Not available'}",
          f"- **Coverage source:** {f.tests.coverage_source or 'Not available'}","",
          "## 9. Production Internal APIs","","_Test/mock/example routes are excluded._","",
          table(["Method","Endpoint","Handler","Component","Source File"],
                [[x.method,x.endpoint,x.handler,x.component,x.source_file] for x in f.internal_apis]),"",
          "## 10. Production External API and Integration Calls","","_Test/mock/example calls are excluded._","",
          table(["Caller","Technology","Target","Method","Source File","Evidence"],
                [[x.caller,x.technology,x.target,x.method,x.source_file,x.evidence] for x in f.external_calls]),"",
          "## 11. Main Use Cases",""]
    if s.main_use_cases:
        for u in s.main_use_cases:
            L += [f"### {u.get('name','Use Case')}",u.get("description",""),
                  f"**Participating Components:** {', '.join(u.get('participating_components',[])) if u.get('participating_components') else 'Not available'}",
                  "**Flow:**"]
            for i,x in enumerate(u.get("flow_steps",[]),1):L.append(f"{i}. {x}")
            L += [f"**Evidence:** {', '.join(u.get('evidence',[])) if u.get('evidence') else 'Not available'}",""]
    else:L += ["No high-level use cases were returned by the local LLM.",""]

    L += ["## 12. Analysis Limitations",""]
    L += [f"- {x}" for x in (s.limitations or ["None reported."])]
    path.write_text("\n".join(L).strip()+"\n",encoding="utf-8")

def write_reports(output,f,s):
    output.mkdir(parents=True,exist_ok=True)
    for p in output.iterdir():
        if p.is_file():p.unlink()
    d=doc(f,s)
    jp=output/"repository_analysis.json"
    mp=output/"repository_analysis.md"
    jp.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding="utf-8")
    write_md(mp,f,s)
    return jp,mp
