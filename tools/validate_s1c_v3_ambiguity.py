from __future__ import annotations
import argparse,json
from pathlib import Path
from typing import Any

PROTOCOL="S1C_V3_AMBIGUITY_COVERAGE_GATE_V1"

def evaluate(corpus:dict[str,Any], oracle_validation:dict[str,Any])->dict[str,Any]:
    failures=[]; rows=[]
    refs=oracle_validation.get("references") or {}
    for task in corpus.get("tasks",[]):
        tid=task["task_id"]; held=task["visible"]["heldout_examples"]; ref=refs.get(tid,{}).get("heldout_semantics",{})
        visible_ids={x["example_id"] for x in held}
        ambiguous=[eid for eid,s in ref.items() if s.get("status")=="AMBIGUOUS"]
        normal=[eid for eid,s in ref.items() if s.get("status")=="OK"]
        cue_ids=[x["example_id"] for x in held if "unresolved between" in str(x.get("raw_text","")).lower()]
        ok=(len(held)==3 and len(ambiguous)==1 and len(normal)==2 and set(ref)==visible_ids and set(cue_ids)==set(ambiguous))
        rows.append({"task_id":tid,"heldout_count":len(held),"normal_count":len(normal),"ambiguous_count":len(ambiguous),"ambiguous_ids":ambiguous,"visible_ambiguity_cue_ids":cue_ids,"pass":ok})
        if not ok: failures.append({"task_id":tid,"gate":"AMBIGUITY_COVERAGE_INVALID","row":rows[-1]})
    return {"protocol":PROTOCOL,"pass":not failures,"terminal":"S1C_V3_AMBIGUITY_COVERAGE_PASS" if not failures else "S1C_V3_AMBIGUITY_COVERAGE_FAIL_CLOSED","failure_count":len(failures),"failures":failures,"rows":rows}

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("corpus",type=Path); ap.add_argument("oracle",type=Path); ap.add_argument("--output",type=Path); args=ap.parse_args()
    corpus=json.loads(args.corpus.read_text(encoding="utf-8")); oracle=json.loads(args.oracle.read_text(encoding="utf-8")); out=evaluate(corpus,oracle)
    if args.output: args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","pass","terminal","failure_count")},indent=2)); raise SystemExit(0 if out["pass"] else 3)