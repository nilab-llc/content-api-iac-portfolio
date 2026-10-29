# CloudFormation版のローカル検証記録

実施日：2026-10-28（日本時間）。対象はこのコピー内のCloudFormation版。AWS変更、権限付与、記事作成、スタック作成は行っていない。

| 確認 | 結果 |
|---|---|
| 共通APIの既存単体テスト | 12件成功 |
| 生成済みテンプレートのインラインコードに対する同じAPI試験 | 12件成功。日本語の登録・取得、入力検証、訓練503と復旧を含む |
| 検証記録の保護 | 3件成功。既存フェーズの上書き、Terraform記録・旧形式記録のCloudFormationへの流用をAWS接続前に拒否 |
| 合計 | 27件、全件成功 |
| 生成物一致 | build_cloudformation.py --check 成功 |
| CloudFormation仕様検証 | cfn-lint 1.58.0、東京リージョン指定、exit 0・指摘なし |
| 直接送信サイズ | template.jsonは9,107バイト、51,200バイト以内。ZIP4MiB制限も生成時チェック成功 |
| 共通コード・Terraform構成 | 元成果物のhandler.py、既存APIテスト、Terraformのmain/variables/outputs/versions/lockとバイト単位一致 |
| 権限案 | JSON構文、重複Sidなし、アクション名のワイルドカードなしを確認 |
| SSO統合候補 | 元のTerraform版Statementを全件・内容そのままで保持。空白を除いた文字数7,846、10,240以下。ファイル全体32,768バイト以下 |
| 公開対象のコピー | 状態ファイル、plan、ZIP、プロバイダー、認証キャッシュをコピーしていない |

ローカル実行環境はPython 3.12.14、配備対象とCI設定はPython 3.13。AWSのPython 3.13での実行確認は未実施。検証ツールはプロジェクト外のworkに取得し、配布物やLambdaへ含めていない。

実行した主要チェック（リポジトリルート）：

```powershell
python scripts/build_cloudformation.py --check
cfn-lint infra/cloudformation/template.json --regions ap-northeast-1
python -m unittest discover -s tests -v
```

この端末では標準pythonの起動先が使えず、利用可能なローカルPythonを明示して実行した。検証ツールは作業フォルダーから読み込み、cfnlint.runner:mainの正式エントリーポイントで呼び出した。Windowsの出力文字コードと一時フォルダーの書き込み制限を解消後、上記すべてのチェックを再実行して成功した。

CI定義にはCloudFormation生成物一致確認とcfn-lintを追加済み。GitHub Actions上での実行はまだ行っていない。Terraform自体の試験は元成果物の既存実施記録を引き継ぎ、今回のローカル作業では再実行していない。

## 未検証

AWS上の現行権限との一致、Access Analyzer、ValidateTemplate、Change Set、実環境のIAM認証、リソース作成とロールバック、変更時のデータ保持、ログ調査と復旧、削除再構築、実際の請求額。権限案はローカル準備済みの候補であり、AWSで有効と証明済みのポリシーではない。

次はAWS上の現状と権限案を照合する。権限の追加とリソース作成は具体的内容をレビューし、承認後に実施する。
