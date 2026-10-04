# S2B2 MVP TCC V3 — implementation-safe successor

Protocol: `S2B2_MVP_TCC_V3`
Owner: #43
Residual: #44

V3 inherits the scientific design, AC dependency DAG, MVP boundaries, B1/B2 fairness rules, model pin, materiality threshold, and result-contamination gates from the frozen V2 authority at:
- human V2 commit `d2b01209d98756d41df26d6cf8945f7b419e9599`
- machine V2 commit `003e8b8fd72c26d150a6c4dd0bb4b43f5e660a45`

V2 B1 execution path terminated before inference because a Python `false`/`False` typo reached remote preflight. No B1 scientific result was produced. Stage-A `STAGE_A_AUDIT_PASS` remains valid and is inherited.

## Authorized V3 delta only

No scientific-method change is authorized.

Allowed implementation repair:
1. replace the invalid Python literal in `tools/preflight_s2b2b1.py`;
2. add a local/static gate that compiles all current S2B2 scripts;
3. import/smoke-test non-model modules;
4. execute B1 scientific preflight locally/remotely before any model/runtime acquisition;
5. fail closed on compile/import/runtime-preflight errors.

Forbidden under V3:
- fixture changes;
- generator changes;
- deterministic B1 core changes;
- scorer/output-contract changes;
- Qwen prompt/model/runtime/temperature changes after paired runner freeze;
- materiality threshold changes;
- B1/B2 research-question changes.

## New AC dependency

`L00_IMPLEMENTATION_STATIC_VALID`
-> all inherited V2 local AC.

`L00_IMPLEMENTATION_STATIC_VALID` requires:
- `py_compile` PASS for every S2B2 script used by the active path;
- import smoke PASS for generator/core/scorer/preflight modules;
- B1 preflight process exits 0 and emits exactly `B1_PREFLIGHT_PASS` before model acquisition;
- no GitHub Actions.

A compile/import/preflight runtime failure is terminal `IMPLEMENTATION_PREFLIGHT_FAILED`; it is not a scientific model result.

## V3 one-shot prefix

`P0A_STATIC_COMPILE`
-> `P0B_IMPORT_SMOKE`
-> `P0C_SCIENTIFIC_PREFLIGHT`
-> inherited V2 `P4_B1_EXECUTE_CACHE`
-> `P5_B1_SCORE_AUDIT`
-> `P6_B1_TERMINAL`
-> B2 path unchanged from V2.

No Qwen model/runtime download may begin before P0A-P0C all PASS.

## Current inherited evidence

Stage A independent audit: `STAGE_A_AUDIT_PASS`.
B1 frozen assets remain:
- deterministic core `3dab663ca2747f102b5c6c3e916119cc0b468708`
- output contract `8ada6bd17b5409e32106afab70692b3cdbf47bef`
- independent scorer `f2ee566eb132362b731d21712d4d601b541e3497`
- generator `04f9b2fff2fde06f2b1be6cfc6030954f59c2f8c`
- manifest `2372e72231d17ff7e9996199635fa26d5ce52194`
- holdout digest `dde736e4f37b55567af45726e378291bfa07d44d39ee58e2038804582426e650`

V3 cannot modify these assets.
