# CloudFormation版：設定変更・障害訓練と復旧

実施日：2026-10-28（日本時間）。ユーザー承認の範囲で、東京のnilab-content-cfnだけを操作した。設定変更・障害訓練と復旧の後、追加承認を得て削除再構築・記事再投入まで実施した。

## 結果

| 検証 | 実結果 |
|---|---|
| 事前退避 | 既知のテスト記事1件だけを確認。強い整合性のDB読み取りとHTTP応答の全項目一致を確認し、記事・テンプレート・設定を非公開保存 |
| 設定変更 | MemoryMb 128→256、LogRetentionDays 7→14。ApiFunctionとApiLogsの更新に加え、FunctionUrlの参照再評価によるConditionalを確認。追加承認後に実行しUPDATE_COMPLETE |
| 記事保持 | GET200、退避したID・日時・タイトル・本文が全項目一致 |
| 訓練 | 環境変数SIMULATE_STORAGE_FAILURE false→true。記事GET503、health200、未認証403 |
| 原因調査 | CloudWatch LogsのRuntimeError: storage_failure_drillを確認し、原因ログを非公開保存 |
| 復旧 | 同変数true→false。UPDATE_COMPLETE、記事GET200、全項目一致 |
| URLと物理ID | 3更新すべてでURLの保持とAWS_IAMを確認。復旧後の6リソースの物理IDも初回作成時と全件一致 |
| 削除前の再照合 | 強い整合性のDB読み取りで退避記事との一致を再確認。6件の対象一覧、現在のテンプレート・パラメータ・記事を非公開保存 |

各更新では事前にChange Setを準備し、対象プロパティだけのModifyであることを確認した。Lambda自体のReplacement=Falseを維持。FunctionUrlだけはTargetFunctionArn / Dynamic / ResourceAttribute / ApiFunction.Arn / Conditionalという既知の依存差分を許容し、他の変更は拒否した。DynamoDB、実行ロール、インライン権限の変更は含まれない。

## 時刻（JST）

- 18:02:18：事前退避
- 18:06:02：設定変更後の記事保持確認
- 18:06:48：訓練503の確認
- 18:07:03：原因ログの取得
- 18:07:45：復旧後の記事200・全項目一致
- 18:08:39：削除前の対象と退避の再照合

各JSONに記録したUTC時刻を変換したもの。APIの厳密な障害継続時間、復旧時間保証、性能指標を測ったものではない。

## 現在の状態と退避先

削除前は256MB、timeout10秒、ログ14日、訓練OFF、AWS_IAM、DynamoDBオンデマンド、記事1件だった。設定変更・訓練・復旧の間はURLの変更はなかった。削除再構築後の最終状態は後述の128MB・ログ7日。

記事と段階別確認・原因ログはプロジェクト外のwork/cfn-lifecycle-records、Change Set・スタック・テンプレート・削除対象一覧はwork/cfn-stack-recordsに保存。Git公開対象に含めない。元のTerraform状態と環境は保持する。

続く削除再構築は、対象と影響の提示後、ユーザーのGO承認を得て実施した。境界ポリシーとSSO権限は削除対象外。テーブルとログの削除により元ID・作成日時・AWS上の旧ログは失われた。再投入は退避したタイトル・本文を共通APIから登録し直す方式で、元ID・元日時を保つDB復元ではない。

今回の503はアプリの訓練フラグによるもので、AWS障害を再現した証拠ではない。実際の請求額、全リソースのドリフト、性能改善、本番業務経験は未検証。

## 削除・再構築・最終確認

| 検証 | 実結果 |
|---|---|
| 削除直前 | スタックARN・6物理ID・現在設定をレビュー済み記録と照合。退避ファイルのSHA256を検証し、強い整合性のDB読み取りで記事全項目一致を再確認 |
| 削除 | 旧スタックのDELETE_COMPLETE、対象6件すべてのDELETE_COMPLETEを確認 |
| 再構築差分 | 同じtemplate.json、128MB・ログ7日・訓練false。CREATE Change Setで6件Addのみを確認して実行 |
| 再構築結果 | 新しいスタックのCREATE_COMPLETE、6件すべてCREATE_COMPLETE |
| 実設定 | Python3.13 / index.handler / 128MB / timeout10秒 / 訓練false / ログ7日 / AWS_IAMを確認 |
| 再投入前 | 新テーブルが空、旧IDのAPI取得404を確認 |
| 再投入 | 退避したタイトル・本文をAPIで1回登録。GET200、登録応答との全項目一致、退避したタイトル・本文との一致 |
| 認証 | 未認証health403、認証済みhealth200 |
| 最終差分 | 同じテンプレート・既定値によるUPDATE Change SetはFAILEDとなり、理由が「The submitted information didn't contain changes. Submit different information to create a change set.」。変更なしによる失敗状態であり、構築失敗ではない。実行はしていない |
| 最終照合 | AWS上のテンプレートとローカルJSONが一致。実行ロールの承認済み権限境界を確認。DBの記事は1件で再投入IDと一致 |

再構築直後の初回試験は認証済みhealth403で停止し、その時点では記事登録していない。URLのAWS_IAM、SSOインラインの内容一致、LambdaのActive/Successfulを読み取りで確認した。権限や構成を変更せず、許容された1回の再試行で成功した。時間経過により解消した事実は確認できるが、一時的な権限反映遅延が原因だったと断定できるログ等は取得していない。

確認時刻（JST）：18:13:17に削除完了を記録、18:14:50に再構築完了を記録、18:15:55に再投入試験の開始時刻を記録し成功、18:16:17に最終確認。厳密な構築時間・復旧時間の測定ではない。

- 旧記事ID：6d858798e0374b579427f97bc0d8115c
- 再投入ID：d9f93f3081644a68a02484d4f11b7742
- 記事の作成日時も変わったことを確認
- Function URLは再作成で変更。現在値は `aws cloudformation describe-stacks --stack-name nilab-content-cfn --profile nilab-readonly --region ap-northeast-1` のOutputsから取得する
- 旧AWSログは削除済み。訓練の原因ログ抜粋は非公開退避済み
- 削除・再構築・最終確認の生JSONはwork/cfn-stack-records、記事と段階別結果はwork/cfn-lifecycle-records。いずれも公開成果物フォルダーの外

最終状態：128MB、timeout10秒、ログ7日、訓練OFF、AWS_IAM、DynamoDBオンデマンド、再投入記事1件。環境はAWS上に残している。Terraform環境と元の状態ファイルは保持。CDK版・GitHub公開・Actions実行・実際の請求額の確認は未実施。
