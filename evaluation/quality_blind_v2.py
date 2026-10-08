"""Issue #58: blind four-arm capability evaluation protocol (standard library only).

This is a post-hoc EVALUATOR. Not an inference engine, trainer, oracle,
gold-generator, action mapping, or a mechanism to certify independence.
All arms must be captured outside this module BEFORE private gold is opened.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import defaultdict
from typing import Any

ARMS = ("LLM0", "V1", "V4", "V5")
ACTIONS = frozenset(("OPEN", "CLOSE", "ABSTAIN"))
PUBLIC_PROTOCOL = "CAPABILITY_BLIND_PUBLIC_V2"
GOLD_PROTOCOL = "CAPABILITY_BLIND_GOLD_V2"
ARM_PROTOCOL = "CAPABILITY_BLIND_ARM_V2"
SEAL_PROTOCOL = "CAPABILITY_BLIND_SEAL_V2"
RESULT_PROTOCOL = "CAPABILITY_BLIND_RESULT_V2"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HISTORICAL_ID = re.compile(r"H(?:0[1-9]|1[0-6])\Z")
SUSPICIOUS = frozenset(("gold", "gold_action", "oracle", "answer", "answer_key",
                        "expected", "expected_action", "scorer", "correct_label",
                        "label", "labels", "reference_answer", "reference_label",
                        "ground_truth", "solution", "target_action"))
MAX_CASES = 10000


class BlindProtocolError(ValueError):
    pass


def deny(reason: str) -> None:
    raise BlindProtocolError(reason)


def unique_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject ambiguous duplicate object members before evaluation or hashing."""
    result = {}
    for key, value in pairs:
        if key in result:
            deny("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def sha(v: Any) -> str:
    return hashlib.sha256(canon(v).encode("utf-8")).hexdigest()


def _fields(obj: Any, required: set[str], reason: str) -> None:
    if not isinstance(obj, dict) or set(obj) != required:
        deny(reason)


def _check_no_gold(obj: Any) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str) or k.lower() in SUSPICIOUS or k.lower().startswith(("gold_", "oracle_", "answer_")):
                deny("PUBLIC_CONTAINS_EVALUATION_KEY")
            _check_no_gold(v)
    elif isinstance(obj, list):
        for v in obj:
            _check_no_gold(v)


def validate_public(public: Any) -> dict[str, Any]:
    _fields(public, {"protocol", "study_id", "ontology", "task_context",
                     "cases", "public_provenance"}, "PUBLIC_FIELDS_INVALID")
    if public["protocol"] != PUBLIC_PROTOCOL:
        deny("PUBLIC_PROTOCOL_INVALID")
    sid = public["study_id"]
    if not isinstance(sid, str) or not 8 <= len(sid) <= 80:
        deny("STUDY_ID_INVALID")
    _check_no_gold(public)
    _fields(public["ontology"], {"actions"}, "ONTOLOGY_FIELDS_INVALID")
    if public["ontology"]["actions"] != ["OPEN", "CLOSE", "ABSTAIN"]:
        deny("ONTOLOGY_MUST_BE_FROZEN")
    provenance = public["public_provenance"]
    _fields(provenance, {"source_id", "independent_author", "training_overlap_reviewed",
                         "prior_v5_fixture_excluded"}, "PUBLIC_PROVENANCE_INVALID")
    if not isinstance(provenance["source_id"], str) or not provenance["source_id"]:
        deny("SOURCE_ID_INVALID")
    if not isinstance(provenance["independent_author"], str) or not provenance["independent_author"]:
        deny("PUBLIC_AUTHOR_MISSING")
    if provenance["training_overlap_reviewed"] is not True or provenance["prior_v5_fixture_excluded"] is not True:
        deny("PROVENANCE_NOT_REVIEWED_OR_HISTORICAL_OVERLAP")
    _check_no_gold(public["task_context"])
    cases = public["cases"]
    if not isinstance(cases, list) or not 4 <= len(cases) <= MAX_CASES:
        deny("PUBLIC_CASE_COUNT_INVALID")
    index, text_seen = {}, set()
    contrast = defaultdict(list)
    for row in cases:
        _fields(row, {"case_id", "text", "entity_registry", "contrast_pair"},
                "PUBLIC_CASE_FIELDS_INVALID")
        cid, text, cp = row["case_id"], row["text"], row["contrast_pair"]
        if not isinstance(cid, str) or len(cid) > 80 or not cid or cid in index:
            deny("DUPLICATE_CASE_ID")
        if HISTORICAL_ID.fullmatch(cid):
            deny("HISTORICAL_V5_ID_FORBIDDEN")
        if not isinstance(text, str) or not text.strip() or len(text) > 5000:
            deny("PUBLIC_TEXT_INVALID")
        compact = re.sub(r"\s+", " ", text).casefold().strip()
        if compact in text_seen:
            deny("DUPLICATE_CASE_TEXT")
        text_seen.add(compact)
        if not isinstance(row["entity_registry"], dict) or not row["entity_registry"]:
            deny("ENTITY_REGISTRY_REQUIRED")
        if cp is not None and (not isinstance(cp, str) or not cp or len(cp) > 80):
            deny("CONTRAST_PAIR_INVALID")
        if cp is not None:
            contrast[cp].append(cid)
        index[cid] = row
    if not contrast or any(len(ids) != 2 for ids in contrast.values()):
        deny("TWO_CASE_CONTRAST_PAIR_REQUIRED")
    return index


def validate_gold(gold: Any, public: dict[str, Any]) -> dict[str, Any]:
    _fields(gold, {"protocol", "study_id", "labels", "gold_provenance"}, "GOLD_FIELDS_INVALID")
    if gold["protocol"] != GOLD_PROTOCOL or gold["study_id"] != public["study_id"]:
        deny("GOLD_IDENTITY_INVALID")
    prov = gold["gold_provenance"]
    _fields(prov, {"independent_adjudicator", "adjudication_protocol", "annotation_complete_before_predictions"},
            "GOLD_PROVENANCE_FIELDS_INVALID")
    if not all(isinstance(prov[k], str) and prov[k] for k in
               ("independent_adjudicator", "adjudication_protocol")):
        deny("GOLD_ADJUDICATOR_MISSING")
    if prov["independent_adjudicator"] in (public["public_provenance"]["source_id"],public["public_provenance"]["independent_author"]):
        deny("GOLD_SOURCE_NOT_SEPARATED")
    if prov["annotation_complete_before_predictions"] is not True:
        deny("GOLD_NOT_FROZEN_BEFORE_PREDICTION")
    reference = validate_public(public)
    labels = {}
    if not isinstance(gold["labels"],list):
        deny("GOLD_LABELS_NOT_LIST")
    for r in gold["labels"]:
        _fields(r, {"case_id", "gold_action", "capability", "critical", "tail"},
                "GOLD_LABEL_FIELDS_INVALID")
        cid = r["case_id"]
        if cid not in reference or cid in labels:
            deny("GOLD_DUPLICATE_OR_UNKNOWN_CASE")
        if r["gold_action"] not in ACTIONS:
            deny("GOLD_INVALID_ACTION")
        if not isinstance(r["capability"], str) or not r["capability"]:
            deny("GOLD_CAPABILITY_INVALID")
        if type(r["critical"]) is not bool or type(r["tail"]) is not bool:
            deny("GOLD_FLAGS_INVALID")
        labels[cid] = r
    if set(labels) != set(reference):
        deny("GOLD_INCOMPLETE")
    pairs = defaultdict(list)
    for c in reference.values():
        if c["contrast_pair"] is not None:
            pairs[c["contrast_pair"]].append(labels[c["case_id"]]["gold_action"])
    if any(len(set(v)) < 2 for v in pairs.values()):
        deny("GOLD_CONTRAST_NOT_DISCRIMINATIVE")
    return labels


def make_precommit(public: dict, gold: dict, *, salt: str) -> dict:
    """Called by independent custodian, never in prediction process.

    Publish only the returned hash commitment, keep gold AND salt private.
    """
    validate_gold(gold, public)
    if not isinstance(salt, str) or len(salt) < 32:
        deny("HIGH_ENTROPY_SALT_REQUIRED")
    return {"protocol":"CAPABILITY_GOLD_PRECOMMIT_V2",
            "study_id":public["study_id"],
            "public_sha256":sha(public),
            "gold_commitment":hashlib.sha256((salt+"\n"+canon(gold)).encode()).hexdigest()}


def _raw_decode(row: dict) -> str:
    _fields(row, {"case_id", "input_sha256", "raw_output", "raw_sha256"}, "RAW_ROW_FIELDS_INVALID")
    if not isinstance(row["raw_output"], str) or len(row["raw_output"]) > 16384:
        deny("RAW_OUTPUT_INVALID")
    if hashlib.sha256(row["raw_output"].encode()).hexdigest() != row["raw_sha256"]:
        deny("RAW_OUTPUT_TAMPERED")
    try:
        parsed = json.loads(row["raw_output"], object_pairs_hook=unique_object_pairs)
    except (ValueError,TypeError):
        return "FORMAT_ERROR"
    if not isinstance(parsed,dict) or set(parsed)!={"action"} or not isinstance(parsed["action"],str) or parsed["action"] not in ACTIONS:
        return "FORMAT_ERROR"
    return parsed["action"]


def validate_arm(arm: dict, public: dict) -> dict[str, str]:
    _fields(arm, {"protocol", "study_id", "arm", "public_sha256",
                  "runtime_source_sha256", "run_spec_sha256", "model_or_runtime_ref",
                  "adapter_sha256", "raw_rows", "raw_rows_sha256"},
            "ARM_FIELDS_INVALID")
    if arm["protocol"] != ARM_PROTOCOL or arm["study_id"] != public["study_id"] or arm["arm"] not in ARMS:
        deny("ARM_IDENTITY_INVALID")
    for key in ("public_sha256", "runtime_source_sha256", "run_spec_sha256",
                "adapter_sha256", "raw_rows_sha256"):
        if not isinstance(arm[key], str) or not HEX64.fullmatch(arm[key]):
            deny("ARM_SHA_INVALID")
    if arm["public_sha256"] != sha(public):
        deny("ARM_PUBLIC_INPUT_DRIFT")
    if not isinstance(arm["model_or_runtime_ref"], str) or not arm["model_or_runtime_ref"]:
        deny("ARM_SOURCE_REF_REQUIRED")
    rows = arm["raw_rows"]
    if not isinstance(rows, list) or sha(rows) != arm["raw_rows_sha256"]:
        deny("ARM_RAW_ROW_COMMITMENT_INVALID")
    index = validate_public(public)
    results = {}
    for row in rows:
        if not isinstance(row, dict):
            deny("ARM_ROW_NOT_OBJECT")
        cid = row.get("case_id")
        if cid not in index or cid in results:
            deny("ARM_CASE_ID_DUPLICATE_OR_UNKNOWN")
        input_hash = sha({"text":index[cid]["text"],"entity_registry":index[cid]["entity_registry"]})
        if row.get("input_sha256") != input_hash:
            deny("ARM_PER_CASE_INPUT_TAMPERED")
        results[cid] = _raw_decode(row)
    if set(results) != set(index):
        deny("ARM_INCOMPLETE_COVERAGE")
    return results


def _confusion(gold: dict, decisions: dict) -> dict:
    out = {"correct":0,"format_failures":0,"legitimate_total":0,"legitimate_correct":0,
           "legitimate_false_refusals":0,"wrong_action":0,
           "invalid_total":0,"invalid_false_action":0,"critical_loss_ids":[],
           "tail_total":0,"tail_correct":0}
    by_capability = defaultdict(lambda:{"correct":0,"total":0})
    for cid, g in gold.items():
        answer,pred = g["gold_action"],decisions[cid]
        valid = pred==answer
        out["correct"]+=int(valid)
        out["format_failures"]+=int(pred=="FORMAT_ERROR")
        by_capability[g["capability"]]["total"]+=1
        by_capability[g["capability"]]["correct"]+=int(valid)
        if g["tail"]:
            out["tail_total"]+=1
            out["tail_correct"]+=int(valid)
        if answer=="ABSTAIN":
            out["invalid_total"]+=1
            out["invalid_false_action"]+=int(pred in ("OPEN","CLOSE"))
        else:
            out["legitimate_total"]+=1
            out["legitimate_correct"]+=int(valid)
            out["legitimate_false_refusals"]+=int(pred=="ABSTAIN")
            out["wrong_action"]+=int(pred not in (answer,"ABSTAIN"))
    out["accuracy"]=out["correct"]/len(gold)
    out["capabilities"]=dict(sorted(by_capability.items()))
    return out


def score(public: dict, gold: dict, arms: dict, seal: dict, *, salt: str) -> dict:
    """All input/output commitments required. Does NOT certify provenance.

    Every asserted provenance value is self-attested: manual independent review
    is required to make any claim about untouched/unseen data or blindness.
    """
    cases=validate_public(public)
    labels=validate_gold(gold,public)
    _fields(seal,{"protocol","study_id","public_sha256","gold_commitment",
                  "arm_raw_commitments","gold_access_after_arms","independent_review"},
            "SEAL_FIELDS_INVALID")
    if seal["protocol"] != SEAL_PROTOCOL or seal["study_id"] != public["study_id"]:
        deny("SEAL_IDENTITY_INVALID")
    if seal["public_sha256"] != sha(public):
        deny("SEAL_PUBLIC_DRIFT")
    commitment=make_precommit(public,gold,salt=salt)
    if commitment["gold_commitment"] != seal["gold_commitment"]:
        deny("GOLD_REVEAL_PRECOMMIT_MISMATCH")
    if set(arms) != set(ARMS) or set(seal["arm_raw_commitments"])!=set(ARMS):
        deny("FOUR_GENUINE_ARMS_REQUIRED")
    _fields(seal["independent_review"],{"status","review_ref"},"REVIEW_FIELDS_INVALID")
    if seal["independent_review"]["status"] not in ("PENDING","EXTERNALLY_REVIEWED"):
        deny("REVIEW_STATUS_INVALID")
    if not isinstance(seal["independent_review"]["review_ref"],str):
        deny("REVIEW_REF_INVALID")
    if seal["gold_access_after_arms"] is not True:
        deny("GOLD_ACCESS_CHRONOLOGY_INVALID")
    pred={}
    for name in ARMS:
        if arms[name]["arm"]!=name or seal["arm_raw_commitments"][name] != sha(arms[name]):
            deny("ARM_SEAL_DRIFT")
        pred[name]=validate_arm(arms[name],public)
    metrics={name:_confusion(labels,pred[name]) for name in ARMS}
    transitions={}
    losses=[]
    for predecessor,successor in zip(ARMS,ARMS[1:]):
        loss, gain, abstain = [],[],[]
        for cid,g in labels.items():
            good_before=pred[predecessor][cid]==g["gold_action"]
            good_after=pred[successor][cid]==g["gold_action"]
            if good_before and not good_after:
                loss.append(cid)
                if pred[successor][cid]=="ABSTAIN" and g["gold_action"]!="ABSTAIN":
                    abstain.append(cid)
            if not good_before and good_after:
                gain.append(cid)
        transitions[f"{predecessor}_TO_{successor}"]={
            "lost":sorted(loss),"correct_to_abstain":sorted(abstain),"gained":sorted(gain)}
        losses.extend(loss)
    pair_errors={}
    for name in ARMS:
        failures=[]
        for pair in sorted({x["contrast_pair"] for x in cases.values()}-{None}):
            group=[cid for cid,c in cases.items() if c["contrast_pair"]==pair]
            if len({pred[name][cid] for cid in group})<2:
                failures.append(pair)
        pair_errors[name]=failures
    anchor_losses={name:sorted(
        cid for cid,g in labels.items() if pred["LLM0"][cid]==g["gold_action"]
        and pred[name][cid]!=g["gold_action"]) for name in ARMS[1:]}
    critical_losses={name:[cid for cid in anchor_losses[name] if labels[cid]["critical"]]
                     for name in ARMS[1:]}
    tail_losses={name:[cid for cid in anchor_losses[name] if labels[cid]["tail"]]
                 for name in ARMS[1:]}
    any_adjacent_correct_loss=any(bool(t["lost"]) for t in transitions.values())
    regression=(
        any_adjacent_correct_loss or bool(any(critical_losses.values())) or bool(any(tail_losses.values()))
        or any(metrics[x]["legitimate_correct"] < metrics["LLM0"]["legitimate_correct"]
               for x in ARMS[1:])
        or any(metrics[x]["invalid_false_action"] > metrics["LLM0"]["invalid_false_action"]
               for x in ARMS[1:])
        or bool(any(pair_errors.values()))
    )
    return {
        "protocol":RESULT_PROTOCOL,
        "terminal":"REVIEW_REQUIRED_SCORES_ARE_NOT_SCIENTIFIC_CERTIFICATION",
        "regression_on_supplied_labels":regression,
        "any_adjacent_correct_to_incorrect":any_adjacent_correct_loss,
        "quality_preservation_certified":False,
        "external_independence_verified_by_evaluator":False,
        "public_sha256":sha(public),
        "gold_commitment":commitment["gold_commitment"],
        "case_count":len(cases),"arm_metrics":metrics,
        "adjacent_transitions":transitions,"anchor_losses":anchor_losses,
        "critical_anchor_losses":critical_losses,"tail_anchor_losses":tail_losses,
        "contrast_pair_non_discrimination":pair_errors,
        "critical_note":"Independent source, genuine model inference, freeze chronology and no training overlap REQUIRE separate review; hashes/self-declarations alone cannot prove any of them."
    }


__all__=["validate_public","validate_gold","validate_arm","make_precommit","score",
         "sha","canon","BlindProtocolError","ARMS"]
