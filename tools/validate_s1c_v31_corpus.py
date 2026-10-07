from __future__ import annotations

import argparse
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from s1c_v31_public_hypotheses import (
    EVALUATION_PROBE_INDICES,
    PROBE_LAYOUT,
    PUBLIC_HYPOTHESES,
    apply_code,
    candidates,
    code_key,
    evaluation_predictions,
    probe_input,
    public_manifest,
)

PROTOCOL = "S1C_V31_INDEPENDENT_ORACLE_VALIDATION_V1"
AUTHORITY = "S1C_V31_INDEPENDENT_ORACLE_VALIDATOR_V1"
STRUCTURAL_DESCRIPTOR = (
    "UNKNOWN_PARTITION_FROM_DISTINCT_PARTIAL_TRANSITIONS_WITH_PUBLIC_GENERIC_HYPOTHESIS"
    "__UNSEEN_PROBE_PREDICTION__RAW_LANGUAGE_TRANSFER"
)

# Independent declarative reference. This module does not import the corpus generator.
REFERENCE = {
    "V311": {
        "arg_types": ["T01", "T02"],
        "A": {"code": ("SET1", "KEEP", "KEEP"), "train": ["couples with", "binds to"], "held": "may connect with", "polarity": "POS", "modality": "POSSIBLE"},
        "B": {"code": ("SET0", "KEEP", "KEEP"), "train": ["decouples from", "disconnects from"], "held": "separates from", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V312": {
        "arg_types": ["T01"],
        "A": {"code": ("SET1", "KEEP", "KEEP"), "train": ["reserves", "holds in reserve"], "held": "sets aside in reserve", "polarity": "POS", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "SET1", "KEEP"), "train": ["releases reservation on", "frees from reservation"], "held": "removes the reservation from", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V313": {
        "arg_types": ["T01", "T02"],
        "A": {"code": ("SET0", "KEEP", "KEEP"), "train": ["hands control to", "passes control to"], "held": "transfers control to", "polarity": "POS", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "SET1", "KEEP"), "train": ["takes control back from", "recovers control from"], "held": "reclaims control from", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V314": {
        "arg_types": ["T01"],
        "A": {"code": ("KEEP", "SET0", "KEEP"), "train": ["reveals", "makes visible"], "held": "does not reveal", "polarity": "NEG", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "KEEP", "SET1"), "train": ["conceals", "keeps hidden"], "held": "keeps concealed", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V315": {
        "arg_types": ["T01", "T02"],
        "A": {"code": ("KEEP", "SET0", "KEEP"), "train": ["mounts on", "attaches as a mount to"], "held": "is mounted onto", "polarity": "POS", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "KEEP", "SET0"), "train": ["unmounts from", "removes the mount from"], "held": "is detached from", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V316": {
        "arg_types": ["T01"],
        "A": {"code": ("KEEP", "KEEP", "SET1"), "train": ["subscribes", "enrolls for updates"], "held": "must subscribe", "polarity": "POS", "modality": "REQUIRED"},
        "B": {"code": ("KEEP", "KEEP", "SET0"), "train": ["unsubscribes", "leaves the update feed"], "held": "opts out of updates", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V317": {
        "arg_types": ["T01", "T02"],
        "A": {"code": ("FLIP", "KEEP", "KEEP"), "train": ["pairs with", "forms a pair with"], "held": "is paired to", "polarity": "POS", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "FLIP", "KEEP"), "train": ["unpairs from", "dissolves the pair with"], "held": "is unpaired from", "polarity": "POS", "modality": "ASSERTED"},
    },
    "V318": {
        "arg_types": ["T01"],
        "A": {"code": ("FLIP", "KEEP", "KEEP"), "train": ["marks", "places a mark on"], "held": "labels as marked", "polarity": "POS", "modality": "ASSERTED"},
        "B": {"code": ("KEEP", "KEEP", "FLIP"), "train": ["unmarks", "clears the mark on"], "held": "removes the mark", "polarity": "POS", "modality": "ASSERTED"},
    },
}


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).lower()).strip()


def _phrase_hits(text: str, phrases: list[tuple[str, str, str]]) -> list[tuple[str, str]]:
    low = norm(text)
    hits = []
    for side, kind, phrase in phrases:
        if norm(phrase) in low:
            hits.append((side, kind))
    return hits


def _task_phrases(spec: dict[str, Any]) -> list[tuple[str, str, str]]:
    out = []
    for side in ("A", "B"):
        for phrase in spec[side]["train"]:
            out.append((side, "TRAIN", phrase))
        out.append((side, "HELD", spec[side]["held"]))
    return out


def _validate_public_manifest(task: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    visible = task["visible"]
    actual = dict(visible.get("public_behavior_hypothesis") or {})
    expected = public_manifest()
    expected.pop("probe_layout", None)
    expected["evaluation_probe_inputs"] = [
        {"probe_id": f"Q{i:02d}", "before": list(probe_input(i))}
        for i in EVALUATION_PROBE_INDICES
    ]
    if actual != expected:
        failures.append({"gate": "PUBLIC_HYPOTHESIS_MANIFEST_MISMATCH"})
    if visible.get("evaluation_probes") != expected["evaluation_probe_inputs"]:
        failures.append({"gate": "EVALUATION_PROBE_INPUT_MISMATCH"})


def _partition_pairings(indices: tuple[int, int, int, int]):
    a, b, c, d = indices
    return (((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c)))


def validate_task(task: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    tid = str(task.get("task_id") or "")
    spec = REFERENCE.get(tid)
    if spec is None:
        return {}, [{"gate": "UNKNOWN_TASK_ID", "task_id": tid}]

    if task.get("structural_descriptor") != STRUCTURAL_DESCRIPTOR:
        failures.append({"gate": "STRUCTURAL_DESCRIPTOR_MISMATCH"})

    visible = task.get("visible")
    if not isinstance(visible, dict):
        return {}, [{"gate": "VISIBLE_OBJECT_REQUIRED"}]

    _validate_public_manifest(task, failures)

    serialized = json.dumps(visible, sort_keys=True, ensure_ascii=False)
    for forbidden in (
        '"target_code"',
        '"oracle"',
        '"family"',
        '"canonical_slot"',
        '"denotation"',
        '"semantic_gloss"',
        '"hidden"',
    ):
        if forbidden in serialized:
            failures.append({"gate": "VISIBLE_HIDDEN_REFERENCE_LEAKAGE", "token": forbidden})

    train = visible.get("training_examples")
    held = visible.get("heldout_examples")
    if not isinstance(train, list) or len(train) != 4:
        failures.append({"gate": "TRAINING_COUNT", "count": None if not isinstance(train, list) else len(train)})
        train = train if isinstance(train, list) else []
    if not isinstance(held, list) or len(held) != 3:
        failures.append({"gate": "HELDOUT_COUNT", "count": None if not isinstance(held, list) else len(held)})
        held = held if isinstance(held, list) else []

    expected_types = sorted(set(spec["arg_types"]))
    if visible.get("type_inventory") != expected_types:
        failures.append({"gate": "TYPE_INVENTORY_MISMATCH"})

    phrases = _task_phrases(spec)
    training_gold: dict[str, str] = {}
    side_members: dict[str, list[str]] = defaultdict(list)
    probe_sets = []
    bundles = []
    individual_candidate_counts = {}

    for ex in train:
        eid = str(ex.get("example_id") or "")
        hits = [x for x in _phrase_hits(str(ex.get("raw_text") or ""), phrases) if x[1] == "TRAIN"]
        if len(hits) != 1:
            failures.append({"gate": "TRAIN_PHRASE_ORACLE_NON_UNIQUE", "example_id": eid, "hits": hits})
            continue
        side = hits[0][0]
        code = spec[side]["code"]
        rows = ex.get("behavior_observations")
        if not isinstance(rows, list) or len(rows) != 2:
            failures.append({"gate": "TRAIN_OBSERVATION_COUNT", "example_id": eid})
            continue

        cand = candidates(rows)
        individual_candidate_counts[eid] = len(cand)
        if len(cand) < 2:
            failures.append({"gate": "SINGLE_EXAMPLE_IDENTIFIES_TARGET", "example_id": eid, "candidate_count": len(cand)})
        if tuple(code) not in cand:
            failures.append({"gate": "TRAIN_OBSERVATION_CONTRADICTS_TEXT_ORACLE", "example_id": eid})

        for row in rows:
            pid = str(row.get("probe_id") or "")
            if not pid.startswith("Q") or not pid[1:].isdigit():
                failures.append({"gate": "INVALID_TRAIN_PROBE_ID", "example_id": eid, "probe_id": pid})
                continue
            idx = int(pid[1:])
            if idx not in (0, 1, 2, 4):
                failures.append({"gate": "TRAIN_USES_EVALUATION_PROBE", "example_id": eid, "probe_id": pid})
            expected_after = list(apply_code(code, row.get("before") or []))
            if row.get("after") != expected_after:
                failures.append({"gate": "TRAIN_TRANSITION_RECOMPUTE_MISMATCH", "example_id": eid, "probe_id": pid})

        training_gold[eid] = code_key(code)
        side_members[side].append(eid)
        probe_sets.append(tuple(str(r.get("probe_id")) for r in rows))
        bundles.append(json.dumps(rows, sort_keys=True))

    if len(set(probe_sets)) != len(probe_sets):
        failures.append({"gate": "EXACT_PROBE_SUBSET_REUSE"})
    if len(set(bundles)) != len(bundles):
        failures.append({"gate": "EXACT_BEHAVIOR_BUNDLE_REUSE"})
    if sorted(len(v) for v in side_members.values()) != [2, 2]:
        failures.append({"gate": "TRUE_PARTITION_MEMBER_COUNT", "side_members": dict(side_members)})

    # Public-hypothesis identifiability; no scorer-only target library is used.
    if len(train) == 4:
        valid_pairings = []
        for pairing in _partition_pairings((0, 1, 2, 3)):
            resolved = []
            for pair in pairing:
                merged = []
                for index in pair:
                    merged.extend(train[index].get("behavior_observations") or [])
                c = candidates(merged)
                resolved.append(c)
            if all(len(c) == 1 for c in resolved) and resolved[0][0] != resolved[1][0]:
                valid_pairings.append(
                    {
                        "pairing": [list(x) for x in pairing],
                        "codes": [code_key(resolved[0][0]), code_key(resolved[1][0])],
                    }
                )
        if len(valid_pairings) != 1:
            failures.append({"gate": "NON_IDENTIFIABLE_PUBLIC_HYPOTHESIS_TASK", "valid_pairings": valid_pairings})
        else:
            pairing = valid_pairings[0]["pairing"]
            observed_partition = {
                frozenset(str(train[i].get("example_id")) for i in pair)
                for pair in pairing
            }
            gold_partition = {frozenset(side_members["A"]), frozenset(side_members["B"])}
            if observed_partition != gold_partition:
                failures.append({"gate": "PUBLIC_HYPOTHESIS_IDENTIFIES_WRONG_PARTITION", "valid_pairing": valid_pairings[0]})

    heldout_ref: dict[str, dict[str, Any]] = {}
    for ex in held:
        eid = str(ex.get("example_id") or "")
        raw = str(ex.get("raw_text") or "")
        low = norm(raw)
        if "unresolved between:" in low and " or " in low:
            a_hit = norm(spec["A"]["held"]) in low
            b_hit = norm(spec["B"]["held"]) in low
            if not (a_hit and b_hit):
                failures.append({"gate": "AMBIGUOUS_PHRASE_DOES_NOT_COVER_BOTH_TARGETS", "example_id": eid})
            heldout_ref[eid] = {"status": "AMBIGUOUS"}
            continue

        hits = [(side, kind) for side, kind in _phrase_hits(raw, phrases) if kind == "HELD"]
        if len(hits) != 1:
            failures.append({"gate": "HELDOUT_PHRASE_ORACLE_NON_UNIQUE", "example_id": eid, "hits": hits})
            continue
        side = hits[0][0]
        item = spec[side]
        args = ["E01"] + (["E02"] if len(spec["arg_types"]) == 2 else [])
        heldout_ref[eid] = {
            "status": "OK",
            "target_code": code_key(item["code"]),
            "arg_types": list(spec["arg_types"]),
            "arguments": args,
            "polarity": item["polarity"],
            "modality": item["modality"],
            "evaluation_probe_expected": evaluation_predictions(item["code"]),
        }

    if sum(1 for x in heldout_ref.values() if x.get("status") == "AMBIGUOUS") != 1:
        failures.append({"gate": "AMBIGUITY_COVERAGE_MISSING"})
    if sum(1 for x in heldout_ref.values() if x.get("status") == "OK") != 2:
        failures.append({"gate": "NORMAL_HELDOUT_REFERENCE_COUNT"})

    slot_refs = {}
    for side in ("A", "B"):
        code = spec[side]["code"]
        key = code_key(code)
        slot_refs[key] = {
            "arg_types": list(spec["arg_types"]),
            "evaluation_probe_expected": evaluation_predictions(code),
        }

    reference = {
        "authority": AUTHORITY,
        "task_id": tid,
        "training_gold": training_gold,
        "slot_references": slot_refs,
        "heldout": heldout_ref,
        "individual_candidate_counts": individual_candidate_counts,
    }
    return reference, failures


def validate_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    failures = []
    references = {}
    tasks = corpus.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != len(REFERENCE):
        failures.append({"gate": "TASK_COUNT", "count": None if not isinstance(tasks, list) else len(tasks)})
        tasks = tasks if isinstance(tasks, list) else []

    ids = [str(t.get("task_id") or "") for t in tasks]
    if len(set(ids)) != len(ids) or set(ids) != set(REFERENCE):
        failures.append({"gate": "TASK_ID_SET_MISMATCH", "ids": ids})

    for task in tasks:
        ref, task_failures = validate_task(task)
        tid = str(task.get("task_id") or "")
        if ref:
            references[tid] = ref
        for row in task_failures:
            failures.append({"task_id": tid, **row})

    return {
        "protocol": PROTOCOL,
        "authority": AUTHORITY,
        "pass": not failures,
        "terminal": "S1C_V31_ORACLE_VALIDATION_PASS" if not failures else "S1C_V31_ORACLE_VALIDATION_FAIL_CLOSED",
        "task_count": len(tasks),
        "failure_count": len(failures),
        "failures": failures,
        "references": references,
        "public_hypothesis_count": len(PUBLIC_HYPOTHESES),
        "generator_imported": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
    out = validate_corpus(corpus)
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {k: out[k] for k in ("protocol", "pass", "terminal", "task_count", "failure_count", "public_hypothesis_count", "generator_imported")},
            indent=2,
        )
    )
    return 0 if out["pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
