#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

PROTOCOL = "S2B2_B1_INDEPENDENT_SEMANTIC_SCORER_V1"


def canon(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: canon(v[k]) for k in sorted(v)}
    if isinstance(v, list):
        keyed = {json.dumps(canon(x), sort_keys=True, separators=(",", ":")): canon(x) for x in v}
        return [keyed[k] for k in sorted(keyed)]
    return v


def atom_key(a: dict[str, Any]) -> str:
    return json.dumps(canon(a), sort_keys=True, separators=(",", ":"))


def schema_signature(schema: dict[str, Any]) -> str:
    return json.dumps(canon({
        "parameters": schema.get("parameters", []),
        "preconditions": schema.get("preconditions", []),
        "effects": schema.get("effects", []),
        "constraints": schema.get("constraints", {}),
    }), sort_keys=True, separators=(",", ":"))


def _vars(v: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(v, str) and v.startswith("$"):
        out.add(v)
    elif isinstance(v, dict):
        for x in v.values(): out |= _vars(x)
    elif isinstance(v, list):
        for x in v: out |= _vars(x)
    return out


def _atoms_valid(atoms: Any, vocab: dict[str, int], params: set[str]) -> bool:
    if not isinstance(atoms, list): return False
    for a in atoms:
        if not isinstance(a, dict) or set(a) != {"pred","args"}: return False
        if a["pred"] not in vocab or not isinstance(a["args"], list) or len(a["args"]) != vocab[a["pred"]]: return False
        if not _vars(a).issubset(params): return False
    return True


def semantic_validity(visible: dict[str, Any], proposal: Any) -> dict[str, Any]:
    req = visible["schema_requirements"]
    vocab = visible["predicate_vocabulary"]
    if not isinstance(proposal, dict): return {"valid":False,"reason":"NOT_OBJECT"}
    required_keys = {"proposal_kind","action_class","parameters","preconditions","effects","constraints"}
    if set(proposal) != required_keys: return {"valid":False,"reason":"WRONG_KEYS"}
    if proposal["proposal_kind"] != "NEW_CLASS" or not isinstance(proposal["action_class"], str): return {"valid":False,"reason":"WRONG_KIND"}
    if not isinstance(proposal["parameters"], list) or set(proposal["parameters"]) != set(req["parameters"]): return {"valid":False,"reason":"PARAMETER_MISMATCH"}
    params=set(proposal["parameters"])
    if not _atoms_valid(proposal["preconditions"],vocab,params) or not _atoms_valid(proposal["effects"],vocab,params): return {"valid":False,"reason":"INVALID_ATOM"}
    constraints=proposal["constraints"]
    if not isinstance(constraints,dict) or set(constraints)!={"forbidden_effects"} or not _atoms_valid(constraints["forbidden_effects"],vocab,params): return {"valid":False,"reason":"INVALID_CONSTRAINT"}
    if {atom_key(x) for x in proposal["preconditions"]} != {atom_key(x) for x in req.get("required_preconditions",[])}: return {"valid":False,"reason":"PRECONDITION_MISMATCH"}
    if {atom_key(x) for x in proposal["effects"]} != {atom_key(x) for x in req.get("required_effects",[])}: return {"valid":False,"reason":"EFFECT_MISMATCH"}
    if {atom_key(x) for x in constraints["forbidden_effects"]} != {atom_key(x) for x in req.get("forbidden_effects",[])}: return {"valid":False,"reason":"FORBIDDEN_CONSTRAINT_MISMATCH"}
    supplied={schema_signature({"parameters":p.get("parameters",[]),"preconditions":p.get("preconditions",[]),"effects":p.get("effects",[]),"constraints":{"forbidden_effects":p.get("forbidden_effects",[])}}) for p in visible.get("primitive_actions",[])}
    if schema_signature(proposal) in supplied: return {"valid":False,"reason":"NOT_NOVEL_VS_SUPPLIED_ONTOLOGY"}
    return {"valid":True,"reason":"VALID"}


def score_rows(fixtures: list[dict[str,Any]], predictions: dict[str,Any]) -> dict[str,Any]:
    valid=invalid=fail_open=0
    per_family=defaultdict(lambda:{"fixtures":0,"valid":0,"invalid":0})
    rows=[]
    for f in fixtures:
        fid=f["id"]
        pred=predictions.get(fid)
        s=semantic_validity(f["visible"],pred)
        ok=bool(s["valid"])
        valid += int(ok); invalid += int(not ok); fail_open += int((not ok) and pred is not None)
        fam=f["family"]
        per_family[fam]["fixtures"] += 1; per_family[fam]["valid"] += int(ok); per_family[fam]["invalid"] += int(not ok)
        rows.append({"fixture_id":fid,"valid":ok,"reason":s["reason"],"prediction":pred})
    return {
        "valid_schema_proposal_rate": valid/len(fixtures),
        "valid_total": valid,
        "invalid_total": invalid,
        "fail_open_count": fail_open,
        "fixture_count": len(fixtures),
        "per_family": {k:{**v,"valid_rate":v["valid"]/v["fixtures"]} for k,v in sorted(per_family.items())},
        "rows": rows,
    }
