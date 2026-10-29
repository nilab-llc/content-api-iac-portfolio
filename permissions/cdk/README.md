# CDK用権限（AWS反映・内容照合済み）

2026-10-28、権限案3件のAccess Analyzerはすべてfindings=[]、生成テンプレートのValidateTemplateも成功。2026-10-29、ユーザーが承認済みの境界作成とSSO更新を実施後、AWS内容とJSONの完全一致、ReadOnlyAccess維持をCLIで確認。初回構築・認証・記事登録取得に続き、設定変更・障害訓練と復旧・削除再構築も確認済み。全アクションの網羅的な権限試験ではない。詳細はverification-records/cdk-aws-preflight.md、verification-records/cdk-deployment.md、verification-records/cdk-lifecycle.md（リポジトリルート基準）を参照。

対象はアカウント364561592630・東京のnilab-content-cdk、実行ロールnilab-content-cdk-runtime、ログ/aws/lambda/nilab-content-cdk、スタックnilab-content-cdk。Change Set名はnilab-content-cdk-で始める。既存ReadOnlyAccessを維持する。

| ファイル | 用途 |
|---|---|
| runtime-boundary.json | 管理者がnilab-content-cdk-runtime-boundaryとして新規作成するLambda実行ロールの権限上限 |
| deploy-and-verify-additions.json | CDK版だけの追加分。現在のSSOインライン全体の置換には使わない |
| sso-inline-merged-proposal.json | Terraform・CloudFormation・CDKの3方式を含む統合候補 |

CDK版のAWS操作は生成したテンプレートをCloudFormationで反映するため、CloudFormation版と同じ操作種別を別名に限定して使う。cdk bootstrap、S3/ECR配布、専用デプロイロール、SSO設定のCLI編集は許可しない。

## 既存権限の保持とサイズ

3方式を単純追記する代わりに、Effect・Action・Conditionが同一のStatementだけをまとめ、Resourceを限定ARNの配列にする。境界条件が異なるStatementはまとめない。例として、Terraformロール作成にCDKの境界を付けてよい、という権限は作らない。

Sidは識別用に再採番するため、現行JSONの見た目やStatement数は変わる。scripts/build_cdk_permissions.pyとテストで、全Effect・Action・Resource・Conditionの組を展開し、統合後が「保存済みの既存2方式の権限＋CDK追加分」と厳密に等しいことを確認する。AllowだけでなくDenyと条件も保持する。空白除外10,240文字・全体32,768バイトの上限も検査する。

境界付きのロール作成、境界の取り外し・定義変更のDeny、LambdaだけへのPassRole、AWS_IAMのURL作成、URL経由限定呼び出し、サービスロールを指定しないChange Set操作の条件は維持する。ValidateTemplateのResource=*はリソース単位で制限できない検証APIに限定する。

生成時の既存権限スナップショットはpermissions/cloudformation/sso-inline-merged-proposal.json。反映前にAWSの現行インラインとこのスナップショットの一致を確認し、違っていれば上書きせず最新内容を保持した案を作り直す。

## 反映手順（別途承認後）

1. CLIで認証・対象・現在のSSOインラインを読み取り、保存済み既存2方式のJSONと一致を確認。
2. 3つの権限案をAWS Access Analyzerで検証し、指摘をレビュー。2026-10-28に3件すべてfindings=[]を確認済み。案を変更した場合は再検証する。
3. 対象と内容の承認後、ユーザーがブラウザで境界ポリシーを新規作成。次にアクセス許可セットnilabのインラインを統合候補に更新し、対象アカウントへプロビジョニング。ReadOnlyAccessは残す。
4. CLIで境界・統合ポリシー・ReadOnlyAccessの一致を確認。有効な認証を無条件で再ログインしない。
5. 同名リソースの衝突確認、ValidateTemplate、6件AddのChange Setをレビュー後、実リソース作成は別途承認を得る。

Access Analyzerの指摘なしも実環境の全操作権限を保証しない。権限不足時は対象限定の修正案をレビューし、AdministratorAccessへ切り替えない。削除再構築では境界とSSO権限は残り、3方式完成後の整理対象となる。
