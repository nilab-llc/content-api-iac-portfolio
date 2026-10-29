# Terraform版：設定変更・障害調査と復旧・削除再構築の実測記録

実施日：2026-10-28（日本時間）。ユーザー承認の範囲で、東京リージョンのテスト環境 `nilab-content-tf` に限定して実行した。実施順序はTerraform → アプリ確認。3方式のうちTerraform版の結果であり、CloudFormation・CDKの実施結果ではない。

## 目的と結果

| 検証 | 予定と実結果 |
|---|---|
| 事前退避 | テーブル内の既知のテスト記事が1件だけであることを確認。強い整合性の読み取りとHTTP応答の全項目一致を確認し、記事JSON・Terraform状態を端末へ退避 |
| 設定変更 | メモリ128→256MB、ログ保持7→14日。planは既存2件の更新のみ、追加・削除なし。apply成功 |
| データ保持 | 設定変更後のGET 200。ID、作成日時、タイトル、本文の全項目が退避データと一致 |
| エラー訓練 | Lambda環境変数 `SIMULATE_STORAGE_FAILURE=false→true` だけを変更。記事GETは503。未認証は403、生存確認は200 |
| 原因確認 | CloudWatch Logsで `RuntimeError: storage_failure_drill` を検出。訓練フラグにより、DynamoDB呼び出し前に保存処理を止めたことを確認 |
| 復旧 | 同フラグをtrue→falseに戻す変更だけを反映。記事GET 200、既存記事全項目一致 |
| 削除 | 退避と各段階の確認記録の存在を検証後、planで対象6件の削除だけを確認。applyは6 destroyed |
| 再構築 | 同じコード・既定値からplanで対象6件の作成だけを確認。applyは6 added。権限境界とAWS_IAMを維持 |
| データ再投入 | 新テーブルが空、旧IDのGETが404であることを確認。退避したタイトル・本文を共通APIから再登録し、GET 200・登録応答との全項目一致を確認 |
| 最終確認 | 未認証403、生存確認200、Terraform planはexit 0 / No changes |

## 時刻の記録（JST）

- 16:53:57：事前退避結果
- 16:55:03：設定変更後の記事保持確認
- 16:55:34：訓練エラー503を確認
- 16:55:46：原因ログの取得結果
- 16:56:23：復旧後の記事取得200・全項目一致
- 16:57:44：再構築後の再投入・取得結果

時刻は段階別JSONのUTC時刻を日本時間へ変換したもの。各APIの厳密な障害継続時間・復旧時間や性能指標を測定したものではない。

## 再現手順の要点

初回構築時のコードとアプリZIPは変更せず、次の変数だけを切り替えた。各planをJSONで確認してから、その保存planをapplyした。

```powershell
# 設定変更：Lambdaとロググループの2件だけを更新
terraform plan -var=memory_mb=256 -var=log_retention_days=14 -out=settings.tfplan
terraform apply settings.tfplan

# 訓練：Lambdaの環境変数だけを更新
terraform plan -var=memory_mb=256 -var=log_retention_days=14 -var=simulate_storage_failure=true -out=failure.tfplan
terraform apply failure.tfplan

# 復旧：訓練フラグだけをfalseへ戻す
terraform plan -var=memory_mb=256 -var=log_retention_days=14 -out=recovery.tfplan
terraform apply recovery.tfplan

# データと状態を退避し、復旧の確認後に実施
terraform plan -destroy -var=memory_mb=256 -var=log_retention_days=14 -out=destroy.tfplan
terraform apply destroy.tfplan

# 元の低コスト設定で再構築
terraform plan -out=rebuild.tfplan
terraform apply rebuild.tfplan
terraform plan -detailed-exitcode
```

共通HTTP検証は `scripts/verify_lifecycle.py` を使用。backup → preserved → failure → logs → restored → rebuildの順。対象アカウントとリソース名はこの検証環境に固定している。backupは既知の1記事以外があれば停止し、既存退避ファイルを上書きしない。検証フェーズは勝手に再試行しない。

## データ・URL・ログの扱い

テーブル削除により元の記事IDと作成日時は失われる。再投入は記事のタイトル・本文を再現するもので、元ID・元日時を保持したバックアップ復元ではない。

- 旧記事ID：`ae78201698d6437aab0a2ac8cfcfce8f`
- 再投入後ID：`84ce4f181a874a8985e7914f4cd3e29f`
- 記事数：最終1件
- Function URL：再作成で変更。現在値は `terraform output -raw function_url` で取得する
- 訓練時のロググループも削除したため、旧ログはAWS上には残っていない。削除前に原因ログの抜粋をローカルの段階別JSONへ保存した
- 権限境界の管理ポリシー、SSOのアクセス許可セットは削除対象外

## 最終状態と評価の限界

環境はAWS上に残している。メモリ128MB、タイムアウト10秒、ログ保持7日、DynamoDBオンデマンド、訓練フラグfalse、Function URLはAWS_IAM。最終planは差分なし。状態ファイルは再構築後のコピーも作業フォルダーへ退避済み。

この検証で示せるのは、個人環境でのIaCによる変更、データ保持の確認、意図的なエラーのログ調査と設定復旧、環境の削除再構築である。実際のAWSサービス障害からの復旧、性能改善の効果、同時負荷、本番運用の経験や復旧時間保証を実証したものではない。請求額の実測、GitHub Actions上での実行、GitHub公開、CloudFormation版・CDK版は未実施。
