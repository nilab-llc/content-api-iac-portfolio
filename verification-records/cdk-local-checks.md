# AWS CDK版：ローカル検証記録

実施日：2026-10-28（日本時間）。対象はこのプロジェクトのCDKローカル実装。AWSの権限変更、スタック準備、リソース作成、記事登録は行っていない。

## 結果

| 検証 | 結果 |
|---|---|
| 共通API試験 | 元ソース12件・CloudFormation埋め込み12件・CDK埋め込み12件、合計36件成功 |
| CDK構成・更新試験 | 6件成功。正確な6リソース、既定設定、権限境界と限定アクション、メモリ・ログ変更、訓練フラグだけの変更、不正設定拒否、Asset・bootstrapチェック不在を確認 |
| 権限統合試験 | 2件成功。全Effect/Action/Resource/Conditionの組で既存権限＋CDK追加分と一致、境界と実行ロールの対応を維持 |
| 検証記録の保護 | 5件成功。CDKとCloudFormation間の混在、旧形式の流用、既存フェーズ上書きをAWS接続前に拒否 |
| 全テスト | 49件、全件成功 |
| CDK生成物 | synth_cdk.py --check成功。CDK Constructから再生成した内容とコミット対象template.jsonが一致 |
| 仕様検証 | cfn-lint 1.58.0、東京指定でCDK template.jsonはexit0・指摘なし |
| サイズ | CDK template.json 7,788バイト、直接送信51,200バイト以内。埋め込みZIP4MiB制限も検査成功 |
| 権限案 | build_cdk_permissions.py --check成功。統合候補は空白除外7,569文字で10,240文字以内、全体32,768バイト以内 |
| 既存成果物 | 共通アプリと既存APIテスト・Terraform構成/lockが元成果物とバイト一致。CloudFormationテンプレートは保存済みAWS配備内容とJSON一致、生成物チェックも成功 |

使用環境：Python3.12.14、Node24.19.0、aws-cdk-lib2.274.0、constructs10.8.1。配備対象とCIのPythonは3.13。CI定義は更新済みだがGitHub Actions上では未実行。

CDKではL2のTable/LogGroup/Roleと、明示的なL1のRolePolicy/Function/Urlを組み合わせた。CDK用の追加AWSリソース、Asset manifest、BootstrapVersionパラメータ、CDKMetadataリソースは生成していない。6リソースの論理IDにはCDKが付けたハッシュが含まれ、CloudFormation版と名前を共用しない。

設定変更はスタックパラメータではなく生成時のSettingsで表す。既定、256MB・ログ14日、同設定で訓練ONという3テンプレートを実際に生成して比較した。API試験は生成済みテンプレートの実際のZipFileコードを読み込んで実施。

## 実行した確認

```powershell
python scripts/synth_cdk.py --check
python scripts/build_cloudformation.py --check
python scripts/build_cdk_permissions.py --check
python -m unittest discover -s tests -v
cfn-lint infra/cdk/template.json --regions ap-northeast-1
```

この端末では標準pythonが使えないため、利用可能なPythonとNodeを明示し、依存ライブラリと一時ファイルは公開成果物の外のworkへ置いた。生の試験出力はwork/cdk-local-check-results.jsonへ保存。

実装中にCDK assembly.manifestのPython変換で互換性エラーが出たため、生成済みmanifest.jsonを直接検査する方法へ修正した。権限統合時の重複Sidも再採番で解消し、権限範囲の同値性を確認した。修正後の上記最終チェックはすべて成功。

## 限界と次の工程

今回実施したのはPythonのCDKプログラムによる生成とローカル検証。cdk CLIのsynth/deploy/bootstrap、AWS側ValidateTemplate/Access Analyzer、CDK環境の実構築・変更・ログ調査・復旧・削除再構築は未実施。反映は生成テンプレートをAWS CLIのChange Setへ渡す計画であり、cdk deployの実績として記載しない。

次は既存認証を使ってAWSの現行SSOと権限案を照合し、名前の衝突とポリシーを検証する。統合案はStatementを再構成するため、反映前に現行2方式のJSONとの一致を必ず再確認する。権限追加と実リソース作成は具体的な内容をレビューして承認後に実施する。
