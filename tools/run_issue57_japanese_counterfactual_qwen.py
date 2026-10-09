#!/usr/bin/env python3
"""Counterfactual Japanese-language diagnostic after frozen capacity sweep.

Development-visible mechanism test only. This tests language sensitivity, not
independent semantic accuracy, V4 authorization, or full quality preservation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from semantic_runtime import discover_and_ground
from tests.test_semantic_runtime_v5_grammar import make_field_task
from tools.run_issue1_pinned_smollm_probe import PROMPT_TEMPLATE, digest, run_one
from tools.run_issue1_qwen25_capacity_format_sweep import MODELS, verify
from tools.run_issue1_native_grammar_ablation import GRAMMAR

# Pre-registered in the earlier issue #57 historical diagnostic (not new gold).
CONTRASTS = {
    "jp_start": "Claim K を審査開始する",
    "jp_end": "Claim K を審査終了する",
    "jp_unknown": "Claim K よくわからない",
    "nonsense_ascii": "Claim K xyzqvblp",
}


def diagnostic(model_dir: Path, llama: Path) -> dict:
    for m in MODELS.values():
        verify(model_dir/m["filename"],m)
    out=[]
    for name,raw in CONTRASTS.items():
        task=make_field_task()
        changed=0
        for example in task["visible"]["heldout_examples"]:
            if example["example_id"]=="H07":
                example["raw_text"]=raw
                changed+=1
        if changed!=1:
            raise ValueError("H07_NOT_FOUND_ONCE")
        ground=discover_and_ground(task)
        found=next((a for a in ground["heldout_assignments"] if a["example_id"]=="H07"),None)
        status=next((a for a in ground["abstentions"] if a["example_id"]=="H07"),None)
        if found is None and status is None:
            raise ValueError("V1_MISSING_H07")
        prompt=PROMPT_TEMPLATE.format(input=raw)
        predictions={}
        for key,info in MODELS.items():
            predictions[key]={}
            for treatment,grammar in (("unconstrained",None),("native_gbnf",GRAMMAR)):
                actual=run_one(llama,model_dir/info["filename"],prompt,seconds=60,grammar=grammar)
                predictions[key][treatment]={
                    "raw": actual["raw_response"],
                    "strict_label": actual["parsed_action"],
                    "stdout_sha256":actual["full_cli_stdout_sha256"],
                }
        out.append({
            "contrast_id":name,
            "raw_input":raw,
            "input_sha256":digest(raw.encode()),
            "prompt_sha256":digest(prompt.encode()),
            "deterministic_v1_assignment": found,
            "deterministic_v1_abstention":status,
            "actual_model_predictions":predictions,
        })
    v1_versions={json.dumps(x["deterministic_v1_assignment"],sort_keys=True,ensure_ascii=False)
                 for x in out}
    return {
        "protocol":"ISSUE57_JAPANESE_CONTRAST_ACTUAL_QWEN_CAPACITY_AND_V1_V1",
        "root_issue":1,"issue":57,"fixture_origin":"EXPOSED_DEVELOPMENT_COUNTERFACTUALS",
        "source_grounder":"semantic_runtime.discover_and_ground",
        "models":MODELS,
        "model_invocations":len(out)*len(MODELS)*2,
        "contrasts":out,
        "v1_same_full_assignment_across_four_texts":len(v1_versions)==1,
        "llm_japanese_generalization_proven":False,
        "blind_gold":False,
        "v4_owner_authorization":False,
        "scientific_four_arm_study":"NOT_RUN",
        "ecv4_closure_allowed":False,
        "terminal":"JAPANESE_COUNTERFACTUAL_DEV_DIAGNOSTIC_ONLY"
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model-dir",type=Path,required=True)
    p.add_argument("--llama-cli",type=Path,required=True)
    a=p.parse_args()
    try:
        print(json.dumps(diagnostic(a.model_dir,a.llama_cli),indent=2,ensure_ascii=False,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"protocol":"ISSUE57_JAPANESE_CONTRAST_ACTUAL_QWEN_CAPACITY_AND_V1_V1",
                          "terminal":"FAIL_CLOSED","error":type(exc).__name__+":"+str(exc)[:500]}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
