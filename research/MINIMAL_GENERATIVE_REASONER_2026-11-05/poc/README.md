# Minimal Generative Reasoner — Executed PoCs 1–5

Date: 2026-11-05. All results are **scoped**. The experiment design is about discovering future-preserving representations and showing where ECv4.4's current framing controller cannot discover them; it **does not** establish a general reasoning mechanism or LLM-grade capabilities.

## Decision table

| PoC | Experiment | Actual outcome | Cleared | Next blocker |
|---|---|---|---|---|
| P1 | Exact finite-state future-preserving quotient, 4–12 source bits | Under restricted actions 4,096 states collapse to 4; with hidden-state probe 4,096 | Exact state equality and negative control in a small system | Exponential enumeration |
| P2 | Counterfactual bit perturbations, up to 32 bits | Necessary bits located with linear-count trajectory queries | No exhaustive states needed for support *diagnosis* | Not a proof of sufficient abstraction, horizon limitations |
| P3 | Symbolic circuit dependency closure, up to 128 bits | Necessary sufficient-coordinate set 2 vs 128 depending on actions; 4,8,12-bit checks exhaustive | Non-enumerative future-preservation certificate for a known bit circuit | Original bits may not be the right coordinate system; not necessarily minimal |
| P4 | **GF(2) observability-based automatic coordinate change** | Source observation depends on **all 128 bits**, yet future-predictive minimal dimension is **2** with restricted actions; 128 when probe allowed | Proof of mathematically **minimal** quotient in a known linear system, independent brute-force check at 6/8 bits | Nonlinear, unknown / learned transition representations; discovery cost |
| P5 | **Actual ECv4.4 framing-search and residual-detector modules**, SHA-pinned | 5/5 expected fault/sanity cases; 128-variable framing CLOSE despite valid 2-variable quotient; supplied REABSTRACT preserved as no gain | Specific **implementation gap** identified in existing EC research | A proof-bearing \`phi/delta\` proposal protocol / mathematical checker |

## Reproduction and evidence

- [P1 source](poc1.py), [P1 observed result](POC1_OBSERVED_RESULTS.json)
- [P2 source](poc2.py), [P2 observed result](POC2_OBSERVED_RESULTS.json)
- [P3 source](poc3.py), [P3 observed result](POC3_OBSERVED_RESULTS.json)
- [P4 standalone source](poc4_repro.py), [P4 observed result](POC4_OBSERVED_RESULTS.json)
- [P5 native EC source harness](poc5_ecv44_native.py), [P5 observed result](POC5_OBSERVED_RESULTS.json)
- P5 source is **not reimplemented**: checkout [GPT-EC-Closure-Engine @ d5ec423](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/tree/d5ec423968f1c9242c590e5e77ccfd92d1f59eb2), pass its \`01_repo/src\` directory in environment variable \`ECV44_SRC\`. The script rejects blob-SHA mismatches before executing. No user device or GitHub Actions needed.

## P4 -> P5 actual overlap

P4 produces a real mathematical certificate for the existence of a two-coordinate sufficient representation in a synthetic 128-bit state process. The original observation row is a dense parity over **all** 128 source coordinates, so naïve source-feature selection cannot find the two latent variables. The rank of the GF(2) observability closure identifies the correct number of predictive coordinates and yields a symbolic quotient transition.

P5 executes the existing ECv4.4 modules at their pinned source blobs:
- **128 variables with evidence and complete goal coverage**: \`detect_residuals => CLEAN\`; \`search_framing => CLOSE\`; no reabstraction candidate is generated.
- **Externally provided two-coordinate projection**: original framing score 0.750, alternative framing 0.846 (+0.096 score); **the EC code did not discover this alternative**.
- **\`required_abstraction\` added to one variable**: \`REABSTRACT\` candidate is generated but scored with no gain, so \`PRESERVE\`.
- **False coordinate expression control**: native score still \`PASS\` at 0.846; mathematical witness x=2 proves the proposed first coordinate is wrong. This does not violate EC's *existing semantic metadata contract*, but proves that a new mathematical verification boundary is required.
- **Explicit protected invariant violation**: rejected by existing native code, as expected.

## RCA and one next action

**B0**: Existing ECv4.4 stores semantic framing metadata and evaluates coverage/evidence/resolution. It does not propose or certify new state-space coordinates, transition equivalence, or generative laws.

**Next MVP, not yet implemented**: supply a separate \`ABSTRACTION_CANDIDATE_V1\` record with a symbolic coordinate map \`phi\`, abstract transition \`delta\`, explicit domain/actions/outputs, and an independent checker proof or counterexample. Adapt \`REABSTRACT\` to accept a **verified candidate** without changing current ECv4.4 intent/closure rules. Do not promote a simple label change or an unverified projection.

### Minimal acceptance criteria

1. Input: existing deterministic transition+observation, never a large LLM or a teacher target.
2. Output: \`phi\`, \`delta\`, exact action contract, claimed quotient rank; reference independent of original source module.
3. Validity: strict future/output preservation or explicit counterexample, including faulty projection mutation.
4. Usefulness: measurable reduction of *complete* representation+transition+verification cost, not just state count.
5. ECv4.4 binding: no false \`CLOSE\` based solely on metadata when an externally **verified** strictly better representation is available; no bypass of protected invariants; preserve original acceptance gates.
6. Quality claim: reports stay \`SCOPED_POC\` until genuine tasks and native SUITE tests run.

This is a documented execution outcome, **not** an ECv4.4 code change and not a claim that general intelligence was reproduced.


## P6 — Verified mathematical projection proposal + independent checker + ECv4.4 scoring

[Proposal/adapter source](poc6_adapter.py) / [separate exact verifier](poc6_checker.py) / [observed results](POC6_OBSERVED_RESULTS.json)

A typed \`ABSTRACTION_CANDIDATE_V1\` carries original model SHA, allowed actions, source width, linear coordinate map \`phi\`, abstract transition \`delta\`, and readout. The independent checker verifies exact all-state identities and independently rederives minimal dimension; no \`2^128\` state enumeration.

Six scoped experiments passed:
- Under restricted actions: 6→2 (score gain 0.008, native score gate **PRESERVE**); 8→2 (0.012, adapter **REVISE_VERIFIED_ABSTRACTION**); 128→2 (0.096, adapter **REVISE_VERIFIED_ABSTRACTION**).
- With an extra hidden-state probe: 6→6, 8→8, 128→128, correctly **PRESERVE**.
- Four mutations per restricted case (wrong coordinate, wrong transition, forged source digest, scope expansion) were rejected by the independent checker and fail-closed adapter (12/12).
- The adapter calls the SHA-pinned real ECv4.4 \`score_framing\` function; **the existing EC code was not modified**. The adapter's new return status is PoC-local, **not** a native ECv4.4 return status.

New finding: n=6→2 is mathematically valid but rejected by native 0.01 score-gain threshold (0.008). This threshold measures original semantic framing improvement, **not predictive rank reduction**. An appropriate future revision should keep the existing EC score/gates intact and define a separate validated scientific utility criterion. No nonlinear capability or general intelligence is proven.

**Current blocker after P6:** test the proposal+checker with a genuine ECv4.4 decision/transition contract rather than the handcrafted GF(2) model; run the actual regression and full intended cost measurement before integrating.

## P7 — Black-box active automata learning, without pretrained source

[PoC7 full results and RCA](POC7_FINDINGS.md) / [machine-readable evidence](POC7_OBSERVED_SUMMARY.json) / [executable L* experiment](poc7_lstar_fallback.py) / [extended query-budget experiments](poc7_extended.py) / [official AALpy driver (NOT_RUN)](poc7_aalpy_native.py).

**SCOPED PASS** for independent Angluin L* algorithm, not actual AALpy software execution (sandbox PyPI acquisition blocked). A synthetic 128-bit nonlinear coordinate-scrambled source yielded a 4-state minimal *reachable* observable machine under a fixed reset. With a hidden-state probing action, 12-bit source yielded 40 states; 128-bit source had 504 minimal reachable states by separate exact reference but was not learned at that size. Random equivalence testing with inadequate budget falsely ended at 7 states (true 40), and the independent checker caught this; 10/10 seeded small learning cases passed exact reachable verification. Next blocker is explicit reset/action/evidence-scope certification before ECv4.4 can treat a learned projection as authoritative.

## PoC8 — 到達可能性の独立証明と適用条件のfail-closed（2026-11-06）
[PoC8の実装・実測・技術依存Mermaid](POC8_FINDINGS_2026-11-06.md) / [実測JSON](POC8_EXECUTION_2026-11-06.json)。合成対象の8bit系・128bit非線形座標変換系で、モデルの未来観測同値性と到達可能状態数の最小性を独立検証。11個の異常／正常系を実行。変更された初期状態・操作・観測・source、間違ったモデルを拒否し、証明予算切れはHOLD。これは**外部アダプターPoC**であり、native ECv4.4への組込み・SUITE試験はまだ行っていない。
