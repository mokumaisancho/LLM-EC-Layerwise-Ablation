# 既存研究による実現可能性判定 — 未知の非線形系からの最小生成原理

Date: 2026-11-05 / ROOT-GEN-001 / relates Issue #71
Status: literature feasibility analysis; **these cited external methods have NOT been run against the project's current PoC fixtures**. Do not call scientific claim closed.

## 結論
- **限定したモデルなら解決可能、広範な未知の非線形推論器の「真の最小原理」の自動同定は未解決。**
- 2019 PNAS Champion et al. directly works on **simultaneous discovery of a low-dimensional coordinate system and sparse nonlinear governing equations**, removing need to invent an algorithm for that limited scope.
- For the previous POC4 / POC6 **discrete deterministic input-output automata**, **AALpy's active automata learning** is a simpler first reuse candidate. It learns small observable finite-state machines from resettable black-box input/output queries without knowing the hidden state coordinates.
- Exact correctness without a known semantics/oracle or a finite state bound remains unavailable; separating a **functional quotient** from the **original latent physical coordinates** is critical.

## Literature and implementation reuse matrix

| ID | Paper / implementation | Already solved (under assumptions) | What it does NOT solve | Match to GEN001 |
|---|---|---|---|---|
| R01 | Champion et al. (PNAS 2019), [Data-driven discovery of coordinates and governing equations](https://pmc.ncbi.nlm.nih.gov/articles/PMC6842598/); [official code](https://github.com/kpchamp/SindyAutoencoders) | NN autoencoder plus sparse dynamics simultaneously estimates latent coordinates and symbolic laws from high-dimensional observations | No exact global minimality proof, needs sufficiently clean trajectories, selected latent dimension, training; may not extrapolate | **Highest topical match** for unknown nonlinear phi and delta |
| R02 | Lusch, Kutz & Brunton (Nature Communications 2018), [Deep learning for universal linear embeddings of nonlinear dynamics](https://doi.org/10.1038/s41467-018-07210-0) | Learns observable Koopman-related coordinate changes to approximately linearize nonlinear dynamics | Latent dimension/cost and global exactness; approximation is not proof | Alternative nonlinear coordinate method |
| R03 | Brunton et al. (PNAS 2016), [SINDy](https://doi.org/10.1073/pnas.1517384113); [PySINDy](https://pysindy.readthedocs.io/en/stable/index.html) | Discovers parsimonious governing equations when suitable coordinates, basis, observations are available | Cannot guarantee discovery of correct coordinates or hidden states by itself | Reuse equation discovery once phi exists |
| R04 | Muškardin et al. (2022), [AALpy](https://link.springer.com/article/10.1007/s11334-022-00449-3); [official Python repository](https://github.com/DES-Lab/AALpy) | Active L*/KV/etc learn black-box finite-state input-output behavior and offer equivalence-testing strategies | Requires reset/query interface, finite observable machine, and true equivalence oracle/state bound or probabilistic tests for confidence; does not reconstruct unique physical phi | **Fastest POC for finite-state behavioral quotient** |
| R05 | Hızlı et al. (ICLR 2025), [Identifying latent state transitions in non-linear dynamical systems](https://proceedings.iclr.cc/paper_files/paper/2025/hash/b192f601432dff4e6777d2d06d52cfa5-Abstract-Conference.html) | Conditional identifiability of nonlinear latent transitions from high-dimensional observations, assuming sufficient latent noise variability and bijective augmented transition | Does not guarantee arbitrary deterministic black-box systems can be identified | Defines when nonlinear discovery may be theoretically possible |
| R06 | Locatello et al. (ICML 2019), [Challenging Common Assumptions...](https://proceedings.mlr.press/v97/locatello19a.html) | Impossibility result for recovering uniquely disentangled representations from unsupervised data without inductive biases | Does not rule out useful task-preserving quotients, or controlled interventions | **Stop condition against unrestricted discovery claims** |
| R07 | Alur et al. (FMCAD 2013), [Syntax-Guided Synthesis](https://doi.org/10.1109/FMCAD.2013.6679385); Abate et al. (CAV 2018), [CEGIS(T)](https://link.springer.com/chapter/10.1007/978-3-319-96145-3_15) | Searches restricted expressions and rejects failing proposals via counterexample and solver | Arbitrary unbounded program space not generally tractable; exact proof needs formal semantics | Reuse certificate/counterexample logic; do not write own prover |
| R08 | AI Feynman, Udrescu & Tegmark (Science Advances 2020), [paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7159912/) | Physics-informed symbolic regression exploiting symmetry/separability/compositionality | Not a general hidden-state dynamical reconstruction solver | Optional targeted equation discovery |

## Single key distinction

(A) **Useful observable behaviorally equivalent state**: find a small input-output automaton or quotient. May be learnable without recovering original internal state. This is sufficient for a bounded EC runtime that only requires exact observable futures.

(B) **True latent physical coordinate/law**: recover the exact generating variables/transition law; often not identifiable without additional restrictions, interventions, or measurement assumptions. This is a stronger scientific claim and is NOT required for the immediate PoC.

(A) and (B) must not be conflated.

## Narrow decision-first reuse path

**First and smallest**: take the existing GEN001 POC4 state-transition process as a black-box SUL:
- Give learning code only reset+action+observed-output. Hide its GF(2) matrices, parity coordinates, quotient rank and generator source.
- Run AALpy L*/Mealy or Moore variant (match observed behavior); get inferred state count and query count.
- Use existing POC4 exact known semantics **only in the independent evaluation side** to verify candidate behavior on all admissible actions or generate a counterexample.
- Both restricted and probe-allowed action contracts must be tested. A minimal model of four observable states for restricted scope is the predicted result, **not yet observed with AALpy**. With the probe input permitted, observed-equivalence may require exponentially many states; impose a budget and fail/stop rather than claim complete discovery.
- Use a deliberately **nonlinear discrete fixture**, e.g. nonlinear Boolean gates, as the next holdout. This is simpler than inventing a general symbolic NN-based phi search.

**If/only if** this black-box observable-state task fails or needs continuous rich state:
- Reuse Champion et al.'s **SINDy autoencoder** (or an up-to-date reimplementation compatible with the local environment), compare to PySINDy without learned coordinates on the same system.
- Small synthetic hidden-system holdout: known 2–4D nonlinear latent dynamics, measured through higher-dimensional nonlinear sensor, multiple initial conditions/actions; no large pretrained LLM.
- Freeze train/holdout environments and evaluate multi-step prediction, discovered latent dimension, symbol count, full model+feature extraction+training cost.
- Any exact output/transition preservation claim requires an independent formal checker for an explicit bounded symbolic candidate; samples alone cannot establish global equality.

## AC and scientific limits
1. **AC-F1** Under an explicit reset/action/observation contract, an existing algorithm discovers a reduced predictive *behavioral* state without seeing the target internals.
2. **AC-F2** A withheld independent oracle checks the discovered model; a counterexample must trigger revision.
3. **AC-F3** The learned model's observable state count is no larger than the exact bound on the finite control, or report "UNKNOWN / budget exceeded" rather than PASS.
4. **AC-F4** The alternate nonlinear source and changed action alphabet are holdouts, not retuned on.
5. **AC-F5** Query cost, all candidate state/data costs, computation time and fail reasons are recorded. Huge model not part of bootstrap.
6. **AC-F6** ECv4.4 only consumes verified candidates and keeps native intent/closure protections. Phase1/SUITE remain independent.

**Expected practical answer**: functional equivalence on a finite accessible system is tractable with existing tools. Arbitrary nonlinear hidden-law discovery, unique original causes, and general LLM-equivalent generative intelligence remain open.

## Decision gate

The single decision now is: **Can an existing active finite-state learner recover the 4-state restricted predictive quotient from POC4 using input-output queries alone?**

If yes, use the learned quotient with independent checking as the next ECv4.4 candidate; if no, inspect reset/query or state-bound failure, not invent a new learning algorithm. This reduces risk/cost and avoids solving the hardest nonlinear discovery problem prematurely.
