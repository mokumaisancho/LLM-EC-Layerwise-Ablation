#!/usr/bin/env python3
"""Read-only causal-contamination and lexical-sensitivity audit; not an LLM comparison.

Run WITHOUT consulting retrospective gold labels. This is diagnosis, not a
new independent holdout or research quality certificate.
"""
from __future__ import annotations
import ast
import builtins
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))

from semantic_runtime import discover_and_ground
from semantic_runtime import discovery
from semantic_runtime.constrained_v5 import classify_explicit
from tests.test_semantic_runtime_v5_grammar import make_field_task,make_grammar


def _assignment(ir,case_id):
    a=next((x for x in ir["heldout_assignments"] if x["example_id"]==case_id),None)
    b=next((x for x in ir["abstentions"] if x["example_id"]==case_id),None)
    return {"slot_id":a["slot_id"],"polarity":a["polarity"],"modality":a["modality"]} if a else {"status":b["status"]} if b else {"status":"MISSING"}

def _replay(task, target_id, new_text):
    task=copy.deepcopy(task)
    for ex in task["visible"]["heldout_examples"]:
        if ex["example_id"]==target_id:
            ex["raw_text"]=new_text
            break
    else:
        raise ValueError("MISSING_TARGET")
    v1=discover_and_ground(task)
    v5=classify_explicit(task,make_grammar())
    decision=next(x for x in v5["decisions"] if x["example_id"]==target_id)
    return {"text":new_text,
            "tokens":discovery.tokens(discovery.mask_entities(new_text,next(x for x in task["visible"]["heldout_examples"] if x["example_id"]==target_id)["entity_registry"])),
            "v1":_assignment(v1,target_id),
            "v5":{"status":decision["status"],"slot_id":decision.get("slot_id")}}

def _blocked_file_reads(task):
    """Dynamic proof only for this exercised execution path, not all possible paths."""
    block=[]
    original_open=builtins.open
    original_path_open=Path.open
    def deny(path,*args,**kwargs):
        p=str(path).lower()
        if "/evaluation/" in p or "/results/" in p or "historical_labels" in p or "/oracle/" in p:
            block.append(p)
            raise RuntimeError("PREDICTOR_ATTEMPTED_TO_READ_EVALUATION")
        return original_open(path,*args,**kwargs)
    def deny_path(self,*args,**kwargs):
        p=str(self).lower()
        if "/evaluation/" in p or "/results/" in p or "historical_labels" in p or "/oracle/" in p:
            block.append(p)
            raise RuntimeError("PREDICTOR_ATTEMPTED_TO_READ_EVALUATION")
        return original_path_open(self,*args,**kwargs)
    with patch("builtins.open",deny),patch.object(Path,"open",deny_path):
        ir=discover_and_ground(task)
        pred=classify_explicit(task,make_grammar())
    return {"blocked_read_attempts":block,
            "provenance":"Only the exercised production prediction path, with already-built test fixture",
            "assignment_count":len(ir["heldout_assignments"]),
            "v5_decision_count":len(pred["decisions"])}

def _imports_and_constants():
    files=("semantic_runtime/runtime.py",
           "semantic_runtime/discovery.py",
           "semantic_runtime/public_hypotheses.py",
           "semantic_runtime/constrained_v5.py",
           "tools/run_capability_retention_historical_v1.py")
    out={}
    for p in files:
        source=(ROOT/p).read_text(encoding="utf-8")
        tree=ast.parse(source)
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node,ast.ImportFrom):
                imports.append(("."*node.level)+(node.module or ""))
        out[p]={"imports":sorted(set(imports)),
                "mentions_hidden_gold": any(k in source for k in ('gold_action','LABELS=','answer_key')),
                "file_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest()}
    return out

def main():
    task=make_field_task()
    counterfactuals={
        "H07_japanese":(
            "Claim K を審査開始する",
            "Claim K を審査終了する",
            "Claim K よくわからない",
            "Claim K xyzqvblp",
        ),
        "H10_english":(
            "Please open review for Claim N",
            "Please close review for Claim N",
            "Please do not open review for Claim N",
            "Please ignore review for Claim N",
        )
    }
    data={}
    for name,forms in counterfactuals.items():
        eid=name.split("_")[0]
        data[name]=[_replay(task,eid,t) for t in forms]
    # Training slot IDs are known through the example behavior in supplied
    # demonstrations. Only test **sensitivity**, not correctness vs gold.
    no_japanese_semantic_resolution=(
        data["H07_japanese"][0]["v1"]["slot_id"] ==
        data["H07_japanese"][1]["v1"]["slot_id"]
    )
    gate_denies_valid_paraphrase=data["H10_english"][0]["v5"]["status"]=="ABSTAIN_UNSUPPORTED_OR_AMBIGUOUS"
    all_japanese_denied=all(r["v5"]["status"]=="ABSTAIN_UNSUPPORTED_OR_AMBIGUOUS" for r in data["H07_japanese"])
    no_eval_file_access=_blocked_file_reads(task)
    code=_imports_and_constants()
    historical=(ROOT/"tools/run_capability_retention_historical_v1.py").read_text(encoding="utf-8")
    issues={
        "japanese_antonym_did_not_flip_v1_slot":no_japanese_semantic_resolution,
        "v5_valid_non_template_phrase_rejected":gate_denies_valid_paraphrase,
        "v5_all_japanese_forms_rejected":all_japanese_denied,
        "historical_runner_imports_test_fixture_with_known_target_labels":
            "from tests.test_semantic_runtime_v5_grammar import make_field_task,make_grammar" in historical,
        "historical_runner_maps_training_ids_to_expected_action_by_hand":
            'frozenset(("T01","T02"))' in historical and ':"OPEN"' in historical,
        "historical_oracle_is_posthoc_labels":
            'labels=json.loads(raw.decode("utf-8"))' in historical,
        "production_runtime_reads_gold_during_exercised_prediction":
            bool(no_eval_file_access["blocked_read_attempts"]),
        "v5_config_has_preapproved_action_labels":
            "review_open" in json.dumps(make_grammar()) and "review_close" in json.dumps(make_grammar()),
    }
    print(json.dumps({
        "protocol":"ISSUE57_QA_CONTAMINATION_STATIC_AND_COUNTERFACTUAL_V1",
        "terminal":"FULL_FOUR_ARM_COMPARISON_BLOCKED_BY_CONFOUNDERS" if any(v for k,v in issues.items() if k!="production_runtime_reads_gold_during_exercised_prediction") else "NO_CONFOUNDERS_OBSERVED",
        "mode":"AUDIT_ONLY_NO_GOLD_READ_NO_LLM_INFERENCE",
        "counterfactuals":data,
        "findings":issues,
        "dynamic_gold_read_probe":no_eval_file_access,
        "static_import_graph":code,
        "disclaimer":"Prior 16 fixtures are development-visible; counterfactual probes are local mechanism tests, never independent holdout or quality estimates.",
        "recommended_gate":"New independent input+label authority and genuine LLM0/V1/V4/V5 output cache; no replay of existing fixture as independent evidence."
    },ensure_ascii=False,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
