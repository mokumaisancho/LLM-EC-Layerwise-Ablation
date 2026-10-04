#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
from pathlib import Path

PROTOCOL = "FUNCTION_BOUNDARY_S2B2B1_STRUCTURED_SCHEMA_HOLDOUT_V1"


def atom(pred: str, *args: str) -> dict:
    return {"pred": pred, "args": list(args)}


def proposal_1(param: str, ready: str, effect: str, target: str) -> dict:
    return {
        "proposal_kind": "NEW_CLASS",
        "action_class": "PROPOSED_NEW_CLASS",
        "parameters": [param],
        "preconditions": [atom(ready, param)],
        "effects": [atom(effect, param)],
        "bindings": {param: target},
    }


def proposal_2(pa: str, pb: str, pre_a: str, pre_b: str, effect: str, a: str, b: str) -> dict:
    return {
        "proposal_kind": "NEW_CLASS",
        "action_class": "PROPOSED_NEW_CLASS",
        "parameters": [pa, pb],
        "preconditions": [atom(pre_a, pa), atom(pre_b, pb)],
        "effects": [atom(effect, pa, pb)],
        "bindings": {pa: a, pb: b},
    }


def case1(fid: str, family: str, target: str, distractor: str, ready: str, effect: str, forbidden: str, partial: str) -> dict:
    param = "$x"
    visible = {
        "parameters": [param],
        "domains": {param: [target, distractor]},
        "predicate_vocab": {ready:1, effect:1, forbidden:1, partial:1, "audit_logged":1},
        "relation": {
            "operator": "REQUIRES_NEW_SCHEMA",
            "required_preconditions": [atom(ready, target)],
            "required_effects": [atom(effect, target)],
            "forbidden_effects": [atom(forbidden, target)]
        },
        "state": [atom(ready, target), atom("audit_logged", distractor)],
        "primitive_actions": [
            {"action_class":"PARTIAL_STEP", "parameters":[param], "preconditions":[atom(ready,param)], "effects":[atom(partial,param)]},
            {"action_class":"UNSAFE_DIRECT", "parameters":[param], "preconditions":[atom(ready,param)], "effects":[atom(effect,param),atom(forbidden,param)]},
            {"action_class":"AUDIT_ONLY", "parameters":[param], "preconditions":[], "effects":[atom("audit_logged",param)]}
        ],
        "existing_candidates": []
    }
    return {"id":fid,"family":family,"visible":visible,"oracle":{"canonical_proposal":proposal_1(param,ready,effect,target),"expected_outcome":"NOVEL_SCHEMA_VALID"}}


def case2(fid: str, family: str, a: str, ad: str, b: str, bd: str, pre_a: str, pre_b: str, effect: str, forbidden: str, partial: str) -> dict:
    pa,pb="$a","$b"
    visible = {
        "parameters": [pa,pb],
        "domains": {pa:[a,ad], pb:[b,bd]},
        "predicate_vocab": {pre_a:1, pre_b:1, effect:2, forbidden:1, partial:2, "audit_logged":1},
        "relation": {
            "operator":"REQUIRES_NEW_SCHEMA",
            "required_preconditions":[atom(pre_a,a),atom(pre_b,b)],
            "required_effects":[atom(effect,a,b)],
            "forbidden_effects":[atom(forbidden,a)]
        },
        "state":[atom(pre_a,a),atom(pre_b,b),atom("audit_logged",ad)],
        "primitive_actions":[
            {"action_class":"PARTIAL_PAIR", "parameters":[pa,pb], "preconditions":[atom(pre_a,pa)], "effects":[atom(partial,pa,pb)]},
            {"action_class":"UNSAFE_PAIR", "parameters":[pa,pb], "preconditions":[atom(pre_a,pa),atom(pre_b,pb)], "effects":[atom(effect,pa,pb),atom(forbidden,pa)]},
            {"action_class":"AUDIT_PAIR", "parameters":[pa,pb], "preconditions":[], "effects":[atom("audit_logged",pa)]}
        ],
        "existing_candidates": []
    }
    return {"id":fid,"family":family,"visible":visible,"oracle":{"canonical_proposal":proposal_2(pa,pb,pre_a,pre_b,effect,a,b),"expected_outcome":"NOVEL_SCHEMA_VALID"}}


CASES = [
    case1("N001","sterile_transfer","sample_A","sample_B","sterility_verified","transferred_sterile","contaminated","transfer_prepared"),
    case1("N002","sterile_transfer","culture_7","culture_8","sterility_verified","transferred_sterile","contaminated","transfer_prepared"),
    case1("N003","verified_rotate","key_A","key_B","rotation_approved","rotated_verified","unapproved_rotation","rotation_staged"),
    case1("N004","verified_rotate","credential_4","credential_5","rotation_approved","rotated_verified","unapproved_rotation","rotation_staged"),
    case2("N005","sealed_handoff","parcel_A","parcel_B","locker_2","locker_3","seal_verified","destination_ready","handed_off_to","seal_broken","handoff_staged"),
    case2("N006","sealed_handoff","specimen_9","specimen_10","vault_4","vault_5","seal_verified","destination_ready","handed_off_to","seal_broken","handoff_staged"),
    case2("N007","approved_migrate","dataset_A","dataset_B","zone_2","zone_3","migration_approved","zone_ready","migrated_to","policy_bypassed","migration_staged"),
    case2("N008","approved_migrate","ledger_6","ledger_7","cluster_4","cluster_5","migration_approved","zone_ready","migrated_to","policy_bypassed","migration_staged"),
    case1("N009","validated_decrypt","archive_A","archive_B","key_validated","decrypted_validated","unvalidated_decrypt","decrypt_staged"),
    case1("N010","validated_decrypt","bundle_3","bundle_4","key_validated","decrypted_validated","unvalidated_decrypt","decrypt_staged"),
    case2("N011","consent_dispatch","message_A","message_B","recipient_2","recipient_3","consent_verified","recipient_ready","dispatched_to","consent_bypassed","dispatch_staged"),
    case2("N012","consent_dispatch","notice_8","notice_9","endpoint_6","endpoint_7","consent_verified","recipient_ready","dispatched_to","consent_bypassed","dispatch_staged"),
    case1("N013","attested_export","report_A","report_B","attestation_valid","exported_attested","unattested_export","export_staged"),
    case1("N014","attested_export","record_14","record_15","attestation_valid","exported_attested","unattested_export","export_staged"),
    case2("N015","verified_mount","volume_A","volume_B","host_2","host_3","volume_verified","host_ready","mounted_on","unverified_mount","mount_staged"),
    case2("N016","verified_mount","image_11","image_12","node_8","node_9","volume_verified","host_ready","mounted_on","unverified_mount","mount_staged")
]


def seed_int(seed: str) -> int:
    return int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)


def generate(seed: str) -> list[dict]:
    rng=random.Random(seed_int(seed))
    fixtures=copy.deepcopy(CASES)
    rng.shuffle(fixtures)
    for f in fixtures:
        rng.shuffle(f["visible"]["primitive_actions"])
        for values in f["visible"]["domains"].values(): rng.shuffle(values)
    return fixtures


def digest(fixtures: list[dict]) -> str:
    return hashlib.sha256(json.dumps(fixtures,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",required=True); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    fixtures=generate(args.seed)
    out={"protocol":PROTOCOL,"seed_source":"generator freeze commit SHA","seed":args.seed,"fixture_count":len(fixtures),"family_count":len({f['family'] for f in fixtures}),"holdout_digest":digest(fixtures),"fixtures":fixtures}
    args.output.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:out[k] for k in ("protocol","seed","fixture_count","family_count","holdout_digest")},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
