from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_TERMINAL_CLASSIFIER_V1"
MATERIALITY=0.20
PRIMARY_KEYS=("training_partition_pairwise_accuracy","heldout_denotational_assignment_accuracy","exact_discovery_and_grounding_rate")

def fail(reason:str,detail:Any=None)->dict[str,Any]:
    return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V3_TERMINAL_FAIL_CLOSED","reason":reason,"detail":detail,"boundary_update_authorized":False}

def classify(audit:dict[str,Any],replay:dict[str,Any])->dict[str,Any]:
    if audit.get("terminal")!="S1C_V3_POSTRUN_AUDIT_PASS" or audit.get("pass") is not True:return fail("POSTRUN_AUDIT_NOT_PASS")
    if replay.get("terminal")!="S1C_V3_FIXED_B2_CAUSAL_REPLAY_PASS" or replay.get("pass") is not True:return fail("CAUSAL_REPLAY_NOT_PASS")
    if audit.get("result_overturning_gate_failures")!=0:return fail("RESULT_OVERTURNING_GATE_FAILURES_NONZERO")
    det=audit["deterministic"]["primary"]; q=audit["qwen25_1p5b"]["primary"]
    deltas={k:float(q[k])-float(det[k]) for k in PRIMARY_KEYS}
    deltas["fixed_b2_downstream_success"]=float(replay["qwen25_1p5b_downstream_success"])-float(replay["deterministic_downstream_success"])
    qmat={k:v for k,v in deltas.items() if v>=MATERIALITY}; dmat={k:v for k,v in deltas.items() if v<=-MATERIALITY}
    if qmat and dmat:return fail("CONFLICTING_MATERIAL_DIRECTIONS",{"deltas":deltas,"qwen_material":qmat,"deterministic_material":dmat})
    if qmat:
        terminal="V3_LLM_MATERIAL_ADVANTAGE"
        boundary="Semantic-slot discovery/grounding retains a material LLM advantage under the frozen V3 partial-behavior assay."
    elif dmat:
        terminal="V3_DETERMINISTIC_MATERIAL_ADVANTAGE"
        boundary="Deterministic external machinery materially matches/exceeds the tested LLM on at least one frozen V3 boundary metric with no opposing material metric."
    else:
        terminal="V3_NO_MATERIAL_SEPARATION"
        boundary="No frozen V3 boundary metric separates the arms by the predeclared materiality threshold."
    return {"protocol":PROTOCOL,"pass":True,"terminal":terminal,"materiality_abs":MATERIALITY,"deltas_qwen_minus_deterministic":deltas,
            "qwen_material_metrics":qmat,"deterministic_material_metrics":dmat,"boundary_statement":boundary,
            "boundary_update_authorized":True,"single_boundary_update_required":True,
            "claim_limit":"Only frozen V3 denotational discovery from raw language plus distinct partial transition probes. No open-ended world knowledge or unrestricted ontology invention claim."}

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("audit",type=Path);ap.add_argument("replay",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    a=json.loads(args.audit.read_text(encoding="utf-8"));r=json.loads(args.replay.read_text(encoding="utf-8"));out=classify(a,r)
    if args.output:args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2));raise SystemExit(0 if out.get("pass") else 3)