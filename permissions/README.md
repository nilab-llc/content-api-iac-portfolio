# AWS権限の設定記録

2026-10-28。既存SSOのReadOnlyAccessを維持し、Terraform版の構築・変更・削除・動作試験に必要な追加権限を設定済み。ユーザーがブラウザで反映した2件の内容は、CLIから準備したJSONとの完全一致を確認。その後、承認済みの6リソースを作成し、API動作試験も成功した。設定手順は再現用に残す。

## 対象

- アカウント: `364561592630`
- 東京リージョン: `ap-northeast-1`
- Lambda / DynamoDB: `nilab-content-tf`
- ログ: `/aws/lambda/nilab-content-tf`
- Lambda実行ロール: `nilab-content-tf-runtime`
- 権限上限ポリシー: `nilab-content-tf-runtime-boundary`

この案はTerraform版だけを対象とする。name変数を変更すると権限と一致しなくなる。CloudFormation版・CDK版の権限、SSO設定の編集、他リソースの変更、APIの公開化、直接のDynamoDBデータ操作は追加しない。

既存ReadOnlyAccessには他サービスの参照権限も含まれる。この追加案で書き込み先を限定しても、アカウント全体の参照範囲が狭くなるわけではない。

## ファイル

| ファイル | 設定先 | 効果 |
|---|---|---|
| `runtime-boundary.json` | IAMのカスタマー管理ポリシーとして作成し、Lambda実行ロールの権限境界に指定 | Lambdaの権限上限を対象テーブルのGetItem/PutItemと対象ログへの出力に限定 |
| `deploy-and-verify-inline.json` | IAM Identity Centerの既存アクセス許可セット `nilab` のインラインポリシー | 対象リソースの構築・変更・削除と、IAM認証付きURLからのAPI試験を許可 |

後者には削除操作も含むが、付与しただけで削除は実行されない。API試験では記事を書き込むため料金が発生し得る。ReadOnlyAccessは残し、AdministratorAccess等は追加しない。

## ロールの権限上限を用意する理由

IAMロールのポリシー編集を許可すると、ロール名だけを限定しても、そこに強い権限を付けられる余地が残る。この案では管理者が先に境界ポリシーを作り、構築担当にはその定義の変更・取り外しを許可しない。ロール新規作成も境界付きに限定する。PassRoleは対象ロールをLambdaに渡す場合だけ許可する。

境界ポリシーそのものは権限を付与せず、実行ロールのインラインポリシーとの共通範囲が有効になる。Terraform側の必須変更は次の1行。2026-10-28にAWS上のポリシーと準備したJSONの完全一致を確認後、既存main.tfに追加した。

```hcl
resource "aws_iam_role" "api" {
  # 既存のname・assume_role_policyはそのまま
  permissions_boundary = "arn:aws:iam::364561592630:policy/nilab-content-tf-runtime-boundary"
}
```

この行は既存ロール定義に追加済み。別の重複リソース定義を作らない。境界を外す変更や、実行ロールの信頼ポリシーを変更する操作は今回の追加権限では許可しない。

## ユーザーがブラウザで設定する順序

1. 管理者用AWSコンソールのアカウントIDを確認し、IAM → ポリシー → ポリシーを作成 → JSONで `runtime-boundary.json` を設定。名前を **nilab-content-tf-runtime-boundary** にして作成する。これはLambda実行ロール用の境界であり、SSOアクセス許可セットの境界には設定しない。
2. IAM Identity Center → アクセス許可セット → **nilab** → インラインポリシーで `deploy-and-verify-inline.json` を設定する。既存インラインポリシーがある場合は上書きせず止めて確認する。以前のCLI確認ではAWS上のロールのインラインポリシーは0件だったが、編集時点で再確認する。
3. `nilab` のReadOnlyAccessが残っていることを確認し、対象アカウントへプロビジョニングする。反映状態を確認する。
4. 設定後にCLIのSSOログインを更新する。ブラウザ認証はユーザーが行う。
5. CLIから境界の内容、SSOロールの権限、同名リソースの有無を読み取りで確認する。同名のロールやAWSリソースが既にある場合は、勝手に取り込んだり削除したりしない。境界のない既存ロールにはこの権限でポリシーを追加できない。
6. Terraformの上記1行を追加・検証し、実環境のplanを取得。予定する作成・変更・費用を確認する。applyはその後の別工程。

上記の権限設定と初回構築は実施済み。再設定の際は既存の内容を確認し、重複作成や上書きを行わない。

## 検証状況と限界

JSONの構文、インラインポリシーのサイズ、書き込み先のARN制限、アクション名にサービス全体のワイルドカードがないことをローカルで確認した。ログARN末尾の `:*` はこのロググループ内のストリーム等を表し、全ログを許可する指定ではない。

AWS Access AnalyzerのValidatePolicyでは構築用ポリシーに指摘なし（findings=[]）。初回applyとIAM認証付きAPI試験は成功し、作成後のplanも差分ゼロ。更新・destroyは未検証。今後、不足権限が判明する場合は、エラーのAPIと対象ARNを確認して限定的に見直す。権限不足の都度、広い権限へ自動的に変更しない。ロールの権限上限ポリシーはTerraformサービス本体の削除対象外で、管理者が作成・管理する。

公式根拠:

- [IAM permissions boundaries](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html)
- [PassRoleの対象ロール制限](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html)
- [Function URLのAWS_IAM認証・2種類の呼び出し権限](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)
