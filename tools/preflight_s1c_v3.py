#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,py_compile,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TOOLS=ROOT/"tools"
sys.path.insert(0,str(TOOLS))

EXPECTED_BLOBS={
 "docs/S1C_V3_DENOTATIONAL_DISCOVERY_CONTRACT_2026-10-07.json":"db1127445f528e48eb675ac615e935114e27f878",
 "tools/s1c_v3_reference_truth_tables.json":"cdd7dfed407ca39e8c28d90cad3eeeb3ddfc2237",
 "tools/score_s1c_v3_denotational.py":"04e81ed94667f44512be6c29876baa1a90df92fb",
 "tools/generate_s1c_v3_corpus.py":"5f42fc77f9206a0f2f403faafc2b07884c3357ab",
 "tools/validate_s1c_v3_corpus.py":"eabc2f103783f1d003e9d9ac0e156d8bb1c396de",
 "tools/s1c_v3_grammar.py":"1440a425799926bd7b343b583ec0bbb8b33d602c",
 "tools/validate_s1c_v3_structure.py":"856a47fbf023da9b1ad2409966688c1036f49c6f",
 "tools/validate_s1c_v3_ambiguity.py":"bc8cc1d1d388534ad173d09471e94955fe83b19c",
 "tools/s1c_v3_deterministic_baseline.py":"4bfcfba79be4be880e0a35bcc4bad42b0faebc62",
 "tools/audit_s1c_v3_independent.py":"2da7f49ca837105dfca0ed76a197a2215c3c41c4",
 "tools/replay_s1c_v3_fixed_b2.py":"bf55bae79d936647fa222572842abdaef5a03723",
 "tools/classify_s1c_v3_terminal.py":"ee5d1f389d9a893b837729a93e4086a1dee33be3",
 "tools/s2b2b2_enumerative_inducer.py":"3ea2365b7d49f766fbdc14fd82c6ca44b2d29eb9",
}
EXPECTED_DATASET_DIGEST="2fc9e81251698c8736f451bcb63acd05eaaed16a3aeb650e19c1ef67e7eedacd"

def blob_sha(path:Path)->str:
    b=path.read_bytes();return hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()
def fail(reason,detail=None):
    print(json.dumps({"protocol":"S1C_V3_PREFLIGHT_V1","pass":False,"terminal":"S1C_V3_PREFLIGHT_FAIL_CLOSED","reason":reason,"detail":detail},indent=2));return 3

def main()->int:
    actual={}
    for rel,exp in EXPECTED_BLOBS.items():
        p=ROOT/rel
        if not p.exists():return fail("FROZEN_SOURCE_MISSING",rel)
        got=blob_sha(p);actual[rel]=got
        if got!=exp:return fail("FROZEN_SOURCE_DRIFT",{"path":rel,"actual":got,"expected":exp})
        if p.suffix==".py":
            try:py_compile.compile(str(p),doraise=True)
            except Exception as e:return fail("PY_COMPILE",{"path":rel,"error":repr(e)})
    try:
        import generate_s1c_v3_corpus as gen
        import validate_s1c_v3_corpus as oracle
        import validate_s1c_v3_structure as structure
        import validate_s1c_v3_ambiguity as amb
        import s1c_v3_deterministic_baseline as baseline
        import score_s1c_v3_denotational as scorer
        import s1c_v3_grammar as grammar
        import audit_s1c_v3_independent as auditmod
        import replay_s1c_v3_fixed_b2 as replaymod
        import classify_s1c_v3_terminal as classifier
    except Exception as e:return fail("IMPORT",repr(e))
    corpus=gen.build_corpus()
    if corpus["dataset_digest"]!=EXPECTED_DATASET_DIGEST:return fail("DATASET_DIGEST",corpus["dataset_digest"])
    ov=oracle.validate_corpus(corpus)
    if not ov["pass"]:return fail("ORACLE_VALIDATION",ov["failures"])
    st=structure.evaluate(corpus["tasks"])
    if not st["pass"]:return fail("STRUCTURAL_NOVELTY",st["failures"])
    am=amb.evaluate(corpus,ov)
    if not am["pass"]:return fail("AMBIGUITY_COVERAGE",am["failures"])
    preds={t["task_id"]:baseline.predict(t) for t in corpus["tasks"]}
    score=scorer.aggregate(corpus["tasks"],preds,ov["references"])
    if not score["pass"]:return fail("BASELINE_SCORE")
    if score["primary"]["training_partition_pairwise_accuracy"]!=1.0:return fail("BASELINE_PARTITION_NOT_IDENTIFIABLE",score["primary"])
    if score["secondary"]["abstention_accuracy"]!=1.0:return fail("BASELINE_ABSTENTION",score["secondary"])
    gchecks=[]
    for t in corpus["tasks"]:
        g=grammar.grammar_for(t);c=grammar.static_contract_check(t,g)
        if not c["pass"]:return fail("GRAMMAR_STATIC",{"task_id":t["task_id"],"failures":c["failures"]})
        gchecks.append({"task_id":t["task_id"],"sha256":hashlib.sha256(g.encode()).hexdigest(),"chars":len(g)})
    # The independent audit must not import generator/scorer/predictor; causal replay must pin B2.
    audit_src=(TOOLS/"audit_s1c_v3_independent.py").read_text()
    if any(x in audit_src for x in ("import generate_s1c_v3","import score_s1c_v3","import s1c_v3_deterministic")):
        return fail("AUDIT_IMPLEMENTATION_NOT_INDEPENDENT")
    if replaymod.SOLVER_BLOB!=EXPECTED_BLOBS["tools/s2b2b2_enumerative_inducer.py"]:
        return fail("CAUSAL_SOLVER_PIN_MISMATCH")
    out={"protocol":"S1C_V3_PREFLIGHT_V1","pass":True,"terminal":"S1C_V3_PREFLIGHT_PASS",
         "source_blob_pins":actual,"dataset_digest":corpus["dataset_digest"],"task_count":corpus["task_count"],
         "training_count":corpus["training_count"],"heldout_count":corpus["heldout_count"],
         "oracle_validation_terminal":ov["terminal"],"structural_terminal":st["terminal"],"ambiguity_terminal":am["terminal"],
         "baseline_primary":score["primary"],"baseline_secondary":score["secondary"],"grammar_checks":gchecks,
         "model_inference_executed":False,"model_acquisition_authorized":True,
         "required_runtime_gate":"S1C_V3_SYNTHETIC_GRAMMAR_SMOKE_PASS"}
    print(json.dumps(out,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())