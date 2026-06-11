# ポジティブニュースサイト開発メモ

## 目的
ネガティブなニュースを除外し、明るいニュースだけを表示するサイト。

## 現在の構成
- Gemini APIでAI判定
- NGワードで一次除外
- 判定結果は approve / review / reject
- APIキーは GEMINI_API_KEY

## AI判定ルール
approve:
- 地域貢献
- 動物
- 教育
- 福祉
- 環境改善
- 人助け
- ほっこりする話

reject:
- 事件
- 事故
- 殺人
- 逮捕
- 裁判
- 戦争
- 不況
- 炎上

review:
- 災害復興
- 病気克服
- 社会問題解決
- ネガティブ要素を含むが結果が良い話

## Codexへの方針
- 既存実装を壊さない
- 変更前に関連ファイルを確認する
- Gemini APIキーをコードに直書きしない
- JSONパース失敗時は review 扱いにする

## 2026-06-08 作業メモ
- ローカル作業フォルダ: `hp-news`
- 現在のMVP構成:
  - backend: Flask + SQLite
  - frontend: React + Vite
- ポジティブニュースの定義を追加:
  - 単に明るい話題ではなく、社会・地域・人の状況が前に進む根拠があるニュース
  - 改善、解決策、支援、回復、挑戦、学びのいずれかを重視
  - 事件、事故、災害、訃報、対立、不祥事が中心で改善要素が薄いものは除外
- 実装済み:
  - `/api/positive-definition`
  - AIフィルタ判定理由 `ai_reason`
  - `ai_decision = include` かつ `positivity_score >= 70` のニュースだけ表示
  - APIキー未設定時はキーワードベースのルール判定
- 注意:
  - このメモの既存方針は Gemini API 前提。
  - 2026-06-08時点の途中実装では OpenAI Responses API 前提だったが、Gemini API に変更した。
  - APIキーはコード、README、GitHubメモに書かない。
- 2026-06-08 Gemini API 変更:
  - AI判定は `GEMINI_API_KEY` / `GEMINI_MODEL` を参照する。
  - デフォルトモデルは `gemini-2.5-flash`。
  - Gemini `generateContent` の JSON出力を使い、`include` / `exclude`、`positivity_score`、`reason` を受け取る。
  - `GEMINI_API_KEY` 未設定時はキーワードベースのルール判定にフォールバックする。
- 環境:
  - Python 3.13.4 をインストール済み
  - `backend/.venv` 作成済み
  - Flask依存関係インストール済み
  - API起動確認済み: `http://127.0.0.1:5000/api/health`
  - フロント起動確認済み: `http://127.0.0.1:5173/`

## 2026-06-11 作業メモ
- ローカルの `hp-news` フォルダは `.git` が無い状態だったため、GitHub リポジトリ `https://github.com/toba007/hp_news_git.git` の `main` 履歴を取得して接続した。
- ローカルに残っていた MVP 実装を GitHub に push する作業を実施。
- push 対象:
  - Flask + SQLite の `backend`
  - React + Vite の `frontend`
  - MVP 詳細版の `README.md`
  - Example Domain リンク修正済みの `docs/DEVELOPMENT_LOG.md`
- `.gitignore` により `backend/positive_news.db`、`backend/.venv/`、`frontend/node_modules/`、`frontend/dist/`、`__pycache__/` はコミット対象外。

## 2026-06-11 NewsAPI 作業メモ
- NewsAPI の APIキーはコードやドキュメントへ直書きしない。
- バックエンドは `NEWS_API_KEY` 環境変数がある場合に NewsAPI `/v2/everything` から記事を取得する。
- NewsAPI 認証は `X-Api-Key` ヘッダーを使い、URL にキーを含めない。
- 検索条件は `NEWS_API_QUERY`、`NEWS_API_LANGUAGE`、`NEWS_API_PAGE_SIZE` で調整可能。
- `NEWS_API_KEY` 未設定または取得失敗時は、従来通り MVP 用モックニュースにフォールバックする。
- NewsAPI の記事も `GEMINI_API_KEY` があれば Gemini 判定、なければローカルルール判定を使う。
