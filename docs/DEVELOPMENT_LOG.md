# Development Log

## 2026-06-08

- `元記事を読む` から `https://example.com/...` に遷移し、Example Domain が表示される問題を確認。
- 原因は MVP 用モックニュースの `source_url` に `example.com` のダミーURLが入っていたこと。
- バックエンドのモックデータでは、実在する元記事URLがない項目の `source_url` を空文字に変更する方針にした。
- 既存 SQLite に残っている `example.com` の古いモックデータは、次回 `/api/news` 取得時に削除して再投入する処理を追加する方針にした。
- フロントエンドでは、URL が未設定または `example.com` の場合はリンクを出さず、`元記事は未設定` と表示する方針にした。
