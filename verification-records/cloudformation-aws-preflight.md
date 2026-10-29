# CloudFormation版：AWS事前照合

実施日：2026-10-28（日本時間）。読み取りと検証APIのみ実行。権限追加・スタック作成・アプリデータ書き込みは行っていない。

| 確認 | 実結果 |
|---|---|
| 認証 | 既存nilab-readonlyプロファイルが有効。再ログイン不要 |
| アカウント | 364561592630、一致 |
| SSOの管理ポリシー | ReadOnlyAccessを確認 |
| SSOインライン | AwsSSOInlinePolicyの13 Statementが保存済みTerraform版JSONと一致 |
| スタックnilab-content-cfn | DescribeStacksで存在しないことを確認 |
| Lambda nilab-content-cfn | GetFunctionConfigurationでResourceNotFoundException |
| DynamoDB nilab-content-cfn | DescribeTableでResourceNotFoundException |
| 実行ロールnilab-content-cfn-runtime | GetRoleでNoSuchEntity |
| ロググループ | /aws/lambda/nilab-content-cfnの前方一致検索で空配列 |
| 境界nilab-content-cfn-runtime-boundary | GetPolicyでNoSuchEntity |
| 境界案のValidatePolicy | findings=[] |
| CloudFormation追加権限案のValidatePolicy | findings=[] |
| SSO統合候補のValidatePolicy | findings=[] |
| AWS CloudFormation ValidateTemplate | 成功。3パラメータの既定値128 / 7 / false、CAPABILITY_NAMED_IAMが必要との応答 |

現行SSOインラインとの一致を確認したため、統合候補は既存Terraform権限を保持した追記案としてレビュー可能。反映前に別の変更が入った場合は再照合が必要。

次の変更候補は2件：管理者が境界ポリシーを新規作成し、既存アクセス許可セットnilabのインラインを統合候補に更新してプロビジョニングする。ブラウザ操作はユーザー。既存ReadOnlyAccessとTerraform境界は維持する。

Access Analyzerの指摘なしやValidateTemplateの成功は、権限がすでに付与されたこと、Change Setが作成できること、Lambdaが動作することの証明ではない。権限反映後のAWS内容照合とChange Set確認が必要。リソース構築・削除・再構築は別途承認後の工程。

## 権限反映後の照合・初回Change Set準備

同日、ユーザーが承認した2件の権限変更をブラウザで実施。その後CLIで以下を確認した。

- 境界nilab-content-cfn-runtime-boundaryが存在し、既定バージョンv1の内容が承認済みJSONと完全一致。
- SSOロールのインラインが統合済みJSONの30 Statementと完全一致。既存ReadOnlyAccessも維持。
- CREATE Change Set `nilab-content-cfn-create-001` を準備。状態CREATE_COMPLETE、実行状態AVAILABLE。ExecuteChangeSetは未実行。
- 差分はApiFunction / ApiLogs / Articles / FunctionUrl / RuntimePolicy / RuntimeRoleの6件Addのみ。既存Terraformリソースへの変更なし。
- パラメータ128MB、ログ7日、訓練falseを確認。

Change Set作成に伴ってCloudFormationスタックの管理用レコードが存在するが、APIの6リソースはまだ構築していない。次はこのレビュー済みChange Setの実行と初回API確認について承認を得る。
