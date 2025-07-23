# embulk-lambda-container

Embulkをコンテナイメージとして動作させるAWS Lambdaの構成例です。

Docker × Lambda でEmbulkを動作させることで、サーバーレスでスケーラブルなデータパイプラインを構築できます。

> **📝 詳細な解説記事**: [EmbulkをDocker×Lambdaで動かす（開発＆本番環境）](https://zenn.dev/konan/articles/653381379e846f)  
> このREADMEと合わせてお読みください。

## 特徴

- **サーバーレス**: Lambda上でEmbulkを実行
- **コンテナベース**: DockerコンテナによりEmbulkとプラグインを一括管理
- **設定ファイル駆動**: Liquid テンプレートによる柔軟な設定管理
- **マルチソース対応**: MySQL、PostgreSQL、MongoDB → Redshift への転送

## アーキテクチャ

```
EventBridge → Lambda (Container) → [Source DB] → S3 → Redshift
```

- **Lambda**: Embulk実行環境（コンテナイメージ）
- **ECR**: Dockerイメージレジストリ
- **EventBridge**: スケジュール実行
- **S3**: 中間ファイル保存領域

## ディレクトリ構成

```
embulk-lambda-container/
├── .env.sample             # 環境変数のサンプル
├── .gitignore              # Git除外設定
├── Dockerfile              # マルチステージビルド設定
├── embulk.properties       # Embulk設定
├── config/                 # データ転送設定ファイル
│   ├── config_users.yml.liquid     # PostgreSQL → Redshift
│   ├── config_orders.yml.liquid    # MySQL → Redshift  
│   └── config_products.yml.liquid  # MongoDB → Redshift
├── src/
│   ├── main.py             # Lambdaハンドラ
│   └── requirements.txt    # Python依存関係
└── README.md
```

## 開発環境セットアップ

### 1. 環境変数の設定

`.env.sample` を参考に `.env` ファイルを作成：

```bash
cp .env.sample .env
# .envファイルを編集して適切な値を設定
```

### 2. Dockerイメージのビルド

```bash
docker build -t embulk-lambda-container .
```

### 3. ローカルテスト

```bash
# 例: usersテーブルの転送テスト
docker run --rm --env-file .env --entrypoint python embulk-lambda-container \
  main.py '{"config_file_name":"config_users.yml.liquid"}'
```

### 4. データ転送の停止

```bash
docker stop <container_name>
```

## 本番デプロイ

### ECRへのプッシュ

```bash
# 1. ECRログイン
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin <your-account-id>.dkr.ecr.ap-northeast-1.amazonaws.com

# 2. イメージタグ付け
docker tag embulk-lambda-container:latest <your-account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/embulk-lambda-container:latest

# 3. プッシュ
docker push <your-account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/embulk-lambda-container:latest
```

### Lambda関数の更新

1. Lambda関数の［新しいイメージをデプロイ］をクリック
2. ECRにプッシュした最新イメージを選択

### 動作確認

Lambda関数のテストイベント：

```json
{
  "config_file_name": "config_users.yml.liquid"
}
```

## 設定ファイルの追加

新しいデータソースを追加する場合：

1. `config/config_new_table.yml.liquid` を作成
2. EventBridge ルールを追加してスケジュール実行を設定

## ARM64環境（M1/M2 Mac）での注意事項

本プロジェクトは `linux/amd64` でビルドされているため、ARM64環境では：

- Rosetta2エミュレーションにより**3-5倍処理が遅く**なります
- ローカルでの動作テストは参考程度に留めてください
- 本格的なテストはx86_64環境またはLambda環境で実行してください

## 参考資料

- [Embulk公式ドキュメント](https://www.embulk.org/)
- [AWS Lambda コンテナイメージ](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)