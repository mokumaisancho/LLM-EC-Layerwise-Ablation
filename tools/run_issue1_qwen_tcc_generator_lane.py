#!/usr/bin/env python3
"""TCC Generator v3 controlled Qwen diagnostic lane for origin Issue #1.

The TCC diagnostic SUCCESS terminal is deliberately NOT scientific four-arm
certification or ECv4 issue closure. Compiles typed, provenance-backed spec
using the exact pinned read-only tcc-compiler.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_issue57_tcc_generator_gate import TCC_SOURCE, context_for, node
from tools.run_issue1_qwen25_capacity_format_sweep import MODELS, run, verify


def sha(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()


def spec() -> dict:
    return {
        "schema": "tcc.spec.v3",
        "tcc_id": "ISSUE1-QWEN-SAME-FAMILY-TWO-FACTOR-ACTUAL-DIAGNOSTIC-V1",
        "goal": "Run actual verified Qwen2.5 0.5B/1.5B and native GBNF paired diagnostic, not scientific gold evaluation",
        "acceptance": [
            "Both registered model file SHA-256 and size match the frozen repo-registered provenance",
            "16 existing development cases, 4 treatment cells, 64 actual model inference invocations",
            "Input and prompt byte hashes remain matched across all treatment cells",
            "GBNF changes only the output formatting constraint, not decoding, model bytes, prompts or cases",
            "All original raw text and output format errors retained, no private gold or policy reads",
            "TCC diagnostic SUCCESS cannot close issue #1/#57/#58 or certify quality preservation",
        ],
        "state_keys": ["pins_verified", "sweep_artifact_sha256", "case_count"],
        "immutable_state_keys": [],
        "entry_nodes": ["verify_pin"],
        "nodes": [
            node("verify_pin", "action", writes=("pins_verified",), failure="blocked_pin"),
            node("run_actual_paired_sweep", "action", depends=("verify_pin",),
                 reads=("pins_verified",), writes=("sweep_artifact_sha256","case_count"),
                 failure="blocked_sweep"),
            node("diagnostic_only_complete", "terminal", depends=("run_actual_paired_sweep",),
                 terminal="SUCCESS"),
            node("blocked_pin", "terminal", terminal="BLOCKED"),
            node("blocked_sweep", "terminal", terminal="BLOCKED"),
        ],
    }


def execute(tcc_root: Path, source_commit: str, model_dir: Path, llama_cli: Path) -> dict:
    pinned = subprocess.run(["git","-C",str(tcc_root),"rev-parse","HEAD"],
                            capture_output=True,text=True,timeout=10)
    if pinned.returncode != 0 or pinned.stdout.strip() != TCC_SOURCE:
        raise ValueError("TCC_GENERATOR_PIN_MISMATCH")
    current = subprocess.run(["git","-C",str(ROOT),"rev-parse","HEAD"],
                             capture_output=True,text=True,timeout=10)
    if current.returncode != 0 or current.stdout.strip() != source_commit:
        raise ValueError("RESEARCH_SOURCE_COMMIT_DRIFT")
    sys.path.insert(0,str(tcc_root))
    from tcc.recipe_builder_v3 import generate_tcc_from_context
    from tcc.core_v3 import compile_spec, normalize_spec, validate_spec
    from tcc.runtime_v3 import execute_graph,to_ecv4_evidence
    contract=spec()
    ctx=context_for(contract,source_commit)
    ctx["selected_issue_id"]="ISSUE-1"
    ctx["actionable_issue_ids"]=["ISSUE-1"]
    ctx["blocked_issue_ids"]=[]
    ctx["snapshot_id"]="ISSUE1-QWEN-DIAGNOSTIC:"+source_commit[:14]
    ctx["source_fingerprint"]="sha256:"+sha({"contract":contract,"source_commit":source_commit,"issue":1,"generator_pin":TCC_SOURCE})
    generated=generate_tcc_from_context(ctx)
    if generated.get("result")!="tcc.spec.v3":
        raise RuntimeError("GENERATOR_BLOCKED:"+str(generated.get("reason_code"))+":"+str(generated.get("errors")))
    if validate_spec(generated["spec"]) or generated["spec"]!=normalize_spec(contract):
        raise RuntimeError("GENERATED_SPEC_SEMANTIC_DRIFT")
    graph=compile_spec(generated["spec"])
    observed: dict = {}
    def verify_handler(_node,_state,_attempt):
        try:
            for name,info in MODELS.items():
                verify(model_dir/info["filename"],info)
            if not llama_cli.is_file() or llama_cli.is_symlink():
                raise ValueError("LLAMA_BINARY_INVALID")
        except (OSError,ValueError) as exc:
            observed["pin_failure"]=type(exc).__name__+":"+str(exc)
            return {"status":"failure","evidence":["pin:FAIL:"+type(exc).__name__]}
        return {"status":"success","writes":{"pins_verified":True},
                "evidence":["pin:PASS:sha256-registered-Qwen2.5-0.5B+1.5B"]}
    def sweep_handler(_node,state,_attempt):
        if state.get("pins_verified") is not True:
            return {"status":"failure","evidence":["sweep:pin-state-not-passed"]}
        try:
            result=run(model_dir,llama_cli,60,head=source_commit)
            count=len(result["paired_cases"])
            if count!=16 or result["runtime"]["expected_total_model_invocations"]!=64:
                raise ValueError("FOUR_CELL_COVERAGE_INVALID")
            observed["result"]=result
            result_digest=sha(result)
            return {"status":"success",
                    "writes":{"sweep_artifact_sha256":result_digest,"case_count":count},
                    "evidence":["sweep:ACTUAL:4-cells:64-invocations", "sweep:sha256:"+result_digest]}
        except Exception as exc:
            observed["sweep_failure"]=type(exc).__name__+":"+str(exc)[:140]
            return {"status":"failure","evidence":["sweep:FAIL:"+type(exc).__name__]}
    runtime=execute_graph(graph,{"verify_pin":verify_handler,"run_actual_paired_sweep":sweep_handler})
    if runtime.get("result")!="TERMINAL":
        raise RuntimeError("TCC_RUNTIME_UNEXPECTED:"+str(runtime.get("result")))
    complete=(runtime["terminal_id"]=="diagnostic_only_complete"
              and runtime["terminal_status"]=="SUCCESS"
              and "result" in observed)
    envelope={
        "protocol":"ISSUE1_GENERATED_TCC_QWEN_DIAGNOSTIC_EXECUTION_V1",
        "research_source_commit":source_commit,
        "tcc_compiler_readonly_commit":TCC_SOURCE,
        "tcc_generated_spec_sha":graph["spec_hash"],
        "tcc_recipe_type":"suite.tcc-generation-recipe.v4",
        "tcc_generated_spec_type":generated["result"],
        "tcc_context_fingerprint":ctx["source_fingerprint"],
        "tcc_graph_nodes":len(graph["nodes"]),
        "tcc_graph_edges":len(graph["edges"]),
        "tcc_runtime_terminal":runtime["terminal_id"],
        "tcc_runtime_status":runtime["terminal_status"],
        "tcc_evidence":to_ecv4_evidence(graph,runtime),
        "actual_model_diagnostic":observed.get("result"),
        "failure":observed.get("pin_failure") or observed.get("sweep_failure"),
        "tcc_diagnostic_lane_success":complete,
        "full_independent_scientific_four_arm":"NOT_RUN",
        "scientific_quality_certified":False,
        "ecv4_issue_closure_authorized":False,
        "research_original_issue_stays_open":True,
        "terminal":"DIAGNOSTIC_SUCCESS_INDEPENDENT_SCIENCE_PENDING" if complete else "FAIL_CLOSED_DIAGNOSTIC_UNAVAILABLE",
    }
    return envelope


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--tcc-root",type=Path,required=True)
    ap.add_argument("--source-commit",required=True)
    ap.add_argument("--model-dir",type=Path,required=True)
    ap.add_argument("--llama-cli",type=Path,required=True)
    a=ap.parse_args()
    try:
        result=execute(a.tcc_root,a.source_commit,a.model_dir,a.llama_cli)
        print(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2))
        return 0 if result["tcc_diagnostic_lane_success"] else 3
    except Exception as exc:
        print(json.dumps({"protocol":"ISSUE1_GENERATED_TCC_QWEN_DIAGNOSTIC_EXECUTION_V1",
                          "terminal":"FAIL_CLOSED", "error":type(exc).__name__+":"+str(exc)[:500]}))
        return 3


if __name__=="__main__":
    raise SystemExit(main())
