# Issue #1 — 元のPhase 1 S1〜S4専用 TCC v10（2026-10-10）

**原課題の正本**：[`ACCEPTANCE_CRITERIA.md`](../ACCEPTANCE_CRITERIA.md)、[`PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json`](PHASE1_MVP_AC_DEPENDENCY_TCC_2026-10-03.json)。元のPhase 1以外へ研究テーマを拡張しない。

## MVPと科学的な終了条件

原課題MVPはAC-01〜09・11〜17・19〜20の**18件がすべてPASS**すること。AC-10とAC-18はpost-MVP。元の効果閾値は絶対差0.20。S1/S2はLLM/Oracle、S3/S4はLLM/真正なnative EC/Oracle。A/B/C/Dは固定された同一上流アーティファクトで比較し、EはS1〜S4の各1層だけをOracleへ置換する。観測された終端性能差だけから原因層を特定しない。

**v10の実測結果：TCC 11 nodes / 15 edges、元の18 ACは2件のみ科学的にQUALIFIED、term `blocked_native`。** 元の凍結済みECv4.4はS3でsingleton次アクションしか返せずM003/M009の複数候補を表現できない。元のS3からはS4のCLOSE/CONTINUEを区別できず、元の10例における構造署名の最良識別上限は8/10。これはEC性能ではなく**情報不足の上界**。

## 自動処理の作業依存関係

| 順序 | TCC Node / 課題 | 依存 | ゲート |
|---|---|---|---|
| W0 | `freeze_original_source` | なし | 元のAC文書、Phase1正本、native EC証拠、S4署名反例、実行コードすべてGit tracked blobs |
| W1 | `verify_original_AC20_MVP18` | W0 | 本来の20 ACと必須18 ACをトポロジカル順序で検査。未達先行ACをPASSにしない |
| W2 | `probe_original_native_S3_S4` | W1 | 凍結済み真正ECv4.4のsingleton S3/情報不足S4の反例を再計算。不適合を正常な科学結果として保存 |
| W3 | `check_versioned_native_successor` | W2 | 新ECが渡された場合はGit commit/module/test blobを検証。ただし構造テストを独立した意味的正確性へ昇格禁止 |
| W4 | `replay_matched_AE_evidence_if_supplied` | W3 | A/B/C/DおよびE_S1〜E_S4のraw、上流固定、全層ハッシュ、欠落/重複、元Oracle分離を再計算。任意入力がない場合は未実行を明記 |
| W5 | `evaluate_original_layer_gains_and_AC_exit` | W4 | rawがある場合だけ効果量0.20で層別の構造的gainを再計算。rawの整合性は実モデル/native同等性の証明とは分離 |
| W6 | `strict_original_phase1_exit` | W5 | 本来の18/18と真正A-E・ソース互換性が揃うまで `ROOT_MVP_VERIFIED` を禁止 |

EC native不適合時も、実行できる残りの証拠・TCC処理を完了してから `blocked_native` に収束する。元の凍結実験を変更せず、変える場合は別名・別ハッシュの後継プロトコルを設ける。

## 何を検証済み／未検証として扱うか

- **検証済み**：原AC20・MVP18の不変性、旧nativeとのS3/S4不一致、両者のインターフェース識別反例、現時点の2/18 AC、バージョン固定されたTCCが一括で実行されること、A-E形式の構造検査と誤評価ゲート。
- **機械的に再計算可能**：もし真正なA-E rawと別保管のOracle goldが届けば [`issue1_phase1_ae_gate_v1.py`](../tools/issue1_phase1_ae_gate_v1.py) が同一性・層間SHA・介入の前段非変更・8条件完全性と gainを計算する。
- **科学的には未検証**：new ECが外部から与えられたS3 adjudicationsなしで自然言語意味判断できること、S4必須条件の十分な導出、真正なモデル/EC同条件A〜Eの実推論と因果比較。これらは作者が記載した `PASS` や構造的テストでは代用不可。
- **正本から除外**：追加の13件の証明AC、120件の独立文書要件、C1〜C6全体、元の再帰学習問題。これらはこの狭いPhase1の必須ACに追加しない。

## 起動方法

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/run_issue1_original_phase1_tcc_v10.py \
  --tcc-root /private/tmp/llmec-tcc-generator-reference-20261009 \
  --native-successor /private/tmp/issue1-ec-native-layerwise-20261010 \
  --out /private/tmp/issue1_original_phase1_v10_actual.json
```

元の上流同一性を保持したA〜E生データと別ファイルのgoldがある場合は `--arms <path> --gold <path>` を追加する。生データの提出だけではoriginal ACを増やさない。outputのコード2は科学的なnative source blocker、3は整合性/実行失敗。コード0の科学的PASSをこの研究段階では返さない。

## 結果を覆すエラーのゲート

- **G0/G7**：元のAC/SCHEMA、ECv4.4資格証明、S4元の識別反例、実行Python/AEスコアのGit HEAD blobを開始時と各実行工程後に照合。
- **G1/G2**：元の20/18 AC依存関係の循環・欠落・前提未達PASS検出。判定後20件の依存・状態をraw証拠に残す。
- **G3**：new ECは異なるsource commit+module/test blobを照合し、真正の旧ECへ擬装したらreject。sourceは各stage後再検証。
- **G4/G5**：A/B共通S1,S2、C/D共通S1,S2、E各層の前段同一、Oracle対象層一致、すべての8 armのS1→S4 SHA chainを検査。
- **G6/G9/G10**：Oracle goldとpredictions別保管、偽native実装名、重複ケース/腕、欠落ケース、異常スキーマはreject。構造整合性を真正モデル/独立gold provenanceへ昇格禁止。
- **G11**：原課題の真の完了は18 AC全PASS、完全なソース互換のnative EC実験、全層A〜Eを実際に実行し、Oracleで対象層だけを介入した場合に限定。現在の誠実な結果は **2/18**。

**残る実作業**：外部 adjudication を入力するだけのECではなく、公開S1/S2から候補の許容性を判断し、S4終了に必要な状態を推論・記録できる versioned EC sourceと、それに対する同条件LLM/Oracle全層の実験を実行すること。元のEC固定入力だけでは達成不能であること自体が、現在の有効な実験結果である。
