# Original Phase1 — AC20依存関係・MVP18・一括TCC v13（2026-10-11）

## 完了判定（変更禁止）

- 正本：`ACCEPTANCE_CRITERIA.md` + `docs/PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`。
- 対象：原Issue #1のS1意味抽出、S2候補生成、S3選択／再枠組み、S4実行／終了のみ。実験A/B/C/Dと各層E_Siを含む。
- MVPはAC-01～09、AC-11～17、AC-19、AC-20の**18件すべてを科学的にPASS**。現在PASSはAC-19/20の**2件**、残16件はNOT_PROVEN。
- AC-10/18はpost-MVP。S1/S2のEC実装、追加13 proof AC、120件コーパス、C1～C6全域への拡張はMVP外。
- Oracle gain絶対差0.20、優勢タイ許容差0.10、モデル最大自動昇格約1.5B、4B自動実行禁止。

## 全20 ACの直近依存関係（原正本と完全一致）

| AC | 状態 | 直接のAC／旧Issue依存 | 必要なW工程 |
|---|---|---|---|
| AC-01 | NOT_PROVEN | AC-02 | W07 |
| AC-02 | NOT_PROVEN | AC-19 | W07 |
| AC-03 | NOT_PROVEN | AC-02, AC-19, ISSUE-22 | W04, W05, W07 |
| AC-04 | NOT_PROVEN | AC-02, AC-03 | W08 |
| AC-05 | NOT_PROVEN | AC-01, AC-03, AC-04, AC-07, AC-17, ISSUE-22 | W06, W07, W08 |
| AC-06 | NOT_PROVEN | AC-04, AC-05, AC-11, AC-12, AC-16, AC-17 | W08 |
| AC-07 | NOT_PROVEN | AC-01 | W06, W07 |
| AC-08 | NOT_PROVEN | AC-05, AC-06, ISSUE-21 | W08, W09 |
| AC-09 | NOT_PROVEN | AC-05, AC-08, ISSUE-21 | W08, W09 |
| AC-10 (post) | NOT_PROVEN | AC-08, AC-09, AC-19 | W09 |
| AC-11 | NOT_PROVEN | ISSUE-23, ISSUE-20 | W04, W05 |
| AC-12 | NOT_PROVEN | AC-04, AC-11 | W05, W08 |
| AC-13 | NOT_PROVEN | ISSUE-12, ISSUE-22 | W03, W07 |
| AC-14 | NOT_PROVEN | AC-01, AC-13 | W03, W07 |
| AC-15 | NOT_PROVEN | — | W03, W07 |
| AC-16 | NOT_PROVEN | AC-17 | W06, W08 |
| AC-17 | NOT_PROVEN | AC-07 | W04, W05, W06 |
| AC-18 (post) | NOT_PROVEN | AC-03, AC-06, AC-08, AC-10_IF_NEEDED | W09 |
| AC-19 | PASS | — | W00 |
| AC-20 | PASS | — | W00 |

「#12/#20～23がclosed」「形式ポリシーテストPASS」「モデルSHA一致」は、**個別の科学的AC達成を意味しない**。親AC未達の子ACはPASSにできない。TCCはAC20全件の `unmet_AC_parents` と `unqualified_work` を一括計算する。

## 仕事の依存関係と一括分岐

| ステージ | 前提 | Issue | 実行・判定 |
|---|---|---|---|
| W00 | — | — | frozen AC20+MVP18; threshold 0.20; base source seals; external input SHA pins |
| W01 | W00 | #1 | v10→v11→v12 compiled TCC; 17 E adversarial controls; 46 S3/S4 source tests; original 2/18 ledger |
| W02 | W01 | #1 | 20 AC topological DAG; 18 MVP statuses; post-MVP 10/18 excluded; issue snapshot |
| W03 | W02 | #14 | verified lightweight LLM source/cache/model receipts or explicit blocker |
| W04 | W02 | #59 | source-custodied independently blind S3 judgments or explicit blocker |
| W05 | W02 | #60 | independently complete S4 obligations incl positive empty proof or explicit blocker |
| W06 | W03+W04+W05 | #61 | trusted actual source-pinned target-only E replay / abstain |
| W07 | W06 | #9 | A/B/C/D/E_S1..S4 all matched; genuine model+EC+Oracle traces / abstain |
| W08 | W07 | #1 | candidate recall; selection accuracy; false closure; missed reframe; oracle gain per layer; latency/cost |
| W09 | W08 | #1 | no AC PASS with failed prerequisite; fixed 0.20; dominant layer/tie/no gain |
| W10 | W09 | #1 | 18/18 scientific PASS, else evidence-specific blocker |

優先順位：まず**#59独立S3意味判断と#60独立S4義務網羅**（並列）、加えて**#14軽量LLM実推論および#61実行・Oracle証跡**。すべて成立した後、**#9 A–E同条件実験**、#1 指標算出・層特定・18AC決裁を実行する。事実上のクリティカルパスは W04/W05 → W06 → W07 → W08 → W09/W10。モデル資産は2026-10-11、Qwen2.5-0.5B の397,808,192バイト／固定SHAを実機で確認したが、モデルの再推論/キャッシュ・独立結果は未立証。

## 条件分岐・結果を覆すエラー対策

- **正常・未充足**：依存レポート、機械実行可能なv10→v11→v12の全検証、モデル資産、AC20判定まで1回で走り切る。その後独立意味判断不足なら `blocked_semantics` を証拠付きで返す。必要な独立素材がないだけで仮の成功結果を生成しない。
- **S3**：LLM出力・S2公知情報から各候補を独立に意味評価し全許容集合を立証できない→BLOCKED。形式ポリシーの一致は診断値。
- **S4**：必須義務と空集合の根拠を独立ソースで証明できない→BLOCKED。単なる `inventory_closed=true` は不合格。
- **LLM**：固定0.5Bモデルファイルの正しいハッシュだけなら `ASSET_VERIFIED`、実推論の再現・設定・seed・キャッシュがなければAC13～15は未立証。サイズ/ハッシュ不一致→`INTEGRITY_FAIL_CLOSED`。
- **E Oracle**：対象SiのみOracleへ置換、その他は信頼済み実装で実際に再実行。余分なOracle変更、エンジンすり替え、失われたreceipt、虚偽の結果、隠れgoldへのアクセス→`blocked_integrity`。未認証のraw/receiptを入力しても科学的PASS不可。
- **A–E**：全4層で固定上流、8 arm（A/B/C/D/E_S1..4）、独立gold、LLM/native双方の同条件が揃わない→`blocked_ae`/適切な前提ブロッカー。
- **指標**：Candidate Recall、Selection Accuracy、False Closure、Missed Reframe、Residual Recall、Reframing Recovery、Oracle gain等を独立再計算。得点差だけで因果層を推定しない。閾値変更や観測後フィクスチャ変更はversioned後継が必須。
- **改ざんG0/G7**：計画、元AC、v12/v13、Oracle v2、テストのGit HEAD blob、外部raw/gold/public SHAを開始/各工程後/終了で再照合。0.5BモデルはストリーミングSHAを最初と最後に照合。実行中の証拠変更はfail closed。
- **依存G1/G2/G11**：AC20／11工程（W00～W10）の欠落・未知親・循環・MVP範囲逸脱・未達親の子AC PASS・本物でない18/18成功を拒否。Actions自動実行は行わない。
- **検証器**：v13は旧v10～v12を改変せず利用。原研究の凍結資料は上書きしない。TCC本体のノードが成功しても、それは「チェック作業の実行成功」であり、MVP科学的PASSとは別の状態値。

## 1回の再実行

```bash
cd /private/tmp/issue1-ac18-onecall-tcc-v13
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_original_phase1_tcc_v13.py \
 --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
 --old-native-root /private/tmp/issue1-ec-native-layerwise-20261010 \
 --policy-native-root /private/tmp/issue59-60-policy-v2 \
 --model /private/tmp/llmec-qwen-comparison-20261009/Qwen2.5-0.5B-Instruct-Q4_K_M.gguf \
 --out /private/tmp/issue1_original_phase1_v13_onecall_actual.json
```

CLI終了2は**調査上の正常なBLOCKED**、3はソース/入力/コードの整合性エラー。実行不能な独立外部素材が提供されるまでは、再プロンプトを要求せず正しい停止地点を証跡で固定する。ローカルの作者所有ソースやハッシュだけでは実験の独立性・正解の真正性を証明できないため、全16未立証ACを自動的にPASSへ昇格する分岐は有効化しない。

## 実行証拠・差分

- v13全AC20依存判定と実測結果：`results/issue1_original_phase1_ac18_onecall_tcc_v13_actual_2026-10-11.json`。
- 機械可読な詳細計画：`docs/ISSUE1_ORIGINAL_PHASE1_AC18_ONECALL_PLAN_V13_2026-10-11.json`。
- Source EC policy #59/#60：EC draft PR #34、原研究v12 draft PR #63、#61 replay draft PR #62を保持する。進行中のv13はversioned別PR。
