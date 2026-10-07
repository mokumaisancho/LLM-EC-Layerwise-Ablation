#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V31_TERMINAL_CLASSIFIER_V1"
MATERIALITY=0.20
PRIMARY_KEYS=(
 "training_partition_adjusted_rand_index",
 "unseen_probe_behavior_accuracy",
 "heldout_denotational_assignment_accuracy",
 "exact_discovery_and_grounding_rate",
)

def fail(reason:str,detail:Any=None)->dict[str,Any]:
    return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V31_TERMINAL_FAIL_CLOSED","reason":reason,"detail":detail,"boundary_update_authorized":False}

def classify(audit:dict[str,Any],replay:dict[str,Any])->dict[str,Any]:
    if audit.get("terminal")!="S1C_V31_POSTRUN_AUDIT_PASS" or audit.get("pass") is not True:return fail("POSTRUN_AUDIT_NOT_PASS")
    if replay.get("terminal")!="S1C_V31_FIXED_B2_CAUSAL_REPLAY_PASS" or replay.get("pass") is not True:return fail("CAUSAL_REPLAY_NOT_PASS")
    if audit.get("result_overturning_gate_failures")!=0:return fail("RESULT_OVERTURNING_GATE_FAILURES_NONZERO")
    d=audit["deterministic"]["primary"];q=audit["qwen25_1p5b"]["primary"]
    deltas={k:float(q[k])-float(d[k]) for k in PRIMARY_KEYS}
    deltas["fixed_b2_downstream_success"]=float(replay["qwen25_1p5b_downstream_success"])-float(replay["deterministic_downstream_success"])
    qmat={k:v for k,v in deltas.items() if v>=MATERIALITY};dmat={k:v for k,v in deltas.items() if v<=-MATERIALITY}
    if qmat and dmat:return fail("CONFLICTING_MATERIAL_DIRECTIONS",{"deltas":deltas,"qwen_material":qmat,"deterministic_material":dmat})
    if qmat:
        terminal="V31_LLM_MATERIAL_ADVANTAGE"
        boundary="Within the frozen finite 64-function denotational-discovery assay, Qwen retains a material advantage in at least one predeclared metric."
    elif dmat:
        terminal="V31_DETERMINISTIC_MATERIAL_ADVANTAGE"
        boundary="Within the frozen finite 64-function denotational-discovery assay, deterministic external machinery has a material advantage in at least one predeclared metric and no material metric favors Qwen."
    else:
        terminal="V31_NO_MATERIAL_SEPARATION"
        boundary="Within the frozen finite 64-function denotational-discovery assay, no predeclared metric separates the arms by the materiality threshold."
    return {"protocol":PROTOCOL,"pass":True,"terminal":terminal,"materiality_abs":MATERIALITY,
            "deltas_qwen_minus_deterministic":deltas,"qwen_material_metrics":qmat,"deterministic_material_metrics":dmat,
            "boundary_statement":boundary,"boundary_update_authorized":True,"single_boundary_update_required":True,
            "claim_limit":"Finite public coordinate-wise transition hypothesis class only; no unrestricted ontology invention or open-ended world-knowledge claim."}

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument("audit",type=Path);ap.add_argument("replay",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=classify(json.loads(args.audit.read_text()),json.loads(args.replay.read_text()));txt=json.dumps(out,indent=2)+"\n"
    if args.output:args.output.write_text(txt,encoding="utf-8")
    print(txt,end="");return 0 if out.get("pass") else 3

if __name__=="__main__":raise SystemExit(main())
