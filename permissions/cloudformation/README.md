# CloudFormation用権限（AWS反映・内容照合済み）

2026-10-28。反映前の現行SSOインラインは保存済みTerraform版の13 Statementと完全一致。3件のJSONをIAM Access Analyzerで検証し、すべてfindings=[]。ユーザー承認後に境界と統合済みSSOインラインを反映し、AWS内容との完全一致、ReadOnlyAccess維持、初回構築・設定変更・削除・再構築を確認済み。全アクションの網羅的な権限試験ではない。詳細は `verification-records/cloudformation-aws-preflight.md`、`verification-records/cloudformation-deployment.md`、`verification-records/cloudformation-lifecycle.md` を参照（リポジトリルート基準）。

## レビュー対象

| ファイル | 用途 |
|---|---|
| runtime-boundary.json | 管理者が `nilab-content-cfn-runtime-boundary` として作成するLambdaの権限上限 |
| deploy-and-verify-additions.json | CloudFormation版だけの追加分。現行SSOインライン全体の置換には使わない |
| sso-inline-merged-proposal.json | 保存済みTerraform版の全Statementを保持し、CloudFormation分を追加した統合候補 |

既存ReadOnlyAccessを前提とする。参照権限の範囲はその既存ポリシーに従う。新しい書き込み先は `nilab-content-cfn` のLambda、DynamoDB、ロググループ、`nilab-content-cfn-runtime` ロール、同名スタックだけ。Change Set名は `nilab-content-cfn-` で始める。

Lambdaロールは境界付きでのみ作成可能。インラインポリシー編集も境界を条件とし、PassRoleはそのロールをLambdaへ渡す場合だけ。境界の取り外し・書換えは明示Deny。境界自体の新規作成権限やSSOポリシー編集権限は作業用SSOへ付与しない。信頼ポリシー変更や管理ポリシーのアタッチも含めない。

Function URLの作成・更新はAWS_IAMに限定。呼び出しはInvokeFunctionUrlと、URL経由に限定したInvokeFunctionの2種類を許可する。公開用のLambdaリソースポリシー追加は含めない。

CloudFormationはChange Setの作成・参照・実行・削除と、対象スタックの削除・ロールバック継続を許可する。直接のCreateStack/UpdateStackは含めずChange Set手順を使う。CreateChangeSetではRoleARNを指定しない条件を付け、専用サービスロールの利用を認めない。Lambda実行ロールは引き続き必要。

ValidateTemplateはリソース単位の制限ができないためResourceが `*`。これはテンプレート検証だけで、全リソースへの書き込み許可ではない。スタックARNとChange Set ARN内の `*` はAWSが生成するID部分。

## 反映前の手順（別途承認後）

1. CLIの既存認証で接続を確認し、アカウントと対象を照合する。期限切れの場合のみSSOログインする。
2. AWS上のSSOインラインポリシーと保存済みTerraform版を比較する。差分があれば統合候補で上書きせず停止し、最新内容を保持した案へ作り直す。
3. Access Analyzerで追加案・境界・統合候補を検証し、指摘を確認する。ローカル構文検査はこの代用にならない。
4. 承認後、ユーザーがブラウザで境界ポリシーを作成し、SSOアクセス許可セットnilabのインラインへ統合内容を反映する。ReadOnlyAccessとTerraformの全Statementを保持する。
5. 対象アカウントへのプロビジョニングを確認し、CLIで境界と有効ポリシーの内容を照合する。認証が有効なら再ログイン不要。反映待ち・認証期限切れ等が必要な場合だけ更新する。
6. 同名スタック・リソースの未使用を確認し、ValidateTemplateとCREATE Change Setを作成する。6件Addだけであることを確認後、実リソース作成の承認を得る。

このJSONを保存しただけでは権限は変わらない。実環境で不足権限が見つかったらイベントを確認して対象限定の修正案を作り、広い管理者権限へ切り替えない。スタック削除後も境界とSSO権限は残るため、3方式完成後の整理対象として記録する。
