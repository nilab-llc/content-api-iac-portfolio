# AWS CDK版：AWS事前照合

実施日：2026-10-28（日本時間）。読み取り・検証APIだけを実行。権限追加、Change Set準備、実リソース作成、記事登録は行っていない。

| 項目 | 確認結果 |
|---|---|
| 認証 | 既存nilab-readonlyが有効。再ログイン不要 |
| アカウント | 364561592630、一致 |
| 現行SSOインライン | 30 Statement、保存済みTerraform＋CloudFormationの統合JSONと完全一致 |
| 管理ポリシー | ReadOnlyAccessを維持 |
| スタックnilab-content-cdk | DescribeStacksで存在しないことを確認 |
| Lambda nilab-content-cdk | ResourceNotFoundException |
| DynamoDB nilab-content-cdk | ResourceNotFoundException |
| 実行ロールnilab-content-cdk-runtime | NoSuchEntity |
| ログ/aws/lambda/nilab-content-cdk | 前方一致検索で空配列 |
| 境界nilab-content-cdk-runtime-boundary | NoSuchEntity |
| 境界案のAccess Analyzer ValidatePolicy | findings=[] |
| CDK追加案のAccess Analyzer ValidatePolicy | findings=[] |
| SSO統合候補のAccess Analyzer ValidatePolicy | findings=[] |
| CDK生成テンプレートのAWS ValidateTemplate | 成功。Parameters=[]、CAPABILITY_NAMED_IAMが必要 |

現行SSOが統合候補の生成元と一致したため、既存2方式を保持した更新案としてレビュー可能。統合後は同じ条件・操作のStatementをまとめるため、現行JSONと見た目・Sid・Statement数は異なる。ローカル試験でEffect/Action/Resource/Conditionの全組が「現行権限＋CDK追加分」と一致することを確認済み。境界と実行ロールの対応を維持し、空白除外7,569文字で上限内。

次の変更候補は2件：管理者が境界nilab-content-cdk-runtime-boundaryを新規作成し、SSOアクセス許可セットnilabのインラインをpermissions/cdk/sso-inline-merged-proposal.jsonへ更新して対象アカウントへ反映する。ブラウザ操作はユーザー。ReadOnlyAccessと既存2方式の境界は保持する。

権限追加の承認・反映後に、AWS内容との一致を確認し、CDK生成テンプレートによる6件AddのCREATE Change Setを準備する。実リソースの構築は具体的なChange Setをレビューして別途承認後に行う。Access Analyzerの指摘なしとValidateTemplate成功は、すべての構築・更新・削除権限やAPI動作の保証ではない。

生記録は公開成果物外のwork/cdk-preflight-current-sso.json、work/cdk-validated-*.json、work/cdk-template-validation.jsonへ保存。認証情報は出力・転記していない。

## 2026-10-29：コマンドによる権限追加の可否確認

ユーザーの「コマンドで可能な処理はエージェントが実行し、不可能な処理だけ手動」方針に従い再確認。権限追加2件は承認済み。

- 既存SSO認証が有効で、対象アカウント364561592630と一致。
- AWS CLIの既存プロファイルはnilab-readonlyのみ。
- 境界nilab-content-cdk-runtime-boundaryはGetPolicyでNoSuchEntity、未作成。
- IAM SimulatePrincipalPolicyで対象の境界ARNを明示したiam:CreatePolicyがimplicitDeny。
- sso:PutInlinePolicyToPermissionSet / sso:ProvisionPermissionSetもResource=*でのシミュレーションはimplicitDeny。現行の既存2方式のインラインにはこれらの管理操作を付与しておらず、別の管理用CLIプロファイルもない。
- 現行SSOインラインは、統合案生成元の既存2方式JSONと引き続き完全一致。

したがって境界の新規作成とSSO統合案の反映だけは、権限を持つユーザーのコンソール操作が必要。操作方法だけを理由に手動へ回したのではなく、現在利用できるCLI認証の権限制限によるもの。エージェント自身に追加の管理者権限を与える対応は行わない。手動反映後の内容照合と以降の承認済み工程はコマンドで実施する。

## 2026-10-29：権限反映と初回Change Set

ユーザーの手動反映完了後、CLIで以下を確認した。

- 境界nilab-content-cdk-runtime-boundaryの既定バージョンv1が、承認済みJSONと完全一致。
- SSOインラインが3方式の統合候補と完全一致。既存ReadOnlyAccessも維持。
- CDK生成テンプレートによるCREATE Change Set nilab-content-cdk-create-001を準備。
- 状態CREATE_COMPLETE、実行状態AVAILABLE。実行ロールの指定なし。
- 差分はApiFunction / ApiLogs3D05D88B / Articles47CFF050 / FunctionUrl / RuntimePolicy / RuntimeRoleFD8790A4の6件Addだけ。

Change Set準備によりスタックの管理レコードは存在するが、ExecuteChangeSetは未実行で、APIの6リソースはまだ作成していない。次はこの具体的なChange Setの実行と初回API確認について承認を得る。
