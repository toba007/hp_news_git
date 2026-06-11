# Positive News MVP

ポジティブニュースサイトの Web 版 MVP です。

## 構成

- `backend`: Flask + SQLite API
- `frontend`: React + Vite

## 起動方法

### バックエンド

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

API: `http://127.0.0.1:5000`

NewsAPI を使って実ニュースを取得する場合は、バックエンド起動前に環境変数を設定します。

```powershell
$env:NEWS_API_KEY="your_newsapi_key"
py app.py
```

検索語を変える場合:

```powershell
$env:NEWS_API_QUERY="education OR environment OR innovation"
$env:NEWS_API_LANGUAGE="en"
$env:NEWS_API_PAGE_SIZE="20"
```

### フロントエンド

別ターミナルで:

```powershell
cd frontend
npm install
npm run dev
```

Web: `http://127.0.0.1:5173`

## ポジティブニュースの定義

このサイトでは、ポジティブニュースを「単に明るい話題ではなく、社会・地域・人の状況が前に進む根拠があるニュース」と定義しています。

採用するニュース:

- 具体的な改善、解決策、支援、回復、挑戦、学びのいずれかがある
- 当事者、地域、社会、環境などへの前向きな影響が説明できる
- 希望だけでなく、取り組み・成果・実証・導入などの根拠がある

除外するニュース:

- 事件、事故、被害、訃報、対立、不祥事が中心で改善要素が薄い
- 宣伝、煽り、予測、根拠のない楽観が中心
- 誰かの失敗や被害を消費する内容

## AIフィルタ

`backend/app.py` にニュース選定用の AI フィルタを追加しています。

- `GEMINI_API_KEY` が未設定の場合: 定義に沿ったキーワードベースのルール判定を使います。
- `GEMINI_API_KEY` が設定されている場合: Gemini API で `include` / `exclude`、`positivity_score`、選定理由を JSON で受け取ります。
- `NEWS_API_KEY` が設定されている場合: NewsAPI から記事を取得し、AIフィルタまたはルール判定でポジティブニュースだけを表示します。
- `NEWS_API_KEY` が未設定または取得失敗の場合: MVP 用モックニュースを表示します。

PowerShell で AI 判定を有効にする例:

```powershell
$env:NEWS_API_KEY="your_newsapi_key"
$env:GEMINI_API_KEY="your_api_key"
$env:GEMINI_MODEL="gemini-2.5-flash"
py app.py
```

## MVP 機能

- 今日のポジティブニュース一覧
- タイトル、要約、カテゴリ、ポジティブ度、選定理由、出典名、元記事リンクの表示
- SQLite 保存
- NewsAPI からの記事取得
