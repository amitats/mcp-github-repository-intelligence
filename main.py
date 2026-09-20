import argparse
import shutil
import sys
from pathlib import Path

from ingestion import ingest_repository, RepositoryIngestionError
from scanner import scan_repository
from static_analysis import run_static_analysis
from architecture_analysis import analyze_architecture
from compatibility import enrich, mark_skipped
from llm_analysis import analyze
from models import SemanticResult
from code_flow_analysis import static_overall_code_flow
from runtime_flow_analysis import enrich_facts_from_runtime, runtime_fallback_flow
from report_writer import write_reports

def args():
    p=argparse.ArgumentParser(description="Repository Intelligence Analyzer - Anand requirement")
    p.add_argument("--source",required=True,help="GitHub/Git URL or local repository folder")
    p.add_argument("--output",default="analysis-output")
    p.add_argument("--skip-compatibility",action="store_true")
    p.add_argument("--skip-llm",action="store_true")
    return p.parse_args()

def main():
    a=args(); repo=None; temp=False
    try:
        print("[1/8] Repository ingestion",flush=True)
        repo,temp,name=ingest_repository(a.source)
        print(f"      Repository: {name}",flush=True)

        print("[2/8] Repository scanning and classification",flush=True)
        files=scan_repository(repo)
        print(f"      Analyzable files: {len(files)}",flush=True)

        print("[3/8] Static facts: stack/dependencies/tests/APIs/integrations",flush=True)
        facts=run_static_analysis(repo,files,a.source,name)

        print("[4/8] Static code architecture and code-flow analysis",flush=True)
        arch,symbols=analyze_architecture(repo,files,facts.repository_kind,facts.artifacts)
        facts.architecture_facts=arch
        facts.symbols=symbols
        runtime_evidence=enrich_facts_from_runtime(repo,files,facts)
        print(f"      Architecture style: {arch.architecture_style}",flush=True)
        print(f"      Entry points: {len(arch.entry_points)}",flush=True)
        print(f"      Components: {len(arch.major_components)}",flush=True)
        print(f"      Relationships: {len(arch.component_relationships)}",flush=True)
        print(f"      Detailed static flows: {len(arch.detailed_code_flows)}",flush=True)

        print("[5/8] Dependency compatibility",flush=True)
        facts.dependencies_by_scope=mark_skipped(facts.dependencies_by_scope) if a.skip_compatibility else enrich(facts.dependencies_by_scope,facts.technology_stack.get("runtime",[]))
        print("      MCP/Search skipped" if a.skip_compatibility else "      Compatibility completed",flush=True)

        print("[6/8] Local LLM semantic explanation",flush=True)
        if a.skip_llm:
            sem=SemanticResult(
                status="Skipped by command line",
                repository_summary=facts.project_description or facts.readme_summary,
                what_repository_does=facts.project_description or facts.readme_summary,
                code_flow_explanation=facts.architecture_facts.data_control_flow,
                overall_code_flow=runtime_fallback_flow(runtime_evidence),
                code_flow_status="Deterministic static code-flow fallback (--skip-llm)",
                limitations=["Local LLM skipped; deterministic architecture and detailed static code flow are still reported."]
            )
        else:
            sem=analyze(repo,files,facts)
        print(f"      LLM status: {sem.status}",flush=True)

        print("[7/8] Result aggregation",flush=True)
        print("[8/8] Writing exactly two structured output files",flush=True)
        jp,mp=write_reports(Path(a.output).resolve(),facts,sem)

        print("\nAnalysis completed successfully.")
        print(f"JSON:     {jp}")
        print(f"Markdown: {mp}")

    except RepositoryIngestionError as exc:
        print(f"Ingestion failed: {exc}",file=sys.stderr);sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.");sys.exit(130)
    except Exception as exc:
        print(f"Analysis failed: {type(exc).__name__}: {exc}",file=sys.stderr);sys.exit(1)
    finally:
        if temp and repo:shutil.rmtree(repo.parent,ignore_errors=True)

if __name__=="__main__":
    main()
