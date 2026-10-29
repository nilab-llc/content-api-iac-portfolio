# CloudFormation設定変更：実行前停止と差分レビュー

2026-10-28（日本時間）。設定変更・記事保持・障害訓練と復旧の承認を得て開始。設定変更前に既知のテスト記事1件を強い整合性で読み、API応答との全項目一致を確認して非公開のwork/cfn-lifecycle-recordsへ退避した。退避時刻18:02:18 JST。

UsePreviousTemplate=Trueで、MemoryMbを128から256、LogRetentionDaysを7から14にするUPDATE Change Set nilab-content-cfn-settings-001を準備。訓練falseは維持。

当初は2件Modify・置換なしを見込んだが、Change Setに3件表示されたため、実行前のガードで停止した。ExecuteChangeSetは呼び出していない。AWSの稼働設定は128MB・ログ7日・訓練falseのまま。

| リソース | 変更 | Replacement | 根拠 |
|---|---|---|---|
| ApiFunction | MemorySize | False | MemoryMbのパラメータ変更 |
| ApiLogs | RetentionInDays | False | LogRetentionDaysのパラメータ変更 |
| FunctionUrl | TargetFunctionArn | Conditional | Dynamic / ResourceAttribute / ApiFunction.Arnの参照再評価 |

DynamoDB、実行ロール、インライン権限の変更は含まれない。URLのAuthType変更も含まれない。追加されたURLのConditionalは、Fn::GetAttでLambda ARNを参照する依存関係に由来することをDetailsで確認した。Lambda自体は置換なしと表示されている。ただし現時点でURLが保持されることを実測しておらず、Conditionalを無条件に置換なしへ読み替えない。

公式根拠：[ResourceChangeDetail](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChangeDetail.html)、[ResourceChange](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_ResourceChange.html)。Dynamicは参照先の更新結果に依存する評価で、RequiresRecreation=AlwaysとDynamicの組み合わせがConditionalとなる。

レビュー候補：この依存関係によるFunctionUrlのConditionalだけを明示的に許容し、3件Modifyを実行する。DynamoDBの変更、Lambdaの置換、URL認証の変更、他のプロパティ変更は引き続き拒否する。実行前後でURL・物理ID・AWS_IAMを照合し、API確認は現在のURLを取得して実施する。記事全項目一致と実設定を確認後、訓練・復旧へ進む。この差分拡張の受諾待ち。

その後ユーザーのGO承認を得て上記差分を実行した。設定変更・訓練・復旧のすべてでURLと全6物理IDが保持され、記事保持と復旧を確認済み。さらに別途承認後に削除再構築も完了。最終記録は `cloudformation-lifecycle.md` を参照。本節の「受諾待ち」は当時の状態を記した履歴。
