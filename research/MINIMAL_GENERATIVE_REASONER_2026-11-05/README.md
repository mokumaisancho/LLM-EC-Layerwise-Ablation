# Minimal Generative Reasoner / 推論可能態と最小生成原理 — 研究記録

> **最新の実行・依存関係（2026-11-07）**: [現行MermaidとIssue#71 C6の分岐](TECHNICAL_DEPENDENCIES.md#current_execution_graph_2026_11_07) / [単一の判断台帳](ACTIVE_DECISION.json)。以下の古い「次の決定点」と当時のPoC提案は研究履歴であり、最新P0の実行指示ではない。2026-11-07の監査で、**直近k0-L*は予測用4状態モデルの発見であり任意raw→学習IDの`phi`を生成していない**ため、Issue#71 C6（`phi,delta,checker,discovery`の総費用）に対しては既知GF(2) P4のソース利用経路を優先すると決めた。P4の**1操作の元系対`phi+delta`の同一契約・最適化済み基準**を定義する前に全費用実験を開始しない。L*での問い合わせ回数削減は別の限定的な効用評価。

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

## 2026-11-06 — PoC8: scope-bound exact evidence gate
[PoC8検証結果とMermaid](poc/POC8_FINDINGS_2026-11-06.md) / [実行コード](poc/poc8_scope_gate.mjs) / [実測JSON](poc/POC8_EXECUTION_2026-11-06.json)。11試験すべて想定どおり。学習モデルを元システムと独立照合し、reset・action・output・sourceの違い、誤モデル、予算不足をfail-closedに分類。128bit非線形合成系の4状態モデルも限定的に検証。**ECv4.4 native統合・権限昇格は未実施**。次の単一ブロッカーは実装source SHAと操作契約に結び付いたnative S3/S4 adapterおよび既存回帰試験。

## 2026-11-06 — PoC9: ECv4.4 native preflight integration (Draft PR)
[実行証拠・費用・残余課題JSON](poc/POC9_NATIVE_ECV44_INTEGRATION_2026-11-06.json)。[EC実装側 Draft PR #40](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/pull/40)、[統合設計・Mermaid](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/blob/research/gen001-verified-abstraction-20261106/research/GEN001_ECV44_BEHAVIORAL_ADMISSION_2026-11-06.md)。独立検証17・EC制御クラス15・portable pytest16=48/48限定試験PASS。外部の信頼できる有限状態ソース・reset/action/output境界を証明してECv4.4 V2 preflightに渡し、不一致や予算不足はBLOCKED。既存nativeフレーミングが先行し、候補は自動適用せずreviewのみ。旧EC全SUITE／S3/S4〜V3 end-to-endはNOT_RUN。人工8→4状態のPythonマイクロベンチでは約0.961倍で**速度改善なし**。このため統合はDraft PRで未マージ。次は実ランタイムのsource意味づけの真正性＋unmocked SUITE＋総コスト評価。

## 2026-11-06 — PoC10 / PoC11: live有限関数照合とS3/S4識別可能性の検証
[PoC10：関数実行とソース表一致の独立照合](poc/POC10_RUNTIME_ATTESTATION_2026-11-06.json) / [PoC11：S4公開情報の同値衝突](poc/POC11_S4_SIGNATURE_COLLISION_2026-11-06.json) / [EC研究ブランチの技術Mermaid](https://github.com/mokumaisancho/GPT-EC-Closure-Engine/blob/research/gen001-verified-abstraction-20261106/research/GEN001_POC10_RUNTIME_S3_S4_BOUNDARY_2026-11-06.md)。PoC10の純粋な有限関数照合11/11 PASS、300回の反復一致。既存ECv4.4 native全SUITEは変更後未実施。PoC11は既存Phase1の縮約されたS4署名において同じ入力でCLOSE/CONTINUEが混在し、10件中少なくとも2件が不識別で上限8/10となることを再計算（フル公開情報の不可能性ではない）。**ECは原理発見器でなく検証と研究進行の管理器**。S3/S4全体のEC置換は既存契約不一致が解消するまで未成立。Draft PR #40は未マージ。

## 2026-11-06 — GEN001 S4 64新規合成holdout（原課題の完了判定と分離）
[事前登録と再現可能な実行コード・結果](holdout_s4_2026-11-06/REPORT.md) / [64件の行別結果](holdout_s4_2026-11-06/HOLDOUT_EXECUTION_SUMMARY.json)。
旧S4判定関数の本文をGitHub上の凍結版と文字単位で照合し、予測器に与える公開7項目だけで新規64件を評価。契約内32/32正解、契約外32件では16誤CLOSE（全64件48正解）。16組の入力同値・正解不一致を確認。**2変数の追加は有効だが未確認の証拠・義務の網羅性・実行効果まで保証しない**。この64件は新規合成で外部独立専門家Goldではない。ECv4.4のREABSTRACTは依然、未知の非線形座標変換を自主発見できず、外部PoC由来候補の審査が中心。原理発見を完了とせず、閉鎖証明の入力不足と独立検証を分離して追跡。

## 2026-11-06 — PoC13: 限定解決の許容条件と決定的ブロッカー
[PoC13実行・RCA・Mermaid](poc13_authority_gate_2026-11-06/REPORT.md) / [再現スクリプト](poc13_authority_gate_2026-11-06/poc13_repro.py) / [64ケース・11異常系](poc13_authority_gate_2026-11-06/POC13_OBSERVED.json)。合成64件で誤CLOSEを16→0、正常CLOSE24を維持。独立ホスト側の固定ハッシュがない／偽造の権威一式ならBLOCKED。ただしホスト権威の実在証明は今回の模擬環境にない。**決定的なブロッカーは外部規範に基づいた義務目録全量と独立証拠の真正性**。非線形座標を万能に自動発見できない点は有限系MVPの現ブロッカーではなく、反例が出た条件でのみ既存L*/CEGIS/SINDy等にエスカレーションする。既存ECv4.4 Draft PR#40の全SUITEはNOT_RUN。

## 2026-11-07 — 現在の本線：PoC7の入力・投影境界を監査
[4状態モデルの入力契約と投影限界、反例の記録](POC7_INPUT_PROJECTION_BOUNDARY_AUDIT_2026-11-07.md)。固定reset・操作0/1で元状態4→学習状態4であり、到達可能状態数の縮約は実証していない。一方、参照合成系には任意のraw状態からの真の2bit投影関数が存在するが、L*学習器はその写像を生成していない。従来の18倍マイクロベンチは任意raw状態の投影費用と公平な直接実装対照を含まず、「投影による総計算削減」PASSではない。入力形態（操作履歴か任意raw状態か）を先に固定し、最小の未検証接続点のみ調べる。汎用次工程スキルの正本は [Skills/evidence-to-next-action](https://github.com/mokumaisancho/Skills/blob/main/skills/evidence-to-next-action/SKILL.md)。

## 2026-11-07 — PoC15: 学習4状態モデルと直接2bit規則を同じ入力契約で比較
[検証結果と次の単一判断](poc/POC15_DIRECT_BASELINE_FINDINGS_2026-11-07.md) / [実測JSON](poc/POC15_DIRECT_COMPARISON_OBSERVED_2026-11-07.json) / [独立JS再検証](poc/poc15_direct_rule_reachable_verifier.mjs)。固定reset・操作0/1で元raw到達4→学習4、4×2遷移一致。L*再学習後の4状態表は元ソースの直接2bit規則と同値。100,000操作では元の非線形Pythonラッパーより約20倍速いが、元raw4状態を事前に表化した公正対照とほぼ同速（15反復で5.66ms対5.73ms）。**「128bit→4状態で計算削減」とする主張はこの入力範囲では支持されない**。学習器は任意raw→ID写像`phi`を生成していない。次の最小判断は元rawで複数の異なるhidden状態が到達するreset条件を1つ追加して初めて、真の状態集約が発生するか確認すること。ECv4.4接続・汎用推論能力の完了は主張しない。

## 2026-11-07 — PoC16: 2つのresetで本当に到達可能なraw状態を8→4に縮約
[正確な検証範囲と反例](poc/POC16_TWO_RESET_FINDINGS_2026-11-07.md) / [8 rawと4同値クラスの実測](poc/POC16_TWO_RESET_OBSERVED_2026-11-07.json) / [再実行可能なJS検証器](poc/poc16_two_reset_quotient.mjs)。PoC7の操作0/1・1bit観測はそのまま、hiddenだけ異なる2つの外部resetを導入。各resetから4 raw、和集合8 raw、分割精緻化で未来観測の最小4クラス、PoC15で以前学習した4状態モデルとの直積検証8状態・16辺PASS。操作2追加ならFAIL、観測値だけで初期モデルIDを固定するとFAIL。**今回は真の到達状態の集約8→4は成立。ただしresetの同じ抽象初期状態は検証者が構成したもので、複数resetからの自動学習や生rawからの投影写像の発見、速度改善は未実施。** 次はreset名と操作履歴だけで初期モデル状態の一致を判定できるかという単一の入口契約を確認する。

## 2026-11-07 — 本線の判断を更新：既存L*で初期reset一つから256→4をブラックボックス学習
[原課題への現在の単一判断（事前登録commitと結果、REUSE判定）](ACTIVE_DECISION.json) / [実行した既存L*移植コード](poc/k0_fixed_reset_blackbox_discovery.mjs) / [実測・独立全到達検算](poc/K0_FIXED_RESET_BLACKBOX_OBSERVED_2026-11-07.json)。
`MGR-P1 k=0` は、元の8bit状態256個すべてが **reset=0, actions=0/1** から到達可能で、全未来の最小出力同値状態は4個（Python独立再計算で確認）。学習器と標本同値照合に与えたのはリセット・操作列→1bit出力だけ。既存PoC7のL*アルゴリズムを移植して実行すると、**学習4状態／重複除去後322問い合わせ／元遷移計算3,874回／EQ 2回**。学習が終わってからソースを参照する全到達チェック256ペア・512遷移PASS（別のPython移植でも一致）、誤った遷移は反例`[0,0]`でFAIL。事前登録 `7982540978ff7cdd5139525a5535186e2fd7703f` より後に実行。**以前のPoC16の恣意的に揃えた2 reset と異なり、固定reset一つから自然に到達する多数の元状態の商を、内部状態なしで学習した限定的な成果**。
進捗評価は `REUSE`：この4状態合成系の類似PoCを自動追加せず、既存の学習器を再利用。学習器は任意の生raw状態→抽象状態の`phi`を導出していない。実行時間や全導入費用の節約は未立証であり、#71 C6とEC本体の全SUITEはOPEN。次の判断前に、実際の出力予測需要と公平な無学習ベースラインを固定する。
