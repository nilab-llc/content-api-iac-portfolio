# Terraform・CloudFormation・AWS CDKの比較

同じAPI・同じAWSサービス・同じ運用確認を用いて、記述と反映方法の違いを比較した。実施日は2026-10-28〜29。個人環境の小規模検証であり、一般的な性能順位や本番運用の優劣を測定したものではない。

## 実装の違い

| 観点 | Terraform | CloudFormation | AWS CDK |
|---|---|---|---|
| 主な定義 | HCL | JSONテンプレート | Python Construct |
| 設定変更 | Terraform変数 | スタックパラメータ | Settingsを変えて再生成 |
| Lambdaコード | archive_fileで共通handler.pyをZIP化 | 共通ソースをZipFileへ生成 | 共通ソースをZipFileへ合成 |
| ハンドラー | handler.handler | index.handler | index.handler |
| 差分確認 | 保存plan | Change Set | CDK生成物の比較＋Change Set |
| 反映 | レビューしたplanをapply | AWS CLIでChange Set実行 | 生成テンプレートをAWS CLIでChange Set実行 |
| 状態の扱い | 非公開のローカルtfstate | CloudFormationスタック | CloudFormationスタック |
| 配布用S3 | なし | なし | なし。Asset不使用 |
| 削除 | destroyの保存planを確認してapply | 対象一覧と退避確認後にDeleteStack | 同左 |
| ローカル試験 | プロバイダーモックのplan・3件 | 生成物一致・cfn-lint・埋め込みAPI | Construct合成・設定差分・権限・埋め込みAPI |

CloudFormationのJSONは共通アプリを取り込む生成処理で保守する。CDKは生成済みJSONを読み込む代用ではなく、Table/LogGroup/RoleのL2と、RolePolicy/Function/UrlのL1から合成する。明示的な権限と6件構成を保つため、必要箇所ではL1を使った。

CDKはLegacyStackSynthesizerを指定し、Asset manifest・BootstrapVersionチェック・CDKMetadataリソースがないことを確認した。本検証にcdk deploy / bootstrapやCDK用S3/ECRの構築実績は含めない。

## 同じ条件で確認した結果

| 段階 | 3方式で確認したこと |
|---|---|
| 構築 | それぞれ6リソースを作成し、IAM認証付きFunction URLから同じAPIを試験 |
| データ保持 | メモリ128→256MB、ログ7→14日へ変更後、既存記事の全項目一致 |
| 訓練 | 環境変数で意図的な保存処理エラーを起こし、記事503・health200・未認証403を確認 |
| 調査・復旧 | storage_failure_drillの原因ログを保存し、フラグOFF後の記事200と全項目一致を確認 |
| 削除・再構築 | 全6件削除、同じコードから全6件作成、新テーブル空・旧ID404、タイトルと本文を再登録 |
| 最終 | 128MB・ログ7日・訓練OFF、記事1件、plan / Change Setの変更なし |

再登録は新ID・新日時となるため、データの完全バックアップ復元と呼ばない。AWS上の旧ログは削除され、原因ログの抜粋は非公開に退避した。

## 差分レビューで得た知見

Terraformではメモリとログの2件更新として確認できた。CloudFormationとCDKでは、その2件に加えてFunctionUrl.TargetFunctionArnがLambda ARNの参照再評価によりConditionalとして表示された。Lambda自体は置換なしだった。Detailsを確認して参照由来の差分だけを許容し、更新後にURLと物理IDが保持されたことを実測した。

CloudFormationの「変更なし」Change SetはFAILEDとその理由を返した。理由を確認して空差分と判定し、構築失敗とは区別した。他の失敗理由まで正常扱いしない。

CloudFormation版の再作成直後は認証済みhealthが403となった。設定・権限・稼働状態を読み取り、記事登録前に停止したことを確認後、構成を変えず1回だけ再試行して成功した。時間経過で解消したが、権限伝播が原因と断定できる証拠は得ていない。CDK版ではこの再試行は不要だった。

## 権限と運用上の判断

Lambdaの実行権限と構築担当の権限を分離し、実行ロールには外部管理の権限境界を指定した。構築担当による境界定義の変更・取り外しを拒否し、PassRoleは対象ロールをLambdaに渡す場合だけ。SSOのプロファイル名nilab-readonlyは歴史的な名前で、実際には対象限定の書き込み権限を持つ。

3方式分のSSO権限を単純追記せず、同じEffect/Action/ConditionのStatementをまとめた。統合前後の全Action/Resource/Conditionの組を照合し、既存権限を維持してCDK分だけ追加したこと、境界条件が別のロールへ交差しないことを試験した。AWS Access Analyzerでも指摘なしを確認した。

小型APIの比較に範囲を絞り、API Gateway、複数環境、自動デプロイ、TerraformのS3状態、負荷試験、専用ダッシュボードは初版へ含めなかった。Terraform状態はローカルなので、共有ロックや自動遠隔バックアップはない。チーム運用へ拡張する場合は別途設計が必要。

## 証拠と限界

- [Terraform実測](../verification-records/terraform-lifecycle.md)
- [CloudFormation実測](../verification-records/cloudformation-lifecycle.md)
- [CDK実測](../verification-records/cdk-lifecycle.md)
- [49件のローカル試験](../verification-records/cdk-local-checks.md)

観察できたのは、この規模・この時点・この構成での再現性と変更・復旧の手順である。料金、厳密な操作時間、RTO、性能差、同時負荷、全リソースのドリフトは測定していない。応募時には自主制作として説明し、商用AWS/IaC経験やcdk deployの経験へ置き換えない。
