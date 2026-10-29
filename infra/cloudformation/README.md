# CloudFormation版（初回構築・API確認済み）

共通アプリを東京の `nilab-content-cfn` に配置する。Terraformの既存環境とは別名。自主制作の検証用で、商用経験として扱わない。2026-10-28に初回構築・API確認、設定変更・記事保持・訓練503・原因ログ確認・復旧、6件削除→同じコードから6件再構築・記事再投入まで成功。最終差分なし、128MB・ログ7日・訓練OFF。結果は `verification-records/cloudformation-deployment.md` と `verification-records/cloudformation-lifecycle.md`（リポジトリルート基準）を参照。以下は再現用であり、現在の環境へ重ねてCREATEしない。

## 構成と生成方法

`template.json` は `scripts/build_cloudformation.py` の生成物。直接編集せず、共通の `app/handler.py` または生成処理を変更して再生成する。JSONはCloudFormationの正式なテンプレート形式。YAML処理ライブラリは不要。

6リソース：DynamoDB、ロググループ、Lambda実行ロール、ロールのインラインポリシー、Python 3.13 Lambda、AWS_IAMのFunction URL。既定値は128MB・10秒・ログ7日・障害訓練OFF。対象アカウントと東京リージョンはRulesで検証し、リソース名は固定する。

CloudFormationのインラインコードは `index.py` に格納されるため `index.handler` を使う。生成時にPython構文、圧縮ZIPの4MiB上限、直接送信テンプレートの51,200バイト上限を確認する。本文にFn::Subを使わず、共通アプリを文字列としてそのまま埋め込む。S3、SAM、Dockerは不要。Lambda付属boto3を使う点はTerraformと同じ。

Lambdaはロググループとインラインポリシーの作成後に作成する。削除時は逆順。権限境界 `nilab-content-cfn-runtime-boundary` は事前に別管理で作成し、スタックの削除対象にしない。専用CloudFormationサービスロールを指定せず、呼び出し元の限定権限で操作する。Lambdaの実行ロールとは別の概念である。

## ローカル確認（リポジトリルート）

```powershell
python -m pip install -r requirements-cfn.txt
python scripts/build_cloudformation.py
python scripts/build_cloudformation.py --check
python -m unittest discover -s tests -v
cfn-lint infra/cloudformation/template.json --regions ap-northeast-1
```

CIにも生成物一致確認とcfn-lintを追加。CIはデプロイしない。ローカル試験は実際のIAM認証や作成権限を証明しない。

## AWS作業前のレビュー

初回は以下のレビュー後、ユーザー承認を得て権限追加と構築を実施済み。再実施や追加変更は対象範囲を確認してから行う。`permissions/cloudformation/README.md` の対象・制限・JSONを確認する。既存認証が有効なら再ログインしない。現在のTerraform状態ファイルは元フォルダーに保持し、このコピーからTerraformをapplyしない。

アカウント364561592630、東京、同名スタック・リソースの未使用、境界の内容、SSO権限の反映を確認してから進める。衝突した既存リソースを削除・取り込みしない。CLI例はAWS CLIがPATHにある前提。Windowsの実体は `C:/Program Files/Amazon/AWSCLIV2/aws.exe`。

```powershell
aws sts get-caller-identity --profile nilab-readonly
aws cloudformation validate-template --template-body file://infra/cloudformation/template.json --profile nilab-readonly --region ap-northeast-1

# 初回はCREATE。これは差分準備であり、リソース構築はまだ行わない。
aws cloudformation create-change-set --stack-name nilab-content-cfn --change-set-name nilab-content-cfn-create-001 --change-set-type CREATE --template-body file://infra/cloudformation/template.json --parameters file://infra/cloudformation/parameters/default.json --capabilities CAPABILITY_NAMED_IAM --profile nilab-readonly --region ap-northeast-1
aws cloudformation wait change-set-create-complete --stack-name nilab-content-cfn --change-set-name nilab-content-cfn-create-001 --profile nilab-readonly --region ap-northeast-1
aws cloudformation describe-change-set --stack-name nilab-content-cfn --change-set-name nilab-content-cfn-create-001 --profile nilab-readonly --region ap-northeast-1
```

期待値は上記6論理リソースのAddだけ。Change Set作成時にリソースなしのスタックが作られることがある。IAM変更の承認フラグは権限自体を付与するものではない。権限、費用、差分をレビュー後、そのChange SetのARNを保存して指定実行する。

```powershell
aws cloudformation execute-change-set --change-set-name <レビューしたChangeSetのARN> --profile nilab-readonly --region ap-northeast-1
aws cloudformation wait stack-create-complete --stack-name nilab-content-cfn --profile nilab-readonly --region ap-northeast-1
aws cloudformation describe-stacks --stack-name nilab-content-cfn --profile nilab-readonly --region ap-northeast-1
python scripts/verify_live.py --url <OutputsのFunctionUrl> --profile nilab-readonly --allow-create-test-article
```

未認証403、認証済みhealth200、記事登録201、取得200と全項目一致を記録する。記事登録は1回だけ。失敗時は自動再試行せず原因を確認する。

## 変更・復旧・再構築の検証計画

段階ごとに新しいChange Set名を使い、UPDATEのChange Setを作成・確認してからそのARNを実行する。テンプレートは同じ、parametersだけ切り替える。`work/cfn-lifecycle-records/` は公開成果物の外の退避先例。各フェーズの記録は上書きしない。

| 順序 | パラメータファイル | 期待差分・確認 |
|---|---|---|
| 事前退避 | default.json | 既知の1記事だけであることを確認、APIとDB全項目一致、記事を非公開退避 |
| 設定変更 | settings.json | Lambda128→256MB、ログ7→14日。2件Modify、置換なし。記事全項目一致 |
| 訓練 | failure.json | Lambdaのフラグfalse→trueだけ。記事GET503、health200、未認証403 |
| 原因確認 | 同上 | CloudWatchのstorage_failure_drillと訓練時刻を照合 |
| 復旧 | settings.json | Lambdaのフラグtrue→falseだけ。記事GET200・全項目一致 |
| 削除 | ― | 退避と復旧を確認し別途承認後、対象スタックだけDeleteStack |
| 再構築 | default.json | 同じ生成済みテンプレートでCREATE。旧ID404、新テーブル空、退避したタイトル・本文を再登録 |
| 最終確認 | default.json | 128MB・ログ7日・訓練OFF、API成功、同一テンプレートのUPDATEに変更なし |

```powershell
python scripts/verify_lifecycle.py backup --target cloudformation --records <非公開退避先>
# 各変更実行後に、該当フェーズを1回ずつ実行する
python scripts/verify_lifecycle.py preserved --target cloudformation --records <同じ退避先>
python scripts/verify_lifecycle.py failure --target cloudformation --records <同じ退避先>
python scripts/verify_lifecycle.py logs --target cloudformation --records <同じ退避先>
python scripts/verify_lifecycle.py restored --target cloudformation --records <同じ退避先>
python scripts/verify_lifecycle.py rebuild --target cloudformation --records <同じ退避先>
```

CloudFormation検証ではTerraform状態をコピーしない。スタックのテンプレート、パラメータ、Outputs、Change Set、イベントも各段階で非公開保存する。APIのURLは再作成で変わるため都度取得する。再投入は元ID・日時を保持したDB復元ではない。

CloudFormationは削除用Change Setを提供しないため、DeleteStack前にリソース一覧6件と退避を確認する。テンプレートのDelete設定により記事・ログも消える。削除の失敗やロールバック停止はイベントを調べ、勝手に境界・権限を広げない。

実測上、Lambdaを更新するとFunctionUrlのTargetFunctionArnがApiFunction.ArnのDynamicな参照再評価によりConditionalの変更として併記された。設定変更は2件だけと決めつけずDetailsを確認する。追加承認後、既知の参照由来の差分だけを許容して実行し、設定変更・訓練・復旧の3回ともURLと物理IDが保持された。テーブル変更やLambdaの置換は許容していない。

最終の変更なし確認はChange SetがFAILEDとなり「変更なし」の理由を返す場合がある。それ以外のFAILEDを正常扱いしない。これはテンプレート差分の確認であり、全リソースのドリフト検証ではない。費用はLambda・DynamoDB・Logsの利用と保持に応じる。Terraformと並存する分も課金対象。実際の請求額は未確認。

## 公式仕様

- [インラインコード・index.handler・4MB上限](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-lambda-function-code.html)
- [CreateChangeSet・TemplateBody上限・サービスロール省略時](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateChangeSet.html)
- [Function URLのIAM認証](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html)
