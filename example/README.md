# Vidu Image to Video サンプル（Python）

Vidu の Image to Video API を叩く最小サンプルです。.env から API キーを読み込み、指定した画像から動画生成タスクを作成します。Python + uv で環境構築します。

`.env` の例:

```
VIDU_API_KEY=your_api_key_here
```

## Python（uv）

前提: Python 3.9+ と `uv` が利用可能であること

1) セットアップ

```
cd example
cp .env.example .env
uv sync
```

2) 実行

```
uv run img2video \
  --model viduq1 \
  --image "https://prod-ss-images.s3.cn-northwest-1.amazonaws.com.cn/vidu-maas/template/image2video.png" \
  --prompt "The astronaut waved and the camera moved up." \
  --duration 5 \
  --resolution 1080p \
  --movement_amplitude auto \
  --off_peak false
```

またはモジュールを直接実行:

```
uv run python -m vidu_examples.img2video --model viduq1 --image <URL>
```

主なオプション:

- `--image` 画像URLまたは data URL（Base64）
- `--prompt` テキストプロンプト
- `--model` `viduq1` | `viduq1-classic` | `vidu2.0` | `vidu1.5`
- `--duration` 4 または 5（モデルに依存）
- `--resolution` `360p` | `720p` | `1080p`（モデルと秒数に依存）
- `--movement_amplitude` `auto` | `small` | `medium` | `large`
- `--off_peak` `true` | `false`
- `--bgm` `true` | `false`
- `--seed` 整数
- `--watermark` `true` | `false`
- `--callback_url` URL
- `--payload` 文字列（透過パラメータ）

> 注: 本スクリプトは「タスク作成（POST /ent/v2/img2video）」のみを行います。完了の確認・動画URL取得は Vidu の「Get Generation」エンドポイントをご利用ください。

## 動画の取得（ステータス確認とダウンロード）

作成時のレスポンスに含まれる `task_id` を使って、ステータスを取得します。`get_generation` コマンドを用意しています。

完了までポーリングして動画URLを検出したら保存:

```
uv run get_generation --task_id <YOUR_TASK_ID> --wait --download output.mp4
```

ステータスを一度だけ確認:

```
uv run get_generation --task_id <YOUR_TASK_ID>
```

注:
- 公式の取得エンドポイントは `GET https://api.vidu.com/ent/v2/tasks/{id}/creations` です（本スクリプトはこれを最優先で利用します）。
- レスポンスの `creations[0].url` が動画URLで、有効期限は約1時間です。期限切れのときは再度このエンドポイントを呼ぶと新しい署名URLが返ります。
- うまくいかない場合は詳細ログ: `uv run get_generation --task_id <ID> --verbose`
- エンドポイントを手動指定したい場合: `uv run get_generation --task_id <ID> --url "https://api.vidu.com/ent/v2/tasks/{task_id}/creations" --method GET`
- 企業版や別リージョンなどベースURLが異なる場合は、環境変数 `VIDU_API_BASE` で上書き可能です（例: `export VIDU_API_BASE=https://api.vidu.com/ent/v2`）。
- コールバック運用をする場合は、`img2video` 呼び出し時に `--callback_url` を設定し、受信したコールバックの `state` が `success` になったタイミングでその内容から動画URLを取得してください。
