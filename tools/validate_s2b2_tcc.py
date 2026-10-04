#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "docs" / "S2B2_MVP_AC_DEPENDENCY_TCC_2026-10-04.json"
EXPECTED_PROTOCOL = "S2B2_MVP_TCC_V1"
FORBIDDEN_KEYS = {"gold","oracle","expected","label","family","category","forbidden","hidden_outcome","scorer_annotation"}
FORBIDDEN_CORE_REFS = ("s2b2a_composition_core", "tools.s2b2a_composition_core")

class GateFailure(RuntimeError):
    def __init__(self, terminal: str, detail: str):
        self.terminal, self.detail = terminal, detail
        super().__init__(detail)

def fail(terminal: str, detail: str) -> None:
    raise GateFailure(terminal, detail)

def load_json(path: Path) -> Any:
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e: fail("INVALID_TEST_CONTRACT", f"cannot read {path}: {e}")

def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",",":"), ensure_ascii=False)

def sha(v: Any) -> str:
    return hashlib.sha256(canon(v).encode()).hexdigest()

def candidate_key(c: dict[str, Any]) -> str:
    b = c.get("bindings", {})
    return canon({"action_class": c.get("action_class"), "bindings": {k:b[k] for k in sorted(b)}})

def signature(a: dict[str, Any]) -> str:
    return canon({"parameters":a.get("parameters",[]),"preconditions":a.get("preconditions",[]),"effects":a.get("effects",[]),"constraints":a.get("constraints",[])})

def scan_keys(v: Any, path: str="$") -> list[str]:
    out=[]
    if isinstance(v, dict):
        for k,x in v.items():
            if k in FORBIDDEN_KEYS: out.append(f"{path}.{k}")
            out += scan_keys(x, f"{path}.{k}")
    elif isinstance(v, list):
        for i,x in enumerate(v): out += scan_keys(x, f"{path}[{i}]")
    return out

def git(*args: str) -> str:
    p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True)
    if p.returncode: fail("INVALID_TEST_CONTRACT", p.stderr.strip() or "git failed")
    return p.stdout

def validate_contract(c: dict[str, Any]) -> None:
    if c.get("protocol") != EXPECTED_PROTOCOL: fail("INVALID_TEST_CONTRACT","wrong protocol")
    if c.get("owner_issue") != 43: fail("INVALID_TEST_CONTRACT","wrong owner issue")
    if c.get("stage_a_scoring",{}).get("materiality_abs") != 0.20: fail("INVALID_TEST_CONTRACT","materiality drift")
    inv=set(c.get("invariants",[]))
    req={"NO_GITHUB_ACTIONS","NO_GOOGLE_DRIVE_MODEL_RELAY","NO_QWEN3_4B_AUTO_BRANCH","NO_POST_RESULT_REPAIR_UNDER_V1","NO_PREDICTOR_AUTHORED_ORACLE","NO_ARM_ASYMMETRIC_HIDDEN_METADATA","NEW_BLOCKING_RESIDUAL_REQUIRES_REGISTRY_AND_VERSIONED_SUCCESSOR"}
    if req-inv: fail("INVALID_TEST_CONTRACT",f"missing invariants {sorted(req-inv)}")

def precheck(c: dict[str, Any]) -> dict[str, Any]:
    core=c["frozen_assets"]["stage_a_core"]; path=ROOT/core["path"]
    if not path.exists(): fail("INVALID_PREDECESSOR_STATE","frozen core missing")
    frozen=git("show",f"{core['commit']}:{core['path']}").encode()
    current=path.read_bytes()
    if frozen != current: fail("FREEZE_ORDER_VIOLATION","Stage-A core drifted after freeze")
    wf=ROOT/".github"/"workflows"
    if wf.exists() and any(p.is_file() and p.suffix in {".yml",".yaml"} for p in wf.iterdir()): fail("INVALID_PREDECESSOR_STATE","GitHub Actions workflow present")
    return {"terminal":"PRECHECK_PASS","core_commit":core["commit"],"core_sha256":hashlib.sha256(current).hexdigest()}

def fixture_map(doc: dict[str, Any]) -> dict[str,dict[str,Any]]:
    rows=doc.get("fixtures")
    if not isinstance(rows,list) or not rows: fail("INVALID_TEST_CONTRACT","fixtures missing")
    out={}
    for r in rows:
        fid=r.get("id")
        if not isinstance(fid,str) or not fid or fid in out: fail("INVALID_TEST_CONTRACT",f"invalid fixture id {fid!r}")
        out[fid]=r
    return out

def no_core_ref(path: Path) -> None:
    text=path.read_text(encoding="utf-8")
    for token in FORBIDDEN_CORE_REFS:
        if token in text: fail("CIRCULAR_ORACLE",f"{path} references {token}")

def prior_set(path: Path|None) -> set[str]:
    if path is None: return set()
    x=load_json(path); vals=x.get("structural_fingerprints",[]) if isinstance(x,dict) else x
    if not isinstance(vals,list): fail("INVALID_TEST_CONTRACT","bad prior fingerprint file")
    return {str(v) for v in vals}

def check_manifest(m: dict[str,Any], ids:set[str], prior:set[str]) -> set[str]:
    rows=m.get("fixtures")
    if not isinstance(rows,list) or len(rows)!=len(ids): fail("HOLDOUT_NOT_INDEPENDENT","manifest count mismatch")
    mids=set(); fps=set()
    for r in rows:
        fid,fp=r.get("id"),r.get("structural_fingerprint")
        if not isinstance(fid,str) or not isinstance(fp,str) or not fp: fail("HOLDOUT_NOT_INDEPENDENT","manifest id/fingerprint missing")
        mids.add(fid)
        if fp in fps: fail("HOLDOUT_NOT_INDEPENDENT",f"duplicate fingerprint {fp}")
        fps.add(fp)
    if mids!=ids: fail("HOLDOUT_NOT_INDEPENDENT","manifest IDs mismatch")
    overlap=fps & prior
    if overlap: fail("HOLDOUT_NOT_INDEPENDENT",f"prior fingerprint overlap {sorted(overlap)}")
    return fps

def stage_a(args) -> dict[str,Any]:
    vd,od,md=load_json(args.visible),load_json(args.oracle),load_json(args.manifest)
    hits=scan_keys(vd)
    if hits: fail("ORACLE_OR_LABEL_LEAKAGE",f"visible forbidden keys {hits}")
    v,o=fixture_map(vd),fixture_map(od)
    if set(v)!=set(o): fail("INVALID_TEST_CONTRACT","visible/oracle IDs mismatch")
    fps=check_manifest(md,set(v),prior_set(args.prior_fingerprints))
    no_core_ref(args.generator); no_core_ref(args.scorer)
    for fid,row in v.items():
        x=row.get("visible",row); known={p.get("action_class") for p in x.get("primitive_actions",[])}
        domains=x.get("domains",{}); existing={candidate_key(c) for c in x.get("existing_candidates",[])}
        gold=o[fid].get("gold_candidates",[]); gkeys={candidate_key(c) for c in gold}
        if existing & gkeys: fail("GOLD_ALREADY_PRESENT",f"{fid}: gold already present")
        for c in gold:
            if c.get("action_class") not in known: fail("INVALID_STAGE_A_FIXTURE",f"{fid}: gold class absent from known primitives")
            for k,val in c.get("bindings",{}).items():
                if val not in domains.get(k,[]): fail("INVALID_STAGE_A_FIXTURE",f"{fid}: binding outside domain")
    return {"terminal":"STAGE_A_CONTAMINATION_GATE_PASS","fixture_count":len(v),"visible_sha256":sha(vd),"oracle_sha256":sha(od),"manifest_sha256":sha(md),"fingerprints":len(fps)}

def stage_b(args) -> dict[str,Any]:
    vd,od,md=load_json(args.visible),load_json(args.oracle),load_json(args.manifest)
    hits=scan_keys(vd)
    if hits: fail("ORACLE_OR_LABEL_LEAKAGE",f"visible forbidden keys {hits}")
    v,o=fixture_map(vd),fixture_map(od)
    if set(v)!=set(o): fail("INVALID_TEST_CONTRACT","visible/oracle IDs mismatch")
    check_manifest(md,set(v),prior_set(args.prior_fingerprints))
    no_core_ref(args.generator); no_core_ref(args.scorer)
    for fid,row in v.items():
        x=row.get("visible",row); known={signature(p) for p in x.get("primitive_actions",[])}
        req=o[fid].get("required_class_signature")
        if not isinstance(req,dict): fail("INVALID_TEST_CONTRACT",f"{fid}: required_class_signature missing")
        if signature(req) in known: fail("ONTOLOGY_CLASS_NOT_ACTUALLY_NOVEL",f"{fid}: equivalent known primitive exists")
    return {"terminal":"STAGE_B_CONTAMINATION_GATE_PASS","fixture_count":len(v),"visible_sha256":sha(vd),"oracle_sha256":sha(od),"manifest_sha256":sha(md)}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--contract",type=Path,default=DEFAULT_CONTRACT)
    sub=ap.add_subparsers(dest="mode",required=True); sub.add_parser("precheck")
    for name in ("stage-a","stage-b"):
        p=sub.add_parser(name); p.add_argument("--visible",type=Path,required=True); p.add_argument("--oracle",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--generator",type=Path,required=True); p.add_argument("--scorer",type=Path,required=True); p.add_argument("--prior-fingerprints",type=Path)
    args=ap.parse_args()
    try:
        c=load_json(args.contract); validate_contract(c)
        out=precheck(c) if args.mode=="precheck" else stage_a(args) if args.mode=="stage-a" else stage_b(args)
        print(json.dumps(out,indent=2,sort_keys=True)); return 0
    except GateFailure as e:
        print(json.dumps({"terminal":e.terminal,"detail":e.detail},indent=2),file=sys.stderr); return 2

if __name__=="__main__": raise SystemExit(main())
