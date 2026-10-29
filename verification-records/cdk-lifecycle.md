# AWS CDK版：設定変更・障害訓練と復旧

実施日：2026-10-29（日本時間）。ユーザー承認の範囲で、東京のnilab-content-cdkだけを操作した。設定変更・復旧後、別途承認を得て削除再構築・記事再投入・最終差分なし確認まで完了。CDKのPython定義から生成したテンプレートをAWS CLIのChange Setで反映した。

| 検証 | 実結果 |
|---|---|
| 事前退避 | 既知のテスト記事1件だけであることを確認。強い整合性のDB読み取りとHTTP応答の全項目一致を確認して非公開退避 |
| テンプレート生成 | CDKから256MB・ログ14日、同設定で訓練ONの2種類を生成。両方cfn-lintで指摘なし。既定template.jsonは上書きしていない |
| 設定変更 | メモリ128→256MB、ログ7→14日。テンプレート全体の差分とAWS Change Setを確認して実行。UPDATE_COMPLETE |
| 記事保持 | GET200、ID・作成日時・タイトル・本文が退避データと全項目一致 |
| 障害訓練 | Lambda環境変数のSIMULATE_STORAGE_FAILURE false→trueだけを変更。記事GET503、health200、未認証403 |
| 原因確認 | CloudWatch LogsのRuntimeError: storage_failure_drillを確認して保存 |
| 復旧 | 訓練falseの設定変更用テンプレートへ戻すChange Setを確認して実行。UPDATE_COMPLETE、記事GET200、全項目一致 |
| URL・物理ID | 3回の更新すべてでURLとAWS_IAMを保持。復旧後の6物理IDも初回作成時と全件一致 |
| 削除前の再照合 | 現在の記事と退避が全項目一致。現在のAWSテンプレートがCDKの復旧用テンプレートと一致。対象6件・テンプレート・設定・記事を非公開保存 |

Lambda更新に伴いFunctionUrl.TargetFunctionArnがDynamic / ResourceAttribute / ApiFunction.Arn / Conditionalとして併記された。既知の参照再評価だけを許容し、Lambda自体はReplacement=False。他のプロパティ変更・テーブル変更・IAM変更は許容していない。変更前の配備テンプレートも各段階の生成元と一致を確認した。

## 確認時刻（JST）

- 08:27:38：事前退避
- 08:28:44：設定変更後の記事保持
- 08:29:32：訓練503
- 08:29:39：原因ログ保存
- 08:30:13：復旧後の記事200・全項目一致
- 08:30:44：削除前の退避と対象の再照合

時刻は各JSONのUTCを変換したもの。厳密な障害時間・復旧時間や性能の計測ではない。503はアプリの訓練フラグによるもので、AWS障害の実証ではない。

## 現在の状態と残作業

削除前は256MB、timeout10秒、ログ14日、訓練OFF、AWS_IAM、DynamoDBオンデマンド、記事1件だった。再構築後の最終状態は128MB・ログ7日・訓練OFF、記事1件。環境はAWS上に残す。Terraform・CloudFormationの既存環境は保持。

記事と段階別結果・原因ログは公開成果物外のwork/cdk-lifecycle-records、Change Set・スタック・テンプレート・削除対象一覧はwork/cdk-stack-records、設定変更用と訓練用のCDK生成テンプレートはwork/cdk-templatesへ保存。公開しない。

対象6件とデータ消失の影響を提示してGO承認後、削除・再構築を実施した。境界ポリシーとSSO権限は削除対象外。記事・原因ログ・テンプレートは退避済み。テーブル削除で元IDと作成日時、ロググループ削除でAWS上の旧ログは失われた。タイトルと本文を共通APIから登録し直す方式で、元ID・日時を保つDB復元ではない。

GitHub公開・Actions実行、実際の請求額は未確認。

## 削除再構築と最終確認

| 検証 | 実結果 |
|---|---|
| 削除直前 | 6件の物理ID、記事退避のSHA256、強い整合性のDB読み取りで記事全項目一致を再確認。現在の配備テンプレートも復旧後の退避と一致 |
| 削除 | 旧スタックDELETE_COMPLETE、対象6件すべてDELETE_COMPLETE |
| 再構築差分 | 同じ既定CDK生成template.jsonを使用。CREATE Change Setの6件Addだけを確認して実行 |
| 再構築 | 新スタックCREATE_COMPLETE、6件すべてCREATE_COMPLETE |
| 設定 | Python3.13、index.handler、128MB、timeout10秒、ログ7日、訓練false、AWS_IAMを確認 |
| 再投入前 | 新テーブルが空、旧記事IDのGET404を確認 |
| 再投入 | 退避したタイトル・本文をAPIで1件だけ登録。GET200、登録応答の全項目一致、退避したタイトル・本文とも一致 |
| 認証 | 未認証403、認証済みhealth200 |
| 最終差分 | 同じ既定CDKテンプレートのUPDATE Change Setが変更なし。FAILEDの理由は「The submitted information didn't contain changes. Submit different information to create a change set.」であり、構築失敗ではない。実行していない |
| 最終照合 | AWSが保持するテンプレートとCDK生成JSONが一致。実行ロールの承認済み境界を確認。記事は再投入IDの1件だけ |

時刻（JST）：09:18:16に削除完了を記録、09:19:48に再構築完了を記録、09:19:59に再投入試験の開始時刻を記録し成功、09:20:16に最終確認。厳密な構築時間・復旧時間を測定したものではない。今回は再構築API試験の再試行は不要だった。

- 旧記事ID：d572864839e848339ed59cc0a02f676f
- 再投入記事ID：a0adead8d526436e8d5eda3c196eedac
- 記事のID・作成日時が変わったことを確認
- Function URLも再作成で変更。現在値は `aws cloudformation describe-stacks --stack-name nilab-content-cdk --profile nilab-readonly --region ap-northeast-1` のOutputsから取得する
- 原因ログ抜粋はローカルへ退避済み。AWS上の旧ログは削除済み
- 削除・再構築・最終確認の生記録はwork/cdk-stack-records、記事・段階別API結果はwork/cdk-lifecycle-records。公開成果物外に保持

最終状態は128MB・ログ7日・訓練OFF、記事1件。実際の請求額、全リソースのドリフト検証、性能改善、本番業務経験、cdk deploy/bootstrapの実行を証明するものではない。3方式比較とGitHub公開・Actions実行が残る。
