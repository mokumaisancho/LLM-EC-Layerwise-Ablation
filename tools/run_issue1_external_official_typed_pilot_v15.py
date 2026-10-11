#!/usr/bin/env python3
"""Source-independent narrow scope S3/S4 typed pilot; NOT original Phase1 gold."""
from __future__ import annotations
import hashlib
import json
import urllib.request

UPSTREAM_REPO="json-schema-org/JSON-Schema-Test-Suite"
UPSTREAM_COMMIT="7de0e6a06031ede80028583dd45d0cd41105ae5b"
FILES={"required.json":"17db8939e75837bc0c7b913300fbe9c8f357961c",
       "properties.json":"eb66fa8bd0b894eef9de333b35c746dc7036ca4c"}
BASE="https://raw.githubusercontent.com/"+UPSTREAM_REPO+"/"+UPSTREAM_COMMIT+"/tests/draft2020-12/"
def gitblob(raw:bytes):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def get(name):
    with urllib.request.urlopen(BASE+name,timeout=15) as resp:
        return resp.read()

def run(fetch=get):
    from jsonschema import Draft202012Validator
    import jsonschema
    source=[]
    total=0
    mixed=0
    matched=0
    num_true=0
    num_false=0
    for name,pin in FILES.items():
        b=fetch(name)
        if gitblob(b)!=pin:
            raise ValueError("EXTERNAL_PUBLISHED_UPSTREAM_BLOB_CHANGED:"+name)
        rows=json.loads(b.decode())
        if not isinstance(rows,list) or not rows:
            raise ValueError("NO_PUBLISHED_CASES:"+name)
        for gi,group in enumerate(rows):
            schema=group["schema"]
            Draft202012Validator.check_schema(schema)
            validator=Draft202012Validator(schema)
            tests=group["tests"]
            valid=[]
            got=[]
            if len({str(x.get("description")) for x in tests})!=len(tests):
                raise ValueError("DUPLICATE_UPSTREAM_CASE_DESCRIPTION:"+name)
            for case in tests:
                expected=case["valid"]
                if type(expected) is not bool:
                    raise ValueError("INVALID_EXTERNAL_GOLD")
                # Validator sees only schema and public sample, not gold.
                errors=list(validator.iter_errors(case["data"]))
                actual=not bool(errors)
                valid.append(expected)
                got.append(actual)
                matched+=int(expected==actual)
                total+=1
                num_true+=int(expected)
                num_false+=int(not expected)
            mixed+=int(len(set(valid))>1)
            source.append({"file":name,"group":gi,
                           "publisher_gold_selected":sum(valid),
                           "independent_validator_selected":sum(got),
                           "all_candidates_agree":valid==got,
                           "S4_complete_only_under_JSON_SCHEMA_validity":
                               all(valid==got),
                           "not_real_task_termination":True})
    if matched!=total or total!=46 or len(source)!=11 or mixed<7:
        raise ValueError("INDEPENDENT_SOURCE_VALIDATOR_DISAGREEMENT")
    return {
        "protocol":"ISSUE1_UPSTREAM_THIRD_PARTY_TYPED_S3_S4_PILOT_V1",
        "upstream_repo":UPSTREAM_REPO,"upstream_commit":UPSTREAM_COMMIT,
        "exact_upstream_git_blobs":FILES,
        "official_source_tests":total,"published_expected_labels_matched":matched,
        "all_admissible_groups":len(source),"mixed_admissibility_groups":mixed,
        "gold_valid":num_true,"gold_invalid":num_false,
        "validator_library":"jsonschema","validator_version":getattr(jsonschema,"__version__","unknown"),
        "upstream_publishers_distinct_from_this_research_project":True,
        "source_custody_is_externally_published_not_expert_double_adjudication":True,
        "gold_visible_to_current_scoring_script":True,
        "model_predictor_was_not_run":True,
        "complete_obligations_only_for_JSON_Schema_validation":True,
        "S3_arbitrary_natural_language_semantics_certified":False,
        "S4_real_world_task_complete_inventory_certified":False,
        "original_all_layer_AE_certified":False,
        "original_MVP18_pass_raised":False,
        "status":"EXTERNAL_PUBLIC_TYPED_SEMANTIC_PILOT_COMPLETE_NOT_ORIGINAL_SCIENCE",
        "case_groups":source,
    }
def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--out")
    a=p.parse_args()
    try:
        x=run()
        txt=json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False)+"\n"
        if a.out:
            from pathlib import Path
            target=Path(a.out)
            if target.is_symlink():raise ValueError("OUTPUT_SYMLINK")
            target.write_text(txt)
        print(json.dumps({k:x[k] for k in ("status","official_source_tests","published_expected_labels_matched","S3_arbitrary_natural_language_semantics_certified","S4_real_world_task_complete_inventory_certified")}))
        return 0
    except Exception as exc:
        print(json.dumps({"terminal":"PILOT_INTEGRITY_BLOCKED","error":str(exc)[:200]}))
        return 3
if __name__=="__main__":
    raise SystemExit(main())
