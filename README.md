# mcp-vidu

## Roo Code での Streamable HTTP（Vidu）設定

Roo Code はすでに Streamable HTTP transport に対応しています。STDIO や SSE と同様に利用でき、リモート MCP サーバーとの通信では推奨方式です。

- サポート状況: すでに対応済み（Roo Code 本体の実装・ドキュメントに記載）
- トランスポート種別: STDIO（ローカル）、Streamable HTTP（推奨のリモート）、SSE（レガシー）


### Vidu 用の設定例

既存の MCP 設定に Vidu を Streamable HTTP で追加／修正する例です。他のサーバー定義はそのまま、`Vidu` のみ Streamable HTTP を指定します。

注意: 下記の値中の API キーやトークンは必ずご自身のものに置き換え、機密情報はリポジトリにコミットしないでください。

```json
{
  "mcpServers": {
    "Vidu": {
      "type": "streamable-http",
      "url": "https://api.vidu.com/mcp/v1",
      "headers": {
        "Authorization": "Token vda_xxxxxxx"
      }
    }
  }
}
```

重要な変更点:

- `type: "streamable-http"`: Vidu を Streamable HTTP で利用
- `url`: 既存のエンドポイントを指定（例: `https://api.vidu.com/mcp/v1`）
- `headers.Authorization`: 認証トークンを設定

上記設定に置き換えたうえで、Roo Code から接続を再試行してください。

## Examples

- Vidu API 最小サンプル（Python/uv）: `example/README.md`
- 画像→動画サンプルスクリプト: `example/src/vidu_examples/img2video.py`
