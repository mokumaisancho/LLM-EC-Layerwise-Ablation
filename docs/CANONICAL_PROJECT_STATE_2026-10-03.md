# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC without material loss.

Authoritative coarse layers:
- S1: Language -> Domain Semantics
- S2: Domain Semantics -> Candidate Set
- S3: Candidate Set + Semantic State -> Selection / Reframing
- S4: Selected State -> Execution / Closure

Large LLMs are optional reference points, not Phase1 critical-path dependencies.

## Canonical MVP contract
Phase1 MVP protocol: `PHASE1_MVP_TCC_V1`.

Normative files:
- `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.md`
- `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`
- `ACCEPTANCE_CRITERIA.md`

MVP means minimum scientifically reportable coarse localization, not fine decomposition.

MVP layer scope:
- S1: LLM + Oracle intervention.
- S2: LLM + Oracle intervention.
- S3: LLM vs actual ECv4.4 + Oracle intervention.
- S4: LLM vs actual ECv4.4 + Oracle intervention.

New deterministic EC S1/S2 implementations are post-MVP only if coarse localization later makes them relevant.

Frozen operational materiality: absolute 0.20. One-fixture 0.10 movement is non-material. Material-layer gains within 0.10 terminate as `MVP_AMBIGUOUS_DOMINANT_LAYER`; no manual tie break.

## Current measurement status
- Phase1 v2 fixture generation: PASS.
- Oracle-label leakage: PASS, 0 findings.
- Oracle replay/hash-chain validation: PASS, 10/10.
- Canonical generated-dataset digest: `8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6`.
- Historical deterministic S3/S4 fallback prebaseline: 1.00 across selection/reframe/closure/final success, NONREPORTABLE.

## Completed dependency remediation
- Issue #21 threshold/capacity decision contract: CLOSED/COMPLETE.
- Issue #12 output-contract vs semantic scoring separation: CLOSED/COMPLETE.
- `tools/run_llm_s3_s4_cache.py` now has raw + schema-constrained arms, cache reuse, output-contract recording, and provenance.
- `tools/compare_s3_s4.py` rejects non-reportable LLM/EC results and upstream hash mismatches.
- `tools/run_ec_s3_s4.py` no longer silently falls back for reportable results. It requires actual ECv4.4 provenance.
- ECv4.4 pinned for this MVP contract:
  - repo `mokumaisancho/GPT-EC-Closure-Engine`
  - commit `d5ec423968f1c9242c590e5e77ccfd92d1f59eb2`
  - protocol `EC_V4_4_RESIDUAL_DETECTOR_V1`

Actual reportable ECv4.4 execution against the pinned repository is still pending, so Issue #20 remains open.

## Active critical path
1. Execute actual pinned ECv4.4 S3/S4 and close Issue #20 only after reportable results pass.
2. Implement Issue #22: LLM S1/S2, A/B arms, one-layer-at-a-time Oracle substitution, and per-layer gain scoring.
3. Satisfy logical dependency `0P5B_MODEL_READY` through any verified non-Drive route.
4. Run Issue #14 frozen ~0.5B capacity point.
5. Run A/B/C/D/E with frozen upstream hashes.
6. Calculate per-layer Oracle substitution gain.
7. Apply frozen 0.20 materiality/tie rules.
8. Exit at one predefined MVP terminal state.
9. Only after MVP: split the selected layer if required.

## 0.5B asset dependency
`0P5B_MODEL_READY` is an OR dependency. Issues #16/#17/#18/#19 are alternative ingress implementations, not a sequential mandatory chain.

Allowed route classes:
- already verified sandbox artifact;
- connector-native non-Drive materialization;
- directly attachable Generic Binary Ingress;
- GitHub text-shard fallback for the 0.5B artifact;
- another size/SHA-verified non-Drive route.

Google Drive model relay is prohibited by the MVP TCC.

## Qwen3-4B ingress status
`Qwen3-4B-Q4_K_M.gguf` has NOT been materialized into the current GPT sandbox.
Expected size: 2,497,280,256 bytes.
Expected SHA-256: `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.

Qwen3-4B is outside the Phase1 MVP critical path and remains optional final-reference work.

## Fail-closed rules
- No fallback may be labeled/reportable as ECv4.
- No semantic LLM metric from invalid/raw output-contract results.
- No causal claim without identical upstream hashes.
- No v1/v2 pooling.
- No hidden taxonomy/oracle labels in model-visible inputs.
- No prompt/fixture/threshold tuning after freeze.
- ~1.5B is allowed exactly once only when the frozen capacity-collapse rule fires.
- No automatic 4B escalation.
- GitHub Actions remain disabled.
- New blocking residuals require issue registration and a new versioned TCC contract; no mid-run branch invention.
