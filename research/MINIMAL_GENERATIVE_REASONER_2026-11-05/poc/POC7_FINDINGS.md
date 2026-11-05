# PoC 7 — ブラックボックスからの最小到達可能状態の学習、誤PASS検出

2026-11-05 / ROOT-GEN-001 / [Issue #71](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/71)

**実行結果: scoped PASS（独立実装L*）。AALpy本体は NOT_RUN。**

## 1. 課題と実行方式

従来のPoC4では、与えられたGF(2)遷移行列から2次元の座標を導出した。PoC7では元の遷移式・座標・正解状態数を**学習器から隠し**、reset・action・観測出力の問い合わせから有限状態機械を学習した。

アルゴリズムは既存のAngluin L*（観測表、membership queries、反例による更新）であり、独自の新アルゴリズムを発明したわけではない。学習時の等価性オラクルは、短い入力列の網羅とランダム入力列による反例探索。これと**独立した検証器**が、正解系との積オートマトンを到達範囲で完全検証し、最小化と一致確認を実施した。

公式AALpy 2.0.0 (2026-10-25) をPyPIから取得しようとしたが、sandbox DNS/ネットワーク制約で失敗。したがって今回は**公式AALpyそのものは実行していない**。実行済みL*の独立実装と、公式AALpy用未実行ドライバは分けて保存した。

## 2. 主要な実測結果

| 対象 | 元の変数 | 指定したreset/action | 学習結果 | 独立正解 | 結果 |
|---|---:|---|---:|---:|---|
| P4 zero | 8 bits | reset=0; actions 0,1 | 1 | 1 | PASS |
| P4 nonzero | 8 bits | reset=1; actions 0,1 | 3 | 3 | PASS |
| P4 reachable | 8 bits | reset=1; actions 0,1,3 | 4 | 4 | PASS |
| Nonlinear scramble | 128 bits | reset=0; actions 0,1 | 4 | 4 | PASS |
| P4 hidden unreadable | 6 bits | reset=1; actions 0,1,2 | 3 | 3 | PASS |
| P4 hidden reachable | 6,8,12 bits | reset=4; actions 0,1,2 | 16,24,40 | 16,24,40 | PASS |

128-bit nonlinear system is a **synthetic invertible nonlinear coordinate mapping** with a small dynamical core. The learner receives input/output queries only. This proves discovery of a small **reachable observational machine**, not original hidden coordinates or an unknown physical law.

Additional independent reference with hidden-access action and reset=4 (no black-box learner at 128 bits):

| Source bits | Minimal reachable observational states |
|---:|---:|
| 6 | 16 |
| 8 | 24 |
| 12 | 40 |
| 16 | 56 |
| 32 | 120 |
| 64 | 248 |
| 128 | 504 |

The 128-bit / 504-state figure comes from the **independent original-system reference**, not an AALpy or L* learning run.

## 3. False-PASS control

A 12-bit system with reset=4 and actions 0,1,2 requires exactly 40 observable states:

| Random input words checked per equality round | Learned states | Independent exact verdict |
|---:|---:|---|
| 0 (short deterministic checks still enabled) | 7 | FAIL, counterexample found |
| 5 | 40 | PASS |
| 50 | 40 | PASS |
| 200 | 40 | PASS |
| 1500 | 40 | PASS |

The 5-query success is specific to this fixture and seed, **not** a general proof that five queries suffice. In an additional deliberately broken test where equivalence checks always reported no counterexample, a two-state wrong hypothesis was declared finished; the independent verifier found the witness sequence [0,0,1].

Ten runs (5 seeds x 2 configurations: nonlinear-128 and hidden-probe-12) all matched independently determined minimal reachable models. This gives reproducibility evidence only for these fixtures.

## 4. Performance and accounting

In a pure-Python microbenchmark for the synthetic nonlinear-128 source, 150,000 transitions across 7 repetitions:
- Full source dynamics: median 0.16666s
- Learned four-state lookup: median 0.00908s
- Observed ratio: about 18.35x on that Python fixture

Learning cost in the measured run: 0.01706s, 1,036 unique membership queries and 12,182 source transitions. A crude amortized crossing point (~16,238 calls) **excludes independent verification and setup costs**. These results do not establish general NN/LLM acceleration, real deployment gain, or true minimal program complexity.

## 5. What this does and does not establish

- **Scoped PASS:** learning a minimal reachable behavioral quotient from a resettable finite input/output interface without pretrained LLM or prior latent state labels.
- **Scoped FAIL / critical risk:** finite random testing can falsely close a non-equivalent model. The separation of evidence and closure in ECv4.4 must account for this.
- **OPEN:** global mathematical projection for all hidden initial states; discovery of unique physical/causal latent coordinates; arbitrary nonlinear laws; general-purpose reasoning from minimal initial principles.
- **NOT_RUN:** actual AALpy 2.0.0 native learning; ECv4.4 native control-plane integration and its full regression.

## 6. One actual blocker for ECv4.4

A candidate behavioral abstraction must include: (1) reset and action contract, (2) outputs and coverage, (3) model and learning/query cost, (4) independently checked evidence grade EXACT_REACHABLE / EMPIRICAL_ONLY / BUDGET_UNKNOWN / COUNTEREXAMPLE, and (5) explicit non-generalization beyond observed scope.

Do not treat an AALpy/L* learner's own absence of counterexamples as an ECv4.4 evidence-authoritative PASS. The correct interface is a scoped certificate-bearing proposal, with an external checker; EC control remains in authority.

## 7. Sources and reproducibility
- [Executed L* baseline source](poc7_lstar_fallback.py)
- [Executed budget, seed and microbenchmark suite](poc7_extended.py) — invokes baseline automatically if no prior result file exists
- [Official AALpy driver, NOT_RUN here](poc7_aalpy_native.py)
- [Machine-readable observed summary](POC7_OBSERVED_SUMMARY.json)
- [Prior-art feasibility and official implementations](../PRIOR_ART_FEASIBILITY_2026-11-05.md)
- [AALpy official repository](https://github.com/DES-Lab/AALpy)
- [Muškardin et al. (2022) AALpy paper](https://doi.org/10.1007/s11334-022-00449-3)
- [Angluin (1987) Learning Regular Sets](https://doi.org/10.1016/0890-5401(87)90052-6)

Absolute source semantics and all reachable states are available to the **independent checker**, not to the learner. Thus the exact PASS is a bounded formal result for these artificial systems, not an assertion of black-box all-state proof for arbitrary unknown systems.
