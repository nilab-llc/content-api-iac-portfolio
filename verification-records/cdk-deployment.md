# AWS CDK版：初回構築とAPI確認

実施日：2026-10-29（日本時間）。ユーザー承認の範囲で、東京のnilab-content-cdkへCDK生成テンプレートをAWS CLIのChange Setで反映した。cdk deploy / bootstrapを実行した実績ではない。

| 確認 | 結果 |
|---|---|
| 実行前 | CREATE Change Set nilab-content-cdk-create-001が6件Addだけ、対象アカウント・東京・サービスロール指定なしを再確認 |
| スタック | CREATE_COMPLETE |
| 6リソース | Lambda、ログ、DynamoDB、URL、実行ポリシー、実行ロールがすべてCREATE_COMPLETE |
| 未認証health | 403 |
| 認証済みhealth | 200 |
| 記事登録 | 201、テスト記事1件を登録 |
| 記事取得 | 200、登録応答との全項目一致 |
| Lambda実設定 | Python3.13、index.handler、128MB、timeout10秒、対象テーブル、訓練falseを確認 |
| URL | AWS_IAM |
| ログ | 対象グループ、保持7日 |
| DynamoDB | PAY_PER_REQUEST |
| 実行ロール | 対象ロールと承認済み権限境界を確認 |
| テンプレート | AWSのGetTemplate応答とCDK生成template.jsonがJSONとして一致 |

API試験完了時刻：08:18:03 JST。記事ID：d572864839e848339ed59cc0a02f676f。共通scripts/verify_live.pyを1回実行し、再試行や追加記事登録は行っていない。

生記録は公開成果物外のwork/cdk-create-*.json、work/cdk-created-stack.json、work/cdk-created-resources.json、work/cdk-deployed-template.json、work/cdk-initial-live.jsonへ保存。認証情報は出力・転記していない。最初の構築進捗にはRuntimePolicyのEventual consistency check initiatedが表示され、その後正常完了した。

現在、CDK環境はAWS上に残している。Terraform・CloudFormation環境も保持。次の未実施工程は、256MB・ログ14日への変更と記事保持、訓練503・原因ログ確認・復旧、削除再構築と記事再投入、最終差分なし確認。GitHub公開・Actions実行と実際の請求額の確認も未実施。
