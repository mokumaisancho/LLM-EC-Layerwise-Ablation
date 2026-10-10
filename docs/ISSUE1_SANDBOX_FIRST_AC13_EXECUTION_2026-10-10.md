# Issue #1 — サンドボックス優先実行と13証明ACの証拠ゲート（2026-10-10）

**検証結果：サンドボックス単体テスト13件PASS。EC/TCC固有の統合検証のみMac経由で実行し、整合性ゲートPASS。原課題は2/18 ACで未完了。**

## 実行環境の決定規則

| 作業 | 使用環境 | 理由 |
|---|---|---|
| AC/DAG/MVP判定、Python実装、13証明AC入力の構造検査、データ汚染・SHA・S4トレース検査 | **ChatGPTサンドボックス（標準）** | Mac上の既存資産に依存せず、起動とファイル転送の手間を減らせる |
| 正本保存・レビュー・issue連携 | **GitHub連携** | リポジトリに直接差分を保存 |
| 実LLMモデル・EC native・TCC compilerの凍結済み環境との統合検証 | **Mac接続（必要時のみ）** | 既存のモデルバイナリ・固定EC/TCCソースの機能を確かめる必要があるため |
| 独立した人間の裁定・ゴールドデータ・S4の規範文書 | **外部の独立権限者による提供** | Sandbox/DCの選択では解決できない |

全処理にDCを使う構成には戻さない。Mac固有の処理以外はサンドボックスでコード検証する。

## 今回追加・接続した成果

- [ポータブルな独立証拠入力の検証器](../tools/issue1_proof13_portable_preflight_v1.py)：原課題18AC・追加13 ACの凍結ハッシュ、外部ファイルSHA、holdout120件以上、文書ID重複、系列・完全一致文書のsplit間混入、S4義務と条項の双方向対応、空義務台帳の肯定証拠を機械検査。**通過しても独立性の認証はしない**。
- [サンドボックスで実行済みの13件の単体/異常系テスト](../tests/test_issue1_proof13_portable_preflight_v1.py)：Git source blobがサンドボックスで実行したコードと一致。13/13 PASS。
- [証拠の提出テンプレート](ISSUE1_INDEPENDENT_PROOF_EVIDENCE_SUBMISSION_V1.template.json)：空のままでは独立証明は成立しない。
- [TCC v9](../tools/run_issue1_root_ac_continuation_tcc_v9.py)：既存13 ACのledger算出分岐でポータブル検査器を実行。外部資料がある場合は `--proof-bundle-root` と `--proof-submission` で読み込み、資料ハッシュを前後照合。**元の18 ACの結果は一切自動昇格させない**。
- [TCC v9実行結果](../results/issue1_root_ac_tcc_v9_sandbox_first_portable_actual_2026-10-10.json)：12ノード・17エッジ、追加形式検証48ケース、S4有限936状態、証拠台帳13件、ソースハッシュ照合すべて実行。**コード・証拠整合性のエラー0**。

### サンドボックスのみで実行する方法

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -q tests.test_issue1_proof13_portable_preflight_v1
python3 tools/issue1_proof13_portable_preflight_v1.py \
 --plan docs/ISSUE1_W4B_W4C_INDEPENDENT_PROOF_AC_V1.json \
 --bundle-root /path/to/independent-evidence \
 --submission /path/to/submission.json \
 --out /path/to/preflight.json
```

ポータブル検査の **exit code 2** は「構造を検査したが第三者の独立性は未証明」という正直な状態。 **3** は契約/資料の破損・汚染検出。 **0は科学的PASSとして使用禁止**。

### TCC v9への接続

既存の凍結済みTCC/EC環境の統合実行は従来の4つの引数で継続できる。外部証拠を受領したときだけ次の引数を追加。

```bash
--proof-bundle-root /path/to/independent-evidence \
--proof-submission /path/to/submission.json
```

証拠検査は必ず原契約ハッシュ/18 AC依存関係・S4形式的安全性の後段で実行。試験中の変更や未認証の独立性自己申告を許可しない。現在の最後の判定は **proof 0/11・原課題2/18 AC** であり、独立した意味判定資料と義務台帳の網羅性が次の真正な依存条件。

**科学的制約**：上記は入力検査・汚染対策と正本への統合を完了させたものであり、独立した実文書120件、人間による盲検二重ラベル・裁定、S4規範台帳の独立レビューを実際に作成したことを意味しない。既存のC03有限状態936件の結果は追加13 ACの部分証拠に過ぎない。外部の真正な資料が揃うまで元の科学的ACのPASSを増やせない。
