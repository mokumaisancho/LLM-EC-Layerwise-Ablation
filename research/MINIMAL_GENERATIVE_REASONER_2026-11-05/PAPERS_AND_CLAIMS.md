# 参照論文・技術的主張・議論論点の対応台帳

記録日: 2026-11-05 / 主題: ROOT-GEN-001。
重要: 論文が示したことと、今回の独立小型推論器への**適用仮説**を同一視しない。
証拠区分: **T**=特定条件で定理・証明、**E**=論文の実験報告、**F**=形式的枠組み、**H**=今回の適用は仮説、**R**=本会話で言及済みだが今回原典再精査なし。
この台帳の「再確認」は原典のメタデータ・概要や本文の一部の照合であり、論文の全実験追試を意味しない。

## A. 重要な一次資料（今回URL・原典を再確認）

### P01
- **Cook (2004), Universality in Elementary Cellular Automata — Rule 110**。[原典](https://www.complex-systems.com/abstracts/v15_i01_a01/)
- 論点: Q07/Q08、T01/T02。ごく簡潔な局所規則による普遍的計算。
- 区分: **T**（所定の初期条件と計算モデルの下で）。有限時間・有限資源での高度な推論の保証ではない。

### P02
- **Hutter (2005), Universal Artificial Intelligence: Sequential Decisions Based on Algorithmic Probability**。[著者ページ](https://www.hutter1.net/ai/uaibook.htm)
- 論点: Q04/Q07、T01/T03。事前知識の大量格納とは異なる普遍的意思決定の理想化。
- 区分: **F/T**。AIXI本体は計算不能、実用的最小推論器の存在証明ではない。

### P03
- **Vereshchagin & Vitányi (2004), Kolmogorov's Structure Functions and Model Selection**。[原稿](https://arxiv.org/abs/cs/0204037)
- 論点: Q03/Q05/Q06、T01。説明に必要な構造の情報量と残差の情報量。
- 区分: **T**（アルゴリズム情報理論）。計算不能性や最適化の困難が残る。

### P04
- **Crutchfield & Shalizi (1999), Thermodynamic Depth of Causal States: Objective Complexity via Minimal Representations**。[原典](https://doi.org/10.1103/PhysRevE.59.275)
- 論点: Q12/Q13、T07/T08。未来予測を維持する因果状態の最小表現。
- 区分: **T/F**（特定の過程・観測設定）。すべての推論能力の最小化を意味しない。

### P05
- **Wu & Fischer (2020), Phase Transitions for the Information Bottleneck in Representation Learning**。[原稿](https://arxiv.org/abs/2001.01878) / [公開論文](https://openreview.net/pdf?id=HJloElBYvB)
- 論点: Q13、T09。情報表現における相転移、学習の質的変化、臨界点の条件。
- 区分: **T/E**（IB目的関数に関して）。推論可能態が同じ地点で飛躍することは**未証明**。
- 関連: **Wu, Fischer, Chuang & Tegmark (2020), Learnability for the Information Bottleneck**。[PMLR](https://proceedings.mlr.press/v115/wu20b.html)

### P06
- **Shalizi & Crutchfield (2002), Information Bottlenecks, Causal States, and Statistical Relevance Bases**。[原典](https://doi.org/10.1142/S0219525902000481)
- 論点: Q13、T08。予測に関係ある情報を表現に残す方法の比較。
- 区分: **F**。Markov chain lumpability / deterministic factor map の全条件をこの論文だけが証明したとは言わない。

### P07
- **Brunton, Brunton, Proctor & Kutz (2016), Koopman Invariant Subspaces and Finite Linear Representations of Nonlinear Dynamical Systems for Control**。[原典](https://doi.org/10.1371/journal.pone.0150171)
- 論点: Q12/Q13、T07。非線形系を観測関数の空間で線形に扱える条件。
- 区分: **T/E**（特定条件・系）。一般に有限次元で完全に表せるわけではなく、次元の増大を伴いうる。

### P08
- **Brunton, Proctor & Kutz (2016), Discovering Governing Equations from Data by Sparse Identification of Nonlinear Dynamical Systems (SINDy)**。[原典](https://doi.org/10.1073/pnas.1517384113)
- 論点: Q12、T07。適切な関数基底で少数項の支配方程式を発見。
- 区分: **E/F**。観測データから方程式を同定する技術であり、最小推論器の自動発見そのものではない。

### P09
- **Hoel, Albantakis & Tononi (2013), Quantifying Causal Emergence Shows That Macro Can Beat Micro**。[原典](https://doi.org/10.1073/pnas.1314922110)
- 論点: Q12、T07。巨視的記述の方が有効情報量が大きくなる場合。
- 区分: **T/E**（選んだ介入・測度・粗視化に依存）。巨視的現象が計算資源を無料で増やすわけではない。

### P10
- **Bonifaci, Mehlhorn & Varma (2012), Physarum Can Compute Shortest Paths**。[原典](https://pubmed.ncbi.nlm.nih.gov/22732274/) / [学会版](https://doi.org/10.1137/1.9781611973099.21)
- 論点: Q10/Q11、T04/T05。粘菌の局所適応モデルが最短経路へ収束する条件付き証明。
- 区分: **T**（特定の数学モデル）。実生物が一般的NP困難問題を常に最適解に導くとの証明ではない。
- 関連: **Nakagaki et al. (2000), Maze-Solving by an Amoeboid Organism**。[Nature](https://www.nature.com/articles/35035159)

### P11
- **Pressé, Ghosh, Lee & Dill (2013), Principles of Maximum Entropy and Maximum Caliber in Statistical Physics**。[原典](https://doi.org/10.1103/RevModPhys.85.1115)
- 論点: Q10、T04/T05。動的な経路確率を制約の下で扱う。
- 区分: **F**。有効な推論フィルターを自動生成するという証拠ではない。

### P12
- **Montévil & Mossio (2015), Biological Organisation as Closure of Constraints**。[原典](https://doi.org/10.1016/j.jtbi.2015.02.029)
- 論点: Q10/Q11、T04/T05。生物の制約が相互に成立・維持される構造。
- 区分: **F**（生命組織の理論）。推論器への転用は **H**。

### P13
- **Schmidhuber (2013), PowerPlay: Training an Increasingly General Problem Solver by Continually Searching for the Simplest Still Unsolvable Problem**。[原典](https://doi.org/10.3389/fpsyg.2013.00313)
- 論点: Q07/Q09、T01/T12。課題を自ら発明・解決し、能力を拡張する設計。
- 区分: **F/E**。初期探索メカニズムや反例・検証は外部から与えられる。

### P14
- **Ellis et al. (2021), DreamCoder: Bootstrapping Inductive Program Synthesis with Wake-Sleep Library Learning**。[原典](https://doi.org/10.1145/3453483.3454080)
- 論点: Q07/Q09、T01/T12。少数の初期演算と課題から新しいライブラリと探索方針を獲得。
- 区分: **E**。与えられる課題、DSL、検証器、計算資源は必須前提。

### P15
- **Schwarzschild et al. (2021), Can You Learn an Algorithm? Generalizing from Easy to Hard Problems with Recurrent Networks**。[原典](https://proceedings.neurips.cc/paper/2021/hash/3501672ebc68a5524629080e3ef60aef-Abstract.html)
- 論点: Q08/Q09、T01/T12。反復回数を増やすことで小問題から大問題へ外挿。
- 区分: **E**。検証されたアルゴリズム課題の範囲内。

### P16
- **Jolicoeur-Martineau (2025), Less is More: Recursive Reasoning with Tiny Networks (TRM)**。[原稿](https://arxiv.org/abs/2510.04871)
- 論点: Q07/Q08、T01/T12。約7Mパラメータの再帰NNでARC-AGIの特定セットに対する高成績を報告。
- 区分: **E**。事前学習なしの汎用大規模LLM代替や下限の証明ではない。

### P17
- **Kolchinsky & Wolpert (2018), Semantic Information, Autonomous Agency and Non-equilibrium Statistical Physics**。[原典](https://doi.org/10.1098/rsfs.2018.0041)
- 論点: Q10、T04/T10。「意味」を機能・存続への因果的寄与として扱う。
- 区分: **F**。数学的真理や推論の正しさに直接同一視できない。

### P18
- **Boopathy et al. (2023), Model-agnostic Measure of Generalization Difficulty**。[原典](https://proceedings.mlr.press/v202/boopathy23a.html)
- 論点: Q04/Q05/Q12、T02/T03。タスク固有の帰納バイアス必要量と内在次元の関係。
- 区分: **T/E**（定義されたタスク分布の下で）。一般の推論能力の事前完全推定ではない。

## B. 会話で参照した関連研究（重要だが、今回の一次確認は一部に限定）

| ID | 研究・資料 | 接続する論点 | 本台帳での扱い |
|---|---|---|---|
| P19 | [Baldi & Vershynin (2019), The Capacity of Feedforward Neural Networks](https://www.sciencedirect.com/science/article/pii/S0893608019301078) | Q04/Q05; 構造が表現し得る関数容量 | **R**、モデル固有 |
| P20 | [Elhage et al. (2022), Toy Models of Superposition](https://transformer-circuits.pub/2022/toy_model/index.html) | Q05/Q12; 少数次元への多特徴の重畳 | **R**、表現 ≠ 正しい推論 |
| P21 | [Legg & Hutter (2007), Universal Intelligence](https://arxiv.org/abs/0712.3329) | Q04; 課題分布にわたる性能 | **R**、実用上の直接計測不能 |
| P22 | [Tishby, Pereira & Bialek (1999/2000), The Information Bottleneck Method](https://arxiv.org/abs/physics/0004057) | Q06/Q13; 必要情報の保持 | **R**、圧縮は出発点ではない |
| P23 | [Delétang et al. (2024), Language Modeling Is Compression](https://arxiv.org/abs/2309.10668) | Q06; 予測と符号長の対応 | **R**、LLM構築を前提にしない根拠にはならない |
| P24 | [Compression Represents Intelligence Linearly (2024)](https://arxiv.org/abs/2404.09937) | Q06/Q04; 圧縮指標と推論評価の相関 | **R**、相関であり潜在能力の証明でない |
| P25 | [Mehta & Schwab (2014), Exact Mapping between RG and Deep Learning](https://arxiv.org/abs/1410.3831) | Q12; くりこみ群・尺度変換 | **R**、特定モデルの対応 |
| P26 | [Cook (2004), Rule 110](https://www.complex-systems.com/abstracts/v15_i01_a01/) | P01と同一出典。会話で繰り返し参照 | **重複・別文献として計上しない** |
| P27 | [Merrill & Sabharwal (2023), The Expressive Power of Transformers with Chain of Thought](https://aclanthology.org/2023.tacl-1.31/) | Q04、Transformer計算力の上限 | **R**、本文・題名の再確認要 |
| P28 | [Spelke: Core Knowledge (関連研究)](https://www.harvardlds.org/our-labs/spelke-lab/) | Q03; 先行する能力と経験知識 | **R**、発達認知の類推 |
| P29 | [Schmidhuber (2004), OOPS](https://arxiv.org/abs/cs/0207097) | Q07; 解法・探索方法の再利用 | **R**、探索コスト |
| P30 | [Wolfram, A New Kind of Science](https://www.wolframscience.com/nks/) | Q08、局所規則と複雑な結果 | **R**、計算・推論性能と区別 |
| P31 | [Causal Emergence (Hoel et al.)](https://doi.org/10.1073/pnas.1314922110) | P09と同一 | **重複・別文献として計上しない** |

## C. 論文から直接は言えない主張（OPEN）

1. 「極小の計算規則が万能である」 → 「巨大LLM級の高度な推論が有限費用で可能」。**論理的飛躍**。
2. 「ある投影で状態数が減る」 → 「推論可能態の範囲が広がった」。**未来・出力・正解の保存確認が必要**。
3. 「IB相転移が存在する」 → 「推論能力・知識の最小構成に普遍的臨界点がある」。**未実証**。
4. 「粘菌モデルが経路へ収束する」 → 「意味ある高度な推論の全問題を局所動力学に置換できる」。**未実証**。
5. 「知識を外に出しても高性能」 → 「初期構造全体の情報量が小さい」。**外部情報・環境・検証器を計上する必要**。
6. 「大きいLLMに対する小さなモデルの同点」 → 「推論能力が同一」。**課題分布・評価・漏洩・コストを明記**。

## D. 最優先で深く読む順番
- **D1: P04 + P06 + P05** — 何が同じ未来を生む状態なのか、投影臨界点は何か。
- **D2: P10 + P12 + P11** — 局所的な制約で正しい解への経路が自然に生じるか。
- **D3: P14 + P13 + P15 + P16** — 初期規則から自己拡張する能力を計測した実験。
- **D4: P07 + P08 + P09** — 高低次元の変換で表現上の複雑性と総計算費用はどう変わるか。

※ D1〜D4 は並列の文献調査軸であり、すべてを終了しないと次へ進めない工程順ではない。実装前の単一決定点は [TECHNICAL_DEPENDENCIES.md](TECHNICAL_DEPENDENCIES.md) のB0。
