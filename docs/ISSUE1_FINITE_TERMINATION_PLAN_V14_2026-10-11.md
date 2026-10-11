# Issue #1 — 終了するための有限計画 v14（2026-10-11）

## 結論とRCA

旧「AC18一括TCC v13」の工程自体は正常完走するが、**目的を達成する経路は未実装**である。v13は原MVP状態を2/18に固定し、S3/S4独立性を固定falseにしたまま、同じ `blocked_semantics` を返す。検証器のテスト数を増やしても、因果比較に必要な証拠は増えない。

しかも、2026-10-03の正本で固定された **ECv4.4のS3選択/ S4終了インターフェースに構造的不適合が実証済み**：

- `results/ec_native_adapter_qualification.json`：元のECはS3 admissible full-set selectionを実装しない（singleton）。反例M003/M009。S3 native `reportable=false`。
- `results/phase1_s4_identifiability_audit_2026-10-03.json`：同一の観測可能シグネチャからCLOSEとCONTINUEが異なる。元のS4入力だけでは識別不能。10件中最高8件という**識別可能性上限**であり、EC正解率とは違う。
- 後継EC PR #34の形式ポリシーが有限範囲で処理可能になったことは事実。しかしこれを**凍結ECv4.4の同一機能と称することはできない**。原AC正本の比較対象をこっそり差し替えない。

さらに **0.5Bの実推論は未実施ではない**：`results/phase1_qwen25_0p5b_reframe_actual_2026-10-03.json` に元の実測がある。YES 10/10、正解1/10でcollapse成立。元の固定規約で許される残りは**同じアッセイで1.5Bを1回だけ**である。モデルファイルの再確認は科学的な進捗ではない。

したがって**元の固定ECv4.4だけで18/18へ到達する計画は成立していない**。これをループで直そうとせず、`INFEASIBLE_UNDER_FROZEN_ECV4_4_INTERFACE`として原仕様の実行可能性を一度確定する（原Issue #1の「科学的18AC完了」とは絶対に記さない）。新しいECで科学的に続ける場合のみ、明示的にversioned後継比較実験を開始する。

## 真の終了を作る2ルート

### Route A: 凍結プロトコルに厳密準拠

`F0` source blobs/S3・S4反例/0.5B実測照合 → **`INFEASIBLE_UNDER_FROZEN_ECV4_4_INTERFACE`**。

これは固定プロトコルの「条件不成立」の最終的な実験可能性判定で、18/18科学的PASSを偽造しない。既存のv10/v11/v12/v13を再走しない。元Issueはデータ未完了として維持し、固定設計の変更なく再試行を許可しない。

### Route B: 研究目的を実際に答える versioned successor（最大5工程、各1回）

| 工程 | 入力依存 | 本当に終わったといえる証拠 | 一回だけの分岐 |
|---|---|---|---|
| F0 比較対象の適格性 | 原AC20/MVP18、元EC凍結反例、後継EC PR #34 | native実装ID・source commit・意味的機能差を独立に明記した**新しい事前登録契約**。旧結果とは混合しない | 適格ならF1、旧EC強制ならRoute A終了 |
| F1 独立したS3/S4正解の確保 | #59, #60 | タスク文書・規範・必須条件が列挙可能な**閉じた対象領域**を一つ選ぶ。出典・版・公開入力と非公開正解を別管理し、モデル予測確定前に正解を独立作成・固定。候補全件/義務全件/「義務なし」の積極的根拠と反例を持つ | 取得・保管・未知例分離に成功ならF2、独立性を証明できなければ**NOT_EVALUABLE_EXTERNAL_AUTHORITY**で終了 |
| F2 LLM実測 | #14, F1、凍結1.5Bモデル | 既に確認済み0.5Bの実測を再利用。同一アッセイで1.5Bを**1回だけ**実推論・seed/設定/raw SHA保存。大規模モデルへ自動昇格なし | モデル能力不足なら**CAPACITY_LIMIT_1P5B**として終了。能力が評価可能ならF3 |
| F3 A/B/C/D/Eの実行 | #61, #9, F1/F2 | 4層×8 arms、実LLM・qualified native EC・真のOracleのsource-pinned receipts。A/B・C/D同一上流、Eは標的Si以外の実行器を不変とする。署名なき自己作成証拠で通過しない | 1回の凍結実行で全証拠成立ならF4、改変/欠損は**INVALID_CAUSAL_INTERVENTION**で終了 |
| F4 指標とACの独立再計算 | F3 | Semantic/Candidate Recall、rank、selection/reframe、False Closure、Missed Reframe、Final Success、Oracle gain、コスト。閾値0.20は維持。ゴールド非可視・source/input pre/post seal、AC20依存を独立照合 | **LOCALIZED / NO_MATERIAL_DIFFERENCE / AMBIGUOUS / INVALID_EVIDENCE**のどれかを確定して終了 |

**MVPは科学的に報告できる原18AC相当を維持**し、post-MVP AC-10/18、120件拡大、追加13 proof AC、C1〜C6は引き続き不要。ただしRoute Bは**新しいEC実装を比較する別バージョン**であり、元の凍結ECv4.4に対する18/18 PASSと同一視してはならない。正解が独立に用意できない場合に「成功」と宣言することも禁止。

## 必須のloop-breakerと改竄ゲート

1. **結果の指紋**：契約・EC実装・生データ・モデル・gold/source commitのSHAを結合。指紋が同じなら結果を再解析・再推論・再採点しない（追加試行=0）。再起動時は既存レポートを返す。
2. **変更条件**：未達箇所に直接対応する新しい証拠が現れた場合のみ、該当する依存工程から1回再開する。単なるソーステスト追加/新TCCバージョン/レポート書式変更は新証拠として認めない。
3. **最大試行**：適格性検討1、source-qualified独立pilot1、1.5B capacity follow-up1、full A–E1、採点1。試験と全証拠がINVALIDなら同条件再試行を許さず、原因と入力の指紋を記録して終了。
4. **停止は成功と区別**：実験成功、差なし、曖昧、容量不足、構造的に評価不能、真性改竄、独立証拠欠落をそれぞれ**最終状態**として報告。ユーザーに「進めて」を繰り返し求めない。
5. **反証ゲート**：凍結ソースblob、Oracle/gold分離、ラベル漏洩、重複評価、同一入力、下流の非標的エンジン再実行証跡、raw/設定pre/post hash、LLM実測/モデル真正性、結果の改変、AC親の未達を一つでも検出したら科学的PASSを撤回し、出力をINVALIDとする。
6. **閉じた実行責任**：独立正解／真正なruntimeを取得できる主体が未確認の時点では「残りはTCCを回せば自動的に終わる」とは記載しない。実装上の機械的ゲートは動くが外部の証拠収集が必要という事実を、1回の前提確認で明示する。

## 今回の実行

- `tools/run_issue1_finite_exit_preflight_v14.py`：正本資料と0.5B実測のGit blobを照合。旧EC S3/S4反例を確定、同一証拠fingerprint再走禁止をレポート。
- `tests/test_issue1_finite_exit_preflight_v14.py`：前提改ざん、旧資料の偽装、0.5B実測改ざん、ループ禁止、false 18/18防止。7件PASS。
- 実際の出力：`results/issue1_finite_exit_preflight_v14_actual_2026-10-11.json`。
- 結論：現行の凍結仕様は `INFEASIBLE`、0.5Bは既に実測済み。versioned後継に進むかどうかは元の設計変更とは**別の意思決定**であり、勝手に比較対象を書き換えない。
