#!/usr/bin/env python3
from __future__ import annotations

import hashlib, itertools, json
from pathlib import Path
from typing import Any

from generate_s2b2b1_schema_synth_holdout import generate

ROOT=Path(__file__).resolve().parents[1]
SEED="04f9b2fff2fde06f2b1be6cfc6030954f59c2f8c"
EXPECTED_DIGEST="dde736e4f37b55567af45726e378291bfa07d44d39ee58e2038804582426e650"
EXPECTED_FPS={
"6ddc844ee709d99af8b9bf205f2d1df01941f49954b244aaa39d792a286ce539","7bf792aed05b54df27f9acae6382ffdbbf66aeec7abfb38455e5bd5c2b5f2d08","7ebcc477375d9e6aaaf86f37e6eebd2245552ef884d2c2d2c11fbdf0ec20d8e2","8563241b834559d047017a2047b66a22b2d9f6b23f058942cf6ca096c2754b0c","8af3b9d7667188272b9adea987e7d4a4993c77d2436bd07c6cc086c5762fbed0","95ce8d497b348cfe5f89152ec456803b4226f2d205343e6f7f8994edf7db46c2","e9ef47decb153806eb2e32b7f3395daa04dbc4ecbc6c50b341d1b3df773392cf","f6b18f94ff26da6d05e6b168c09f569605389ad7f2f4152621ab3aa5e8e83f31"}
FORBIDDEN_VISIBLE={"oracle","gold","expected","family","category","label","hidden_outcome","scorer_annotation"}

def canon(v:Any)->str:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def atom_key(v:dict)->str:return canon(v)
def subst(v:Any,b:dict[str,str])->Any:
    if isinstance(v,str) and v.startswith("$"): return b[v]
    if isinstance(v,list): return [subst(x,b) for x in v]
    if isinstance(v,dict): return {k:subst(x,b) for k,x in v.items()}
    return v

def scan(v:Any,path="$")->list[str]:
    out=[]
    if isinstance(v,dict):
        for k,x in v.items():
            if k in FORBIDDEN_VISIBLE: out.append(f"{path}.{k}")
            out+=scan(x,f"{path}.{k}")
    elif isinstance(v,list):
        for i,x in enumerate(v): out+=scan(x,f"{path}[{i}]")
    return out

def known_primitive_can_satisfy(visible:dict)->bool:
    req=visible["schema_requirements"]
    domains=visible["domains"]
    state={atom_key(a) for a in visible.get("state",[])}
    for p in visible.get("primitive_actions",[]):
        params=p.get("parameters",[])
        if any(x not in domains for x in params): continue
        for vals in itertools.product(*(domains[x] for x in params)):
            b=dict(zip(params,vals))
            pre={atom_key(subst(a,b)) for a in p.get("preconditions",[])}
            if not pre.issubset(state): continue
            eff={atom_key(subst(a,b)) for a in p.get("effects",[])}
            if any(x not in b for x in req["parameters"]): continue
            r_eff={atom_key(subst(a,b)) for a in req.get("required_effects",[])}
            r_forbid={atom_key(subst(a,b)) for a in req.get("forbidden_effects",[])}
            if r_eff.issubset(eff) and not (eff & r_forbid): return True
    return False

def main()->int:
    rows=generate(SEED)
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if digest!=EXPECTED_DIGEST: raise SystemExit("B1_PREFLIGHT_FAIL:DIGEST")
    if len(rows)!=16 or len({r['family'] for r in rows})!=8: raise SystemExit("B1_PREFLIGHT_FAIL:COUNT")
    fps={r["structural_fingerprint"] for r in rows}
    if fps!=EXPECTED_FPS: raise SystemExit("B1_PREFLIGHT_FAIL:FINGERPRINT")
    failures=[]
    for f in rows:
        leaks=scan(f["visible"])
        if leaks: failures.append({"id":f["id"],"gate":"LEAKAGE","detail":leaks})
        if known_primitive_can_satisfy(f["visible"]): failures.append({"id":f["id"],"gate":"KNOWN_PRIMITIVE_ALREADY_SUFFICIENT"})
        if "oracle" not in f or "semantic_signature" not in f["oracle"]: failures.append({"id":f["id"],"gate":"ORACLE_RECORD_MISSING"})
    if failures:
        print(json.dumps({"terminal":"B1_PREFLIGHT_FAIL","failures":failures},indent=2)); return 2
    out={"terminal":"B1_PREFLIGHT_PASS","protocol":"S2B2_MVP_TCC_V3","fixture_count":16,"family_count":8,"holdout_digest":digest,"known_primitive_insufficient":"16/16","visible_leakage":"0/16","structural_fingerprints":8,"model_inference":False}
    print(json.dumps(out,indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
