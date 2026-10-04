#!/usr/bin/env python3
from __future__ import annotations

import argparse, copy, hashlib, json, random
from pathlib import Path
from typing import Any

PROTOCOL = "FUNCTION_BOUNDARY_S2B2_B1_SCHEMA_SYNTH_HOLDOUT_V1"


def atom(pred: str, *args: str) -> dict[str,Any]: return {"pred":pred,"args":list(args)}

def prim(name, params, pre, eff, forbidden=None):
    return {"action_class":name,"parameters":params,"preconditions":pre,"effects":eff,"forbidden_effects":forbidden or []}

def fixture(fid,family,params,req_pre,req_eff,forbid,vocab,primitives,domains,state):
    return {
      "id":fid,
      "family":family,
      "structural_fingerprint": hashlib.sha256(json.dumps({
        "param_count":len(params),
        "pre_shapes":[[a["pred"],len(a["args"])] for a in req_pre],
        "effect_shapes":[[a["pred"],len(a["args"])] for a in req_eff],
        "forbid_shapes":[[a["pred"],len(a["args"])] for a in forbid],
        "primitive_shapes":[[len(p["parameters"]),len(p["preconditions"]),len(p["effects"]),len(p.get("forbidden_effects",[]))] for p in primitives]
      },sort_keys=True,separators=(",",":")).encode()).hexdigest(),
      "visible":{
        "schema_requirements":{"parameters":params,"required_preconditions":req_pre,"required_effects":req_eff,"forbidden_effects":forbid},
        "predicate_vocabulary":vocab,
        "domains":domains,
        "state":state,
        "primitive_actions":primitives
      },
      "oracle":{"semantic_signature":{"parameters":params,"preconditions":req_pre,"effects":req_eff,"constraints":{"forbidden_effects":forbid}}}
    }


def make_cases():
    out=[]
    # F1 unary: 1 precondition -> 1 effect; known primitive omits required effect.
    for i,(x,y) in enumerate((("asset_A","asset_B"),("asset_C","asset_D")),1):
      out.append(fixture(f"B1{i:02d}","unary_1pre_1effect",["$x"],[atom("eligible","$x")],[atom("certified","$x")],[atom("revoked","$x")],{"eligible":1,"certified":1,"revoked":1,"logged":1},[prim("LOG_ONLY",["$x"],[atom("eligible","$x")],[atom("logged","$x")])],{"$x":[x,y]},[atom("eligible",x)]))
    # F2 unary: 2 preconditions -> 1 effect; known primitive has only one precondition and forbidden side effect.
    for j,(x,y) in enumerate((("record_A","record_B"),("record_C","record_D")),3):
      out.append(fixture(f"B1{j:02d}","unary_2pre_1effect",["$x"],[atom("verified","$x"),atom("approved","$x")],[atom("released","$x")],[atom("bypassed","$x")],{"verified":1,"approved":1,"released":1,"bypassed":1},[prim("FAST_RELEASE",["$x"],[atom("verified","$x")],[atom("released","$x"),atom("bypassed","$x")])],{"$x":[x,y]},[atom("verified",x),atom("approved",x)]))
    # F3 unary: 1 precondition -> 2 required effects.
    for j,(x,y) in enumerate((("bundle_A","bundle_B"),("bundle_C","bundle_D")),5):
      out.append(fixture(f"B1{j:02d}","unary_1pre_2effect",["$x"],[atom("ready","$x")],[atom("sealed","$x"),atom("indexed","$x")],[atom("corrupted","$x")],{"ready":1,"sealed":1,"indexed":1,"corrupted":1},[prim("SEAL_ONLY",["$x"],[atom("ready","$x")],[atom("sealed","$x")])],{"$x":[x,y]},[atom("ready",x)]))
    # F4 binary: independent preconditions on each parameter -> binary effect.
    for j,(a,b,ad,bd) in enumerate((("job_A","node_A","job_B","node_B"),("job_C","node_C","job_D","node_D")),7):
      out.append(fixture(f"B1{j:02d}","binary_2pre_1cross_effect",["$a","$b"],[atom("job_ready","$a"),atom("node_ready","$b")],[atom("assigned","$a","$b")],[atom("overloaded","$b")],{"job_ready":1,"node_ready":1,"assigned":2,"overloaded":1},[prim("ASSIGN_UNCHECKED",["$a","$b"],[atom("job_ready","$a")],[atom("assigned","$a","$b"),atom("overloaded","$b")])],{"$a":[a,ad],"$b":[b,bd]},[atom("job_ready",a),atom("node_ready",b)]))
    # F5 binary: relation precondition -> two effects on different arities.
    for j,(a,b,ad,bd) in enumerate((("doc_A","vault_A","doc_B","vault_B"),("doc_C","vault_C","doc_D","vault_D")),9):
      out.append(fixture(f"B1{j:02d}","binary_cross_pre_2effects",["$a","$b"],[atom("authorized_for","$a","$b")],[atom("stored_at","$a","$b"),atom("retained","$a")],[atom("exposed","$a")],{"authorized_for":2,"stored_at":2,"retained":1,"exposed":1},[prim("STORE_ONLY",["$a","$b"],[atom("authorized_for","$a","$b")],[atom("stored_at","$a","$b")])],{"$a":[a,ad],"$b":[b,bd]},[atom("authorized_for",a,b)]))
    # F6 binary: two cross preconditions -> one unary effect, distractor produces required + forbidden.
    for j,(a,b,ad,bd) in enumerate((("pkg_A","sig_A","pkg_B","sig_B"),("pkg_C","sig_C","pkg_D","sig_D")),11):
      out.append(fixture(f"B1{j:02d}","binary_2cross_pre_1effect",["$a","$b"],[atom("signed_by","$a","$b"),atom("trusted","$b")],[atom("accepted","$a")],[atom("untrusted_accept","$a")],{"signed_by":2,"trusted":1,"accepted":1,"untrusted_accept":1},[prim("ACCEPT_ANY",["$a","$b"],[atom("signed_by","$a","$b")],[atom("accepted","$a"),atom("untrusted_accept","$a")])],{"$a":[a,ad],"$b":[b,bd]},[atom("signed_by",a,b),atom("trusted",b)]))
    # F7 binary: no required precondition, 2 effects, explicit forbidden side effect.
    for j,(a,b,ad,bd) in enumerate((("queue_A","worker_A","queue_B","worker_B"),("queue_C","worker_C","queue_D","worker_D")),13):
      out.append(fixture(f"B1{j:02d}","binary_0pre_2effects",["$a","$b"],[],[atom("linked","$a","$b"),atom("enabled","$a")],[atom("disabled","$a")],{"linked":2,"enabled":1,"disabled":1},[prim("LINK_ONLY",["$a","$b"],[],[atom("linked","$a","$b")]),prim("ENABLE_UNSAFE",["$a"],[],[atom("enabled","$a"),atom("disabled","$a")])],{"$a":[a,ad],"$b":[b,bd]},[]))
    # F8 unary: 3 preconditions -> 2 effects; known primitives split the effects, none individually sufficient.
    for j,(x,y) in enumerate((("release_A","release_B"),("release_C","release_D")),15):
      out.append(fixture(f"B1{j:02d}","unary_3pre_2effect_split",["$x"],[atom("tested","$x"),atom("signed","$x"),atom("current","$x")],[atom("published","$x"),atom("audited","$x")],[atom("stale","$x")],{"tested":1,"signed":1,"current":1,"published":1,"audited":1,"stale":1},[prim("PUBLISH_ONLY",["$x"],[atom("tested","$x"),atom("signed","$x")],[atom("published","$x")]),prim("AUDIT_ONLY",["$x"],[atom("current","$x")],[atom("audited","$x")])],{"$x":[x,y]},[atom("tested",x),atom("signed",x),atom("current",x)]))
    return out

CASES=make_cases()

def seed_int(seed:str)->int: return int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)
def generate(seed:str)->list[dict]:
    rng=random.Random(seed_int(seed)); rows=copy.deepcopy(CASES); rng.shuffle(rows)
    for f in rows:
        rng.shuffle(f["visible"]["primitive_actions"])
        for vals in f["visible"]["domains"].values(): rng.shuffle(vals)
    return rows

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    rows=generate(args.seed); digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    out={"protocol":PROTOCOL,"seed_source":"generator freeze commit SHA","seed":args.seed,"fixture_count":len(rows),"family_count":len({x['family'] for x in rows}),"holdout_digest":digest,"fixtures":rows}
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"protocol":PROTOCOL,"fixture_count":len(rows),"family_count":out["family_count"],"holdout_digest":digest,"structural_fingerprints":sorted({x['structural_fingerprint'] for x in rows})},indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
