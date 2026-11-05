# Minimal Generative Reasoner / 推論可能態と最小生成原理 — 研究記録

記録日: 2026-11-05 (JST) / 文書バージョン: 1.0
ステータス: **研究上の原課題・仮説と先行研究の接続記録。新規PoC・NN実験・AC完了を意味しない。**

## 単一の原課題（ROOT-GEN-001）

**既存の大規模LLM・その圧縮・蒸留を出発点にせず、最小限の初期構造・生成規則・表現変換・経路選択機構から、限られた計算資源でどれほど高度かつ多様な推論能力を実現できるか。その成立条件と下限を明らかにする。**

発想の中心は「既に大量の知識があるから推論できる」ではなく、「推論を生み出す小さな能力・構造が先にあり、そこから知識、規則、解法と多様な機能が展開する」という可能性（哲学的には可能態／流出論の比喩）。

### 原課題に含む区別
- **可能態（潜在能力）と現実態（課題で顕在化した性能）**は区別する。タスク未実行で潜在能力全体を厳密特定できるとは主張しない。
- **計算可能性（チューリング完全性）と実用的な推論性能**は別。時間・メモリ・検証資源を含める。
- **知識量、生成規則、表現変換、探索バイアス、物理的環境**のコストを別勘定で隠さず、初期構造全体として評価する。
- **圧縮は設計の出発点ではなく、発見した構造を評価した結果**。大型LLMは比較用であり、教師、Gold、初期生成器、蒸留元の必須条件ではない。
- 「意味がある（makes sense）」は単なる整然さではない。正しさ・予測可能性・目的達成への因果的寄与を区別する。
- 生物の最短経路や形態形成からの推論器設計は**類推的仮説**であり、一般推論成立の実証ではない。

## 文書索引
1. [課題・議論の推移と原課題への収束 — Mermaid](ISSUE_FLOW.md)
2. [数学・物理・情報・実装の技術依存関係 — Mermaid](TECHNICAL_DEPENDENCIES.md)
3. [先行論文・書籍・検証範囲・論点IDの対応](PAPERS_AND_CLAIMS.md)
4. [ECv4 → ECv4.4 および既存研究との接続・非同一性](ECV4_4_4_TRACE.md)

## 既存研究との接続
- [本研究の収蔵先: LLM-EC-Layerwise-Ablation](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation) — S1意味抽出、S2候補生成、S3選択/再構成、S4実行/終了判断を同一上流成果物で比較する既存研究。S3/S4のECv4.4 native adapterは既存AC契約に従う。
- [EC正本: GPT-EC-Closure-Engine](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/tree/GPT-EC-V4) — GOAL/ISSUE/AC/WORK/EVIDENCE/GATE/CLOSURE の決定論的統制。科学的推論器が既に完成したわけではない。
- [関連原課題: neural-algorithmic-reducibility](https://github.com/mokumaisancho/neural-algorithmic-reducibility) — NN→決定論的規則の既存研究。特に [物理と認識論](https://github.com/mokumaisancho/neural-algorithmic-reducibility/blob/main/PHYSICS_AND_EPISTEMOLOGY.md) は投影が未来を保存する必要条件を既に記録。
- ECv4／ECv4.4は本研究の**先行実装・研究管理の接続点**。推論能力の発生原理そのものを証明する既存成果とは扱わない。

## 調査済みと未解明の境界
- 既知: 極小の計算機構による普遍計算、因果状態による予測に十分な状態集約、特定の情報ボトルネック相転移、特定の粘菌モデルの最短経路収束、反復型小型NNの課題特化的な成功。
- 未解明: 一般的な「推論能力」全体をタスク非依存に測る尺度、最小生成原理の特定、投影の臨界点で有用推論が飛躍的に増える普遍的条件、事前学習された巨大知識なしで汎用LLM級の能力が成立するか。
- 科学上の区分: **定理 / 条件付き実証 / 仮説 / 未研究または未確認**を [PAPERS_AND_CLAIMS.md](PAPERS_AND_CLAIMS.md) に区別。

## 最短の次の決定点（設計のみ・未実行）
「ある表現変換 phi と最小動的規則 delta が、求める出力と将来の遷移を保ちながら、総記述長と総実行コストの両方を減らすか」を、既存の厳密に定義された有限の状態遷移系で確認する。成立しなければ、推論器を実装する前に仮説を修正。成立しても一般的な知能やLLM代替性までは主張しない。

この記録は新たな独立研究テーマの追跡資料であり、既存S1〜S4のacceptance criteria・判定・状態の変更を伴わない。

## 2026-11-05: 実行済みPoC（MGR-P1/P2/P3）

- [実験報告・7条件の実測・偽PASS制御・次の単一ブロッカー](poc_finite_quotient_v1/REPORT.md)
- [P1: 最小の未来保存状態の抽出と線形投影の反例](poc_finite_quotient_v1/run_poc.py)、[P1実行結果](poc_finite_quotient_v1/results.json)
- [P2: 観測深度が不足すると起きる誤同値と反例](poc_finite_quotient_v1/poc_horizon.py)、[P2実行結果](poc_finite_quotient_v1/horizon_results.json)
- スコープ: **合成8bit状態256個、各2入力、7条件、未来保存の全状態検証**。大規模LLM・蒸留・NN重みは使用していない。
- 限定結果: `k=0`では256→4個の未来同値状態、`k=1`では4→6個かつ線形XORによる正確な最小射影は不可能。最長6ステップの隠れ依存がある場合、1ステップだけの観測は192個の必要状態を6個と誤判定する。
- [P3: 2bit XOR射影を少数の観測から発見](poc_finite_quotient_v1/poc_sparse_discovery.py)、[全120試行・独立判定](poc_finite_quotient_v1/sparse_discovery_results.json)。k=0の12状態観測で10/10正解（限定条件）、k=1では標本上の誤PASSも発見。
- **次の単一ブロッカー**: 事前に線形XORという表現クラスを指定せず、**非線形な未来保存射影と有効な動的規則を未知の系から発見・反証できるか**。実測のLLM代替性や実行速度向上は未確認。


## 2026-11-05: PoC1–PoC6 executed
[PoC execution ledger, evidence and reproductions](poc/README.md) / [PoC6 independent checker](poc/poc6_checker.py) / [PoC6 adapter](poc/poc6_adapter.py) / [PoC6 results](poc/POC6_OBSERVED_RESULTS.json).

**Evidence-based narrowing**: a linear 128-dimensional source can have a mathematically minimal 2-dimensional future-predictive quotient under a restricted action contract; the existing ECv4.4 framing controller does not discover this purely from its semantic residual metadata. A separate certificate-bearing proposal/verification adapter was tested against the pinned *actual* ECv4.4 scoring functions. Nonlinear/general reasoning and full EC integration remain OPEN. [Single blocker Issue #71](https://github.com/mokumaisancho/LLM-EC-Layerwise-Ablation/issues/71).

## 2026-11-05: Existing research feasibility — avoid solving nonlinear discovery from scratch
[Original papers, official implementations, applicability matrix and exact limits](PRIOR_ART_FEASIBILITY_2026-11-05.md). Highest direct match: Champion et al. 2019 SINDy-autoencoder (simultaneously discovers nonlinear coordinates and sparse dynamics). Lowest-cost first probe: AALpy active automata learning for **reachable** black-box input/output states with explicit reset/action assumptions. Global 4-state POC4 quotient is not necessarily learnable from a single reset. General latent identifiability requires assumptions (Locatello 2019; Hızlı et al. 2025). None of these methods has been newly run here.

## 2026-11-05 — P7 active learning result and remaining blocker
[Executed PoC7 and independent exact reachable verifier](poc/POC7_FINDINGS.md). The learner did not need native transition matrices, pretrained LLMs, or latent-coordinate labels to recover a minimal **reachable** finite input-output machine on scoped synthetic systems. It did not infer a globally valid latent coordinate/law. False-PASS controls confirmed that terminating an active learner is not a proof; the existing ECv4.4 authority gate requires a separately checked scope-specific certificate. Official AALpy library acquisition failed in sandbox; a tested L* standalone implementation and a distinct unexecuted native driver are provided.
