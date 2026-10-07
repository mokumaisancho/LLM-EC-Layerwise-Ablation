#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

PROTOCOL="S1C_V32_TERMINAL_CLASSIFIER_V1"
MATERIALITY=0.20
PRIMARY=("semantic_output_validity_rate","training_partition_adjusted_rand_index","unseen_probe_behavior_accuracy","heldout_denotational_assignment_accuracy","exact_discovery_and_grounding_rate")

def fail(reason,detail=None):
    return {"protocol":PROTOCOL,"pass":False,"terminal":"S1C_V32_TERMINAL_FAIL_CLOSED","reason":reason,"detail":detail,"boundary_update_authorized":False}

def classify(audit,replay):
    if audit.get("terminal")!="S1C_V32_POSTRUN_AUDIT_PASS" or audit.get("pass") is not True:return fail("POSTRUN_AUDIT_NOT_PASS")
    if replay.get("terminal")!="S1C_V32_FIXED_B2_CAUSAL_REPLAY_PASS" or replay.get("pass") is not True:return fail("CAUSAL_REPLAY_NOT_PASS")
    if audit.get("result_overturning_gate_failures")!=0:return fail("RESULT_OVERTURNING_GATE_FAILURES_NONZERO")
    d=audit["deterministic"]["primary"];q=audit["qwen25_1p5b"]["primary"]
    deltas={k:float(q[k])-float(d[k]) for k in PRIMARY}
    deltas["fixed_b2_downstream_success"]=float(replay["qwen25_1p5b_downstream_success"])-float(replay["deterministic_downstream_success"])
    qm={k:v for k,v in deltas.items() if v>=MATERIALITY};dm={k:v for k,v in deltas.items() if v<=-MATERIALITY}
    if qm and dm:return fail("CONFLICTING_MATERIAL_DIRECTIONS",{"deltas":deltas,"qwen_material":qm,"deterministic_material":dm})
    if qm:terminal="V32_LLM_MATERIAL_ADVANTAGE";statement="Within the frozen finite 64-function assay, Qwen has a material advantage in at least one predeclared metric."
    elif dm:terminal="V32_DETERMINISTIC_MATERIAL_ADVANTAGE";statement="Within the frozen finite 64-function assay, deterministic external machinery has a material advantage in at least one predeclared metric and no material metric favors Qwen."
    else:terminal="V32_NO_MATERIAL_SEPARATION";statement="Within the frozen finite 64-function assay, no predeclared metric separates the arms by the materiality threshold."
    return {"protocol":PROTOCOL,"pass":True,"terminal":terminal,"materiality_abs":MATERIALITY,"deltas_qwen_minus_deterministic":deltas,
            "qwen_material_metrics":qm,"deterministic_material_metrics":dm,"boundary_statement":statement,"boundary_update_authorized":True,
            "single_boundary_update_required":True,"claim_limit":"Finite public coordinate-wise 64-function hypothesis class only; no unrestricted ontology invention or open-ended world-knowledge claim."}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("audit",type=Path);ap.add_argument("replay",type=Path);ap.add_argument("--output",type=Path);args=ap.parse_args()
    out=classify(json.loads(args.audit.read_text()),json.loads(args.replay.read_text()));txt=json.dumps(out,indent=2)+"\n"
    if args.output:args.output.write_text(txt)
    print(txt,end="");return 0 if out.get("pass") else 3
if __name__=="__main__":raise SystemExit(main())
