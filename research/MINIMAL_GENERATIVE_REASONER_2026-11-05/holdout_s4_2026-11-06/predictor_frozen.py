#!/usr/bin/env python3
"""Frozen publicly visible S4 closure predictor (copied from prior diagnostic).

This subprocess sees ONLY public seven-field JSON, never a source ledger or gold.
Original code reference: Git blob d7aa6d74946064ffb6b9896c8c9ae94573f11630.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

PROTOCOL = "ISSUE1_S4_INTERFACE_INFORMATION_SUCCESSOR_DIAGNOSTIC_V1"


def predict(x:dict)->dict:
    fields={"protocol","selected_count","rejected_count","reframe_required",
            "trigger_residual_types","relation_groups","required_condition_state"}
    if not isinstance(x,dict) or set(x)!=fields or x.get("protocol")!=PROTOCOL:
        raise ValueError("PUBLIC_ONLY_SCHEMA_REQUIRED")
    # Known *typed* policy, NOT learned from gold/expected labels:
    # unresolved mandatory condition prevents closure; distinct competing
    # alternatives need selection continuation; equivalence permits completion.
    # It does not infer general language semantics or independent competence.
    if x["required_condition_state"] not in ("UNRESOLVED","NOT_EXPLICITLY_UNRESOLVED"):
        raise ValueError("INVALID_REQUIRED_CONDITION_STATE")
    if x["required_condition_state"]=="UNRESOLVED":
        return {"closure_class":"CONTINUE","reason":"UNRESOLVED_REQUIRED_CONDITION"}
    if any(g["relation_type"]=="COMPETING" and g["selected_member_count"]>=2
           for g in x["relation_groups"]):
        return {"closure_class":"CONTINUE","reason":"COMPETING_ALTERNATIVES_OPEN"}
    return {"closure_class":"CLOSE","reason":"NO_EXPLICIT_BLOCKING_SIGNAL_IN_PUBLIC_PROJECTION"}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--predict-public',type=Path,required=True)
    a=ap.parse_args()
    obj=json.loads(a.predict_public.read_text(encoding='utf-8'))
    print(json.dumps(predict(obj),sort_keys=True,ensure_ascii=False))

if __name__=='__main__':main()
