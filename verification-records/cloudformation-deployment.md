# CloudFormation版：初回構築とAPI確認

実施日：2026-10-28（日本時間）。対象アカウント364561592630、東京リージョンのnilab-content-cfn。ユーザーが承認した初回構築とAPI試験のみ実行した。設定変更、障害訓練、削除再構築はこの時点では未実施。

## 実施結果

| 項目 | 結果 |
|---|---|
| 実行前レビュー | Change Set nilab-content-cfn-create-001。6件Addのみ、128MB・ログ7日・訓練false、CloudFormationサービスロール指定なしを再確認 |
| スタック | CREATE_COMPLETE |
| リソース | ApiFunction、ApiLogs、Articles、FunctionUrl、RuntimePolicy、RuntimeRoleの全6件がCREATE_COMPLETE |
| 認証なし | GET /healthは403 |
| 認証あり | GET /healthは200 |
| 記事登録 | POST /articlesは201。テスト記事を1件登録 |
| 記事取得 | GET /articles/{id}は200、登録応答と全項目一致 |
| 実設定 | Python3.13、index.handler、128MB、timeout10秒、訓練false、対象テーブル名が一致 |
| URL | AWS_IAMを確認 |
| ロール | 対象のLambda実行ロールと外部管理の権限境界を確認 |
| ログ | 対象グループ、保持7日を確認 |
| テーブル | PAY_PER_REQUESTを確認 |
| テンプレート | GetTemplateで取得した内容とローカルtemplate.jsonがJSONとして一致 |

API試験完了時刻：17:57:23 JST。登録記事ID：6d858798e0374b579427f97bc0d8115c。共通のscripts/verify_live.pyを1回実行し、自動再試行や追加登録は行っていない。

## 記録と残存環境

APIの結果、現行URL、作成済みスタックとリソース一覧、AWS上のテンプレート、Change Setと実行要求の生記録はプロジェクト外のwork/cfn-*.jsonへ保存した。認証情報は出力・転記していない。

環境はAWS上に残している。Terraform環境も保持しており、今回のChange SetにTerraformリソースの変更は含まれない。実際の請求額は未確認。Lambda・DynamoDB・Logsの利用とデータ保持に応じた課金対象となる。

次の未実施工程は、メモリ256MB・ログ14日への設定変更と記事保持、訓練フラグによる503・原因ログ・復旧、退避後の削除再構築と記事再投入。最終的なテンプレート差分なし確認、CDK版、GitHub公開・Actions実行も残る。今回のテンプレート一致は全リソースのドリフト検証を意味しない。
