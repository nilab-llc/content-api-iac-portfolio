# AWS CDK版（初回構築・API確認済み）

PythonのAWS CDK v2で、東京のnilab-content-cdkを定義する自主制作。Terraform・CloudFormationの既存環境は保持する。共通アプリはapp/handler.py。2026-10-29に初回6件構築とAPI確認、設定変更・記事保持・訓練503・原因ログ確認・復旧、削除再構築・記事再投入まで成功。最終差分なし、128MB・ログ7日・訓練OFF。以下は再現用であり、現在の環境へ重ねてCREATEしない。結果はverification-records/cdk-deployment.mdとverification-records/cdk-lifecycle.md（リポジトリルート基準）を参照。

## 実装と反映方式

content_stack.pyのCDK Constructからテンプレートを生成する。テーブル・ロググループ・実行ロールはL2 Construct、権限とLambda・Function URLは明示的なL1 Constructを使用。6件構成と最小権限を維持し、暗黙の管理ポリシーや追加のログ保持用Lambdaを作らない。

共通PythonコードをZipFileへ埋め込む。CDKのAsset配布は使わない。LegacyStackSynthesizerを明示し、生成物にAsset manifest・BootstrapVersion・CDKMetadataリソースがないことを試験する。ローカル生成にはNode.jsが必要。DockerやAWSへの接続は不要。

反映は **CDKで生成したテンプレートをAWS CLIのCloudFormation Change Setへ渡す方式**。今回の実績にcdk deploy、cdk bootstrap、CDK用S3/ECRへの配布は含めない。CDKのプログラム定義・テンプレート生成と、CloudFormationによる実行を分けて説明する。app.py/cdk.jsonはCDK CLIの入口も用意しているが、CLI経由の実行は今回のローカル検証に含めない。

AWS CDK 2.274.0・constructs 10.8.1を固定。CIはPython3.13とNode24。LambdaのPython3.13、128MB、timeout10秒、ログ7日、障害訓練OFF、オンデマンドDynamoDB、AWS_IAMのFunction URLは他方式と同じ。

## ローカル確認

以下はリポジトリルートで実行する。PythonとNodeがPATHにある前提。標準SDKや認証情報のコピーは不要。

```powershell
python -m pip install -r requirements-cdk.txt -r requirements-cfn.txt
python scripts/synth_cdk.py
python scripts/synth_cdk.py --check
python scripts/build_cdk_permissions.py --check
python -m unittest discover -s tests -v
cfn-lint infra/cdk/template.json --regions ap-northeast-1
```

template.jsonは生成物。直接編集せず、CDK定義か共通アプリを直して再生成する。生成時に共通コード一致、ZIP4MiB上限、直接送信テンプレート51,200バイト上限、Asset不在を確認する。標準設定以外は明示した出力先へ書き、コミットする既定テンプレートを上書きしない。

```powershell
python scripts/synth_cdk.py --memory-mb 256 --log-retention-days 14 --output <非公開作業先>/cdk-settings.json
python scripts/synth_cdk.py --memory-mb 256 --log-retention-days 14 --simulate-storage-failure true --output <非公開作業先>/cdk-failure.json
```

CDK版は設定値を生成時に確定する。CloudFormation版のようなMemoryMb等のスタックパラメータは作らない。設定を変えるときはテンプレートを再生成する。

## AWS検証の計画（未実行）

1. 既存認証でアカウント364561592630と東京を照合。同名スタック・6リソース・権限境界の衝突を参照する。有効なSSOの再ログインは不要。
2. permissions/cdk/README.mdの権限案を現行SSOと照合し、Access Analyzerで検証。既存2方式の権限を保持した統合候補としてレビューし、承認後にユーザーがブラウザで反映する。
3. AWSのValidateTemplate後、nilab-content-cdkのCREATE Change Setを準備する。6件Addだけを確認して、実リソース作成の承認後に実行する。
4. OutputsのFunctionUrlOutputを取得し、共通verify_live.pyで未認証403・health200・記事登録201・取得200と全項目一致を確認する。記事登録は1回だけ。
5. 記事退避後、cdk-settings.jsonによるUPDATE Change Setを確認して実行。メモリとログ保持だけの変更、記事全項目一致を確認する。
6. cdk-failure.jsonで訓練フラグをONにし、記事503・health200・原因ログstorage_failure_drillを保存。cdk-settings.jsonに戻して記事200・全項目一致を確認する。
7. テンプレート・設定・記事・原因ログを非公開退避し、対象6件を確認して別途承認後にDeleteStack。既定template.jsonから再構築し、旧ID404・新テーブル空を確認してタイトル・本文を再登録する。
8. 最終APIと記事1件を確認。同じ既定テンプレートによるUPDATE Change Setの「変更なし」を確認し、128MB・ログ7日・訓練OFFへ戻す。

Lambdaの更新に伴うFunctionUrl.TargetFunctionArnのDynamic / ApiFunction.Arn参照によるConditional差分は、CloudFormation版で実測済み。CDK版でも実際のDetailsを確認する。Lambda置換やテーブル変更を無条件に許容しない。

```powershell
aws cloudformation create-change-set --stack-name nilab-content-cdk --change-set-name nilab-content-cdk-create-001 --change-set-type CREATE --template-body file://infra/cdk/template.json --capabilities CAPABILITY_NAMED_IAM --profile nilab-readonly --region ap-northeast-1
aws cloudformation describe-change-set --stack-name nilab-content-cdk --change-set-name nilab-content-cdk-create-001 --profile nilab-readonly --region ap-northeast-1
# レビュー・承認後、そのChange Set ARNだけを指定して実行する
aws cloudformation execute-change-set --change-set-name <レビュー済みARN> --profile nilab-readonly --region ap-northeast-1
python scripts/verify_live.py --url <OutputsのFunctionUrlOutput> --profile nilab-readonly --allow-create-test-article
```

Change Set名はnilab-content-cdk-で始める。CLI例は作成完了の待機とイベント確認を含めて運用し、CreateChangeSetの直後に無条件でExecuteしない。権限不足・想定外差分・作成失敗時は停止し、広い権限へ切り替えない。

共通の段階別確認は `python scripts/verify_lifecycle.py <phase> --target cdk --records <CDK専用の非公開退避先>`。phaseはbackup / preserved / failure / logs / restored / rebuild。Terraform・CloudFormationの退避先を混用しない。CDK検証ではTerraform状態をコピーしない。再投入はタイトル・本文の再登録であり、元ID・日時を保持するDB復元ではない。

再作成でURLは変わり得る。CloudFormation版では再作成直後に認証済みhealth403が1回発生し、構成を変えず時間経過後の1回再試行で解消した。CDK版で同じことが起きると決めつけず、設定・権限・記事未登録を確認してから判断する。自動再試行・自動追加登録は行わない。

## 公式仕様

- [PythonでのCDK](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [Stack synthesisの設定](https://docs.aws.amazon.com/cdk/v2/guide/configure-synth.html)
- [LegacyStackSynthesizer](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk/LegacyStackSynthesizer.html)
- [インラインLambdaコード](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-lambda-function-code.html)
