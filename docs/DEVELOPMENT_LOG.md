# Development Log

## 2026-06-08

- モックニュースの `source_url` に `example.com` が入っていたため、「元記事を読む」から Example Domain に遷移していた問題を修正。
- バックエンドのモックデータでは、実在する元記事URLがない項目の `source_url` を空文字に変更。
- 既存 SQLite に残っている `example.com` の古いモックデータを、次回 `/api/news` 取得時に削除して再投入する処理を追加。
- フロントエンドでは、URL が未設定または `example.com` の場合はリンクを出さず、「元記事は未設定」と表示するよう変更。
