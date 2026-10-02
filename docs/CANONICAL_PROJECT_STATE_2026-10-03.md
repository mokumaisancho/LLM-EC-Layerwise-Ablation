# Canonical Project State — 2026-10-03

## Root research goal
Localize which externally measurable LLM reasoning/control functions can be replaced or supplemented by deterministic EC without material loss.

The authoritative layer decomposition is:
- S1: Language -> Domain Semantics
- S2: Domain Semantics -> Candidate Set
- S3: Candidate Set + Semantic State -> Selection / Reframing
- S4: Selected State -> Execution / Closure

Large LLMs are optional reference points, not the initial-study critical path.

## Current measurement status
Phase1 v2 fixture generation: PASS.
Oracle-label leakage gate on model-visible task inputs: PASS, 0 findings.
Oracle replay / hash-chain validation: PASS, 10/10 fixtures.
Canonical generated-dataset digest: `8bfce027bdc82a34b78e9b1a87f7812d907db34c164f50a9a996bd41b3b824d6`.

The repository S3/S4 deterministic implementation was executed in sandbox without an EC_V4_4_PYTHONPATH binding. It therefore ran `FALLBACK_NO_EC_PATH` and scored 1.00 on selection, reframe, closure, and joint final-task success across 10 fixtures. This is a harness prebaseline only. It MUST NOT be reported as an actual ECv4 result.

## Qwen3-4B ingress status
`Qwen3-4B-Q4_K_M.gguf` has NOT been materialized into the current GPT sandbox.
Expected size: 2,497,280,256 bytes.
Expected SHA-256: `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5`.

Verified facts:
- The artifact identity and whole-file SHA are known.
- Render-side full artifact acquisition and SHA verification have succeeded previously.
- The current GPT sandbox shell cannot resolve/reach external Render/Hugging Face endpoints directly.
- Therefore the current blocker is the ChatGPT product boundary from a remote binary/file reference into sandbox materialization, not model integrity or Render capacity.
- Google Drive must not be used for the large-model path.

Qwen3-4B is now explicitly removed from the Phase1 critical path and retained only as an optional final reference comparison.

## Active critical path
1. Bind the actual ECv4 implementation for reported EC measurements; fallback is fail-closed for reported results.
2. Complete deterministic EC coverage for S1/S2 or formally constrain the first reported experiment to Oracle-fixed upstream + S3/S4.
3. Run a lightweight ~0.5B instruction model on the exact same frozen Phase1 v2 upstream hashes.
4. Execute A/B/C/D/E comparisons.
5. Calculate Oracle substitution gain per layer.
6. Select the single highest-materiality layer.
7. Split only that layer and retest.
8. Escalate model capacity to ~1.5B only if the ~0.5B result remains capacity-ambiguous.
9. Use Qwen3-4B only for optional final reference validation.

## Fail-closed rules
- A fallback EC implementation cannot be labeled ECv4.
- No reported LLM-vs-EC causal claim without identical upstream hashes.
- No v1/v2 result pooling.
- No hidden taxonomy/oracle labels in model-visible inputs.
- No holdout/prompt/threshold tuning after freeze.
- GitHub Actions remain disabled.
- Google Drive large-model persistence/relay is prohibited.
