# Issue #1 — 全課題込み・最短一括実行計画 v15（2026-10-11）

## 原要求と不変のAC

- 原課題：S1 Language→Semantics、S2 Semantics→Candidate Set、S3 Candidate Set→Selection/Reframing、S4 Selected State→Execution/Closure。A（LLM/LLM）、B（LLM/EC）、C（固定S2/LLM）、D（固定S2/EC）、E_S1..E_S4（各層のみOracle）の真正な因果比較。
- 原20 AC依存と18必須MVPは[正本](../docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json)どおり。18のうちAC19/20のみPASS。AC10/18はpost-MVP、効果量絶対閾値0.20と優勢タイ差0.10固定。
- 原ECv4.4はS3候補全件集合とS4独立義務状態を表現できない（M003/M009、識別可能性8/10）。これをテスト反復で解消したと偽らない。後継ECは必ず別のversioned successor。
- 新しい13 proof AC、120件任意コーパス、C1-C6横断、モデル4B、GitHub ActionsはMVPに持ち込まない。

## 最短5段階の確定依存・分岐

| 順 | 依存・Issue | 今回実行した事実 | 次段階へ進める本物のAC証拠／停止 |
|---|---|---|---|
| F0：旧EC不適合→versioned successor | #20/23、#59/60、元ECソース | 元ECのS3/S4不適合をソース・反例照合。新EC `GPT-EC-Closure-Engine` PR #34、commit `3f435ad` を固定 | 旧ECを維持するルートは `ROOT_FROZEN_PROTOCOL_INFEASIBLE` で終了。後継はEC変更を記録してF1 |
| F1：第三者ソースから独立正解・S3/S4義務を確保 | #59＋#60 | 公式 JSON Schema Test Suite 独立公開データ `7de0e6a` の required/properties 計46件をSHA固定取得し、`jsonschema`独立検証器と46件一致。**限定した型付き検証の予備実績** | 依然、自然言語S3全許容集合、実タスクS4全義務、正解のblind保持・source custodian認証が未立証：`SUCCESSOR_EXTERNAL_AUTHORITY_NOT_EVALUABLE`。データなしで生成した「正解」禁止 |
| F2：LLM実測と容量の評価 | #14 | **0.5B：1/10、1.5B：9/10。** 両方2026-10-03に同一凍結S3 reframeアッセイで**実推論済み**。両モデルの実物ファイルとSHA確認。1.5Bでcollapse条件解消。旧EC再枠組み9/10だが誤りの位置異なる | **完了：再実行不要、4Bなし。** S3全件選択やS4実タスク成功には転用しない |
| F3：実LLM＋適格native EC＋真OracleのA/B/C/D/E | #61→#9 | 対象外E層のOracleすり替えと自己生成receiptを拒否するv2ゲート・証拠検証器あり | F1のsource custodian認証とOracle blind分離が揃えば、固定S1/S2ハッシュ・source commit・model seed・raw SHA・S3/S4実行証跡の8 armsを一度だけ実行。不整合なら`SUCCESSOR_INVALID_CAUSAL_RUN`で終了。現在`NOT_EXECUTED_UNQUALIFIED_INPUTS` |
| F4：事前固定の指標・AC18スコア | F3→#1 | 旧20AC DAGと0.20閾値は封印、過去の検証器455テスト成功は保持 | 真正なA–E生出力を取得した場合のみSemantic/Candidate Recall、rank、selection、missed reframe、false closure、Oracle gain、cost/latencyを再計算。支配層判定 `LOCALIZED`/差なし `NO_MATERIAL_LAYER`/曖昧 `AMBIGUOUS`/証拠無効 `INVALID`。証拠欠損時は採点せず終了 |

## 検証結果を覆すエラー排除

- **G0 不変性**：元仕様・検証器・旧raw・1.5B測定成果・official corporaのGit blob、ECコミットをpin。前後確認。ハッシュだけで正解の独立性を認定しない。
- **G1 AC依存**：20AC DAGの親未立証なら子ACをPASSにしない。18/18は実行器や型付きpilotのPASSで代替不可。
- **G2 gold漏洩**：予測器が正解を参照すれば無効、重複case IDと後出し正解、調整用に見たデータをheld-outと呼ぶことを無効とする。
- **G3 E対象だけ**：対象外のLLM/EC/Oracle実行器の入替をソース別実行証跡で再現して拒否。自己申告JSON SHAだけでは不合格。
- **G4 反証可能性**：同一証拠fingerprintでの再推論・実験再採点は0回。新しい真の証拠が発生した依存ステージだけ開き直す。旧v1～v13のテストの反復を科学的進捗に数えない。
- **G5 失敗でも最終判定**：不適合、外部正解未取得、容量限界、真正なA–E証拠不備、差なし、効果量曖昧をそれぞれ別の終端で保存。見せかけのAC完了にはしない。

## これまでのTCCとの相違

旧v13：入力条件に関係なく科学的ACを2/18に固定し、改めて455件の回帰テストを繰り返した。

**新v15**：実測済み1.5Bを自動で取り込み、公式第三者データの出典を確定し、全5段階において「出来た」「既に出来ていた」「正しい意味で未取得」を区別して出力する。公的データ46件に対する一致をもって自然言語全体やタスク終了網羅性と誤認しない。

実行コマンド：

```bash
cd /private/tmp/issue1-fast-integrated-v15
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_fast_integrated_v15.py \
  --include-official-pilot \
  --ec-root /private/tmp/issue59-60-policy-v2 \
  --out /private/tmp/issue1_fast_integrated_v15_final_actual.json
```

exit 2：必要な実験材料の欠損を含む**有効な科学的終了判定**（元EC不適合＋後継F1未成立）。exit 3：検証結果を覆すintegrity failure。現状の科学的ACは2/18であり、真の18/18ではない。v15の公開公式46件と過去の0.5/1.5B結果は局所的検証。AC上書き不可。

## 最短で残る不可欠な依存

実装者がいくら検証器を増やしても代替できない条件は、**第三者が出典と採点基準を確定した自然言語S3全候補判定と実タスクS4義務全件の独立gold、および同条件での本物の実装・Oracle実行のsource-pinned receipt**。この2系統が無ければv15は`SUCCESSOR_EXTERNAL_AUTHORITY_NOT_EVALUABLE`を終端として確定し、同じ指示の再投入や疑似ゴールド生成を要求しない。獲得後のみF3/F4を実行する。
