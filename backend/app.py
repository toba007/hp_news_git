from __future__ import annotations

import json
import os
import sqlite3
from datetime import date
from pathlib import Path
from urllib import error, parse, request

from flask import Flask, jsonify
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "positive_news.db"
GEMINI_GENERATE_CONTENT_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)
NEWS_API_EVERYTHING_URL = "https://newsapi.org/v2/everything"
NEWS_API_DEFAULT_QUERY = (
    "improvement OR solution OR support OR recovery OR breakthrough OR "
    "innovation OR success OR education OR environment"
)


POSITIVE_NEWS_DEFINITION = {
    "title": "ポジティブニュースの定義",
    "summary": (
        "単に明るい話題ではなく、社会・地域・人の状況が前に進む根拠があるニュース。"
        "課題や被害を扱う場合も、具体的な改善、支援、解決策、回復、挑戦、学びが"
        "記事の中心にあるものを採用します。"
    ),
    "required_signals": [
        "具体的な改善、解決策、支援、回復、挑戦、学びのいずれかがある",
        "当事者、地域、社会、環境などへの前向きな影響が説明できる",
        "希望だけでなく、取り組み・成果・実証・導入などの根拠がある",
    ],
    "exclude_signals": [
        "事件、事故、被害、訃報、対立、不祥事が中心で改善要素が薄い",
        "宣伝、煽り、予測、根拠のない楽観が中心",
        "誰かの失敗や被害を消費する内容",
    ],
    "threshold": 70,
}

POSITIVE_KEYWORDS = [
    "改善",
    "解決",
    "支援",
    "回復",
    "復興",
    "再生",
    "前進",
    "成功",
    "成果",
    "開始",
    "導入",
    "開発",
    "実証",
    "挑戦",
    "学び",
    "交流",
    "削減",
    "向上",
    "活用",
    "improvement",
    "solution",
    "support",
    "recovery",
    "breakthrough",
    "innovation",
    "success",
    "education",
    "environment",
    "sustainable",
    "progress",
]

RISK_KEYWORDS = [
    "死亡",
    "事故",
    "事件",
    "災害",
    "被害",
    "不祥事",
    "逮捕",
    "批判",
    "対立",
    "炎上",
    "訃報",
    "death",
    "accident",
    "crime",
    "disaster",
    "damage",
    "arrest",
    "conflict",
    "scandal",
    "war",
]


MOCK_NEWS = [
    {
        "title": "地域の空き家を学習スペースへ再生する取り組みが拡大",
        "summary": (
            "自治体と学生団体が協力し、空き家を放課後の学習スペースとして活用。"
            "地域住民の見守りも加わり、子どもたちの居場所づくりと地域交流の両方に"
            "成果が出ています。"
        ),
        "category": "地域",
        "positivity_score": 92,
        "source_name": "Positive Local",
        "source_url": "",
    },
    {
        "title": "海洋プラスチック削減へ、新素材の実証実験が前進",
        "summary": (
            "大学発スタートアップが分解されやすい包装素材の実証実験を開始。"
            "小売店との連携により、使いやすさと環境負荷低減を両立する解決策として"
            "期待されています。"
        ),
        "category": "環境",
        "positivity_score": 88,
        "source_name": "Green Future News",
        "source_url": "",
    },
    {
        "title": "中小企業の技術継承を支えるAI研修プログラムが始動",
        "summary": (
            "熟練技術者のノウハウを動画とAIで整理し、若手が学びやすい研修にする"
            "試みが始まりました。人手不足への現実的な改善策として、複数の工場で"
            "導入が進んでいます。"
        ),
        "category": "テクノロジー",
        "positivity_score": 84,
        "source_name": "Tech Hope",
        "source_url": "",
    },
    {
        "title": "被災地の商店街で若手起業家による新店舗が相次いで開業",
        "summary": (
            "復興が進む商店街で、地元食材や観光体験を活かした新店舗が増えています。"
            "住民と来訪者の交流が生まれ、地域経済の再生に向けた前向きな動きが"
            "広がっています。"
        ),
        "category": "経済",
        "positivity_score": 90,
        "source_name": "Hope Economy",
        "source_url": "",
    },
    {
        "title": "高校生チームが高齢者向け移動支援アプリを開発",
        "summary": (
            "高校生が地域課題の解決を目指し、バス時刻や徒歩ルートをわかりやすく"
            "案内するアプリを制作。試験利用した高齢者からは、外出の不安が減った"
            "との声が出ています。"
        ),
        "category": "挑戦",
        "positivity_score": 95,
        "source_name": "Youth Challenge Journal",
        "source_url": "",
    },
]


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    init_db()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/news")
    def list_news():
        ensure_seed_news()
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, summary, category, positivity_score, source_name,
                       source_url, published_date, ai_decision, ai_reason
                FROM news
                WHERE ai_decision = 'include' AND positivity_score >= ?
                ORDER BY positivity_score DESC, published_date DESC, id DESC
                """,
                (POSITIVE_NEWS_DEFINITION["threshold"],),
            ).fetchall()
        return jsonify({"items": [dict(row) for row in rows]})

    @app.get("/api/positive-definition")
    def positive_definition():
        return jsonify(POSITIVE_NEWS_DEFINITION)

    @app.post("/api/news/refresh")
    def refresh_news():
        changed = fetch_and_store_positive_news()
        return jsonify({"changed": changed})

    return app


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                category TEXT NOT NULL,
                positivity_score INTEGER NOT NULL CHECK (
                    positivity_score >= 0 AND positivity_score <= 100
                ),
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                published_date TEXT NOT NULL,
                ai_decision TEXT NOT NULL DEFAULT 'include',
                ai_reason TEXT NOT NULL DEFAULT ''
            )
            """
        )
        ensure_column(conn, "news", "ai_decision", "TEXT NOT NULL DEFAULT 'include'")
        ensure_column(conn, "news", "ai_reason", "TEXT NOT NULL DEFAULT ''")


def ensure_column(
    conn: sqlite3.Connection, table_name: str, column_name: str, definition: str
) -> None:
    columns = {
        row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def ensure_seed_news() -> None:
    mock_titles = [item["title"] for item in MOCK_NEWS]
    placeholders = ", ".join("?" for _ in mock_titles)
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
        current_mock_count = conn.execute(
            f"SELECT COUNT(*) FROM news WHERE title IN ({placeholders})", mock_titles
        ).fetchone()[0]
        missing_classification = conn.execute(
            "SELECT COUNT(*) FROM news WHERE ai_reason = ''"
        ).fetchone()[0]
        stale_mock_links = conn.execute(
            """
            SELECT COUNT(*) FROM news
            WHERE title IN ({}) AND source_url LIKE 'https://example.com/%'
            """.format(placeholders),
            mock_titles,
        ).fetchone()[0]
    if (
        count == 0
        or current_mock_count < len(MOCK_NEWS)
        or missing_classification > 0
        or stale_mock_links > 0
    ):
        fetch_and_store_positive_news()


def fetch_and_store_positive_news() -> int:
    """Fetch positive news from NewsAPI when configured, otherwise use mock data."""
    news_api_key = os.getenv("NEWS_API_KEY")
    if news_api_key:
        try:
            items = fetch_newsapi_news(news_api_key)
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            items = build_mock_news_with_reason(
                f"NewsAPI取得に失敗したためモックデータを使用: {exc}"
            )
    else:
        items = MOCK_NEWS

    changed = 0
    with get_connection() as conn:
        mock_titles = [item["title"] for item in MOCK_NEWS]
        placeholders = ", ".join("?" for _ in mock_titles)
        conn.execute(f"DELETE FROM news WHERE title IN ({placeholders})", mock_titles)
        conn.execute("DELETE FROM news WHERE source_url LIKE 'https://example.com/%'")
        for item in items:
            classification = classify_news_item(item)
            reason_prefix = item.get("ai_reason_prefix", "")
            reason = classification["reason"]
            if reason_prefix:
                reason = f"{reason_prefix} / {reason}"
            cursor = conn.execute(
                """
                INSERT INTO news (
                    title, summary, category, positivity_score, source_name,
                    source_url, published_date, ai_decision, ai_reason
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title) DO UPDATE SET
                    summary = excluded.summary,
                    category = excluded.category,
                    positivity_score = excluded.positivity_score,
                    source_name = excluded.source_name,
                    source_url = excluded.source_url,
                    published_date = excluded.published_date,
                    ai_decision = excluded.ai_decision,
                    ai_reason = excluded.ai_reason
                """,
                (
                    item["title"],
                    item["summary"],
                    item["category"],
                    classification["positivity_score"],
                    item["source_name"],
                    item["source_url"],
                    item.get("published_date") or date.today().isoformat(),
                    classification["decision"],
                    reason,
                ),
            )
            changed += cursor.rowcount
    return changed


def fetch_newsapi_news(api_key: str) -> list[dict]:
    query = os.getenv("NEWS_API_QUERY", NEWS_API_DEFAULT_QUERY)
    language = os.getenv("NEWS_API_LANGUAGE", "en")
    page_size = int(os.getenv("NEWS_API_PAGE_SIZE", "20"))
    page_size = max(1, min(page_size, 100))
    params = {
        "q": query,
        "searchIn": "title,description",
        "language": language,
        "sortBy": "publishedAt",
        "pageSize": str(page_size),
    }
    url = f"{NEWS_API_EVERYTHING_URL}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"X-Api-Key": api_key}, method="GET")

    try:
        with request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"NewsAPI error {exc.code}: {detail}") from exc

    if data.get("status") != "ok":
        raise ValueError(data.get("message", "NewsAPI returned an error"))

    items = [
        item
        for article in data.get("articles", [])
        if (item := normalize_newsapi_article(article)) is not None
    ]
    if not items:
        raise ValueError("NewsAPI returned no usable articles")
    return items


def normalize_newsapi_article(article: dict) -> dict | None:
    title = clean_newsapi_text(article.get("title"))
    summary = clean_newsapi_text(article.get("description")) or clean_newsapi_text(
        article.get("content")
    )
    source_url = article.get("url") or ""
    if not title or not summary or not source_url or title == "[Removed]":
        return None

    source = article.get("source") or {}
    published_at = article.get("publishedAt") or date.today().isoformat()
    return {
        "title": title,
        "summary": summary,
        "category": infer_category(f"{title} {summary}"),
        "positivity_score": 0,
        "source_name": source.get("name") or "NewsAPI",
        "source_url": source_url,
        "published_date": published_at[:10],
    }


def clean_newsapi_text(value: str | None) -> str:
    if not value:
        return ""
    return value.replace("\r", " ").replace("\n", " ").strip()


def infer_category(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["environment", "climate", "energy"]):
        return "環境"
    if any(word in lowered for word in ["technology", "ai", "innovation"]):
        return "テクノロジー"
    if any(word in lowered for word in ["education", "school", "student"]):
        return "教育"
    if any(word in lowered for word in ["health", "medical", "care"]):
        return "医療・福祉"
    return "ニュース"


def build_mock_news_with_reason(reason: str) -> list[dict]:
    return [{**item, "ai_reason_prefix": reason} for item in MOCK_NEWS]


def classify_news_item(item: dict) -> dict:
    """Use Gemini when configured, otherwise fall back to a local rule filter."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            return classify_with_gemini(item, api_key)
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            fallback = classify_with_rules(item)
            fallback["reason"] = f"AI判定に失敗したためルール判定を使用: {exc}"
            return fallback
    return classify_with_rules(item)


def classify_with_rules(item: dict) -> dict:
    text = f"{item['title']} {item['summary']}"
    positive_hits = [word for word in POSITIVE_KEYWORDS if word in text]
    risk_hits = [word for word in RISK_KEYWORDS if word in text]
    score = 50 + min(len(positive_hits) * 8, 40) - min(len(risk_hits) * 10, 35)

    if risk_hits and not positive_hits:
        score -= 15

    score = max(0, min(100, score))
    decision = (
        "include"
        if score >= POSITIVE_NEWS_DEFINITION["threshold"] and positive_hits
        else "exclude"
    )
    reason_parts = []
    if positive_hits:
        reason_parts.append(f"前向きな要素: {', '.join(positive_hits[:4])}")
    if risk_hits:
        reason_parts.append(f"注意要素: {', '.join(risk_hits[:4])}")
    if not reason_parts:
        reason_parts.append("明確な改善・支援・解決策の根拠が不足")

    return {
        "decision": decision,
        "positivity_score": score,
        "reason": " / ".join(reason_parts),
    }


def classify_with_gemini(item: dict, api_key: str) -> dict:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    payload = {
        "systemInstruction": {
            "parts": [{"text": build_positive_news_filter_prompt()}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": json.dumps(
                            {
                                "title": item["title"],
                                "summary": item["summary"],
                                "category": item["category"],
                                "source_name": item["source_name"],
                            },
                            ensure_ascii=False,
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "decision": {
                        "type": "STRING",
                        "enum": ["include", "exclude"],
                    },
                    "positivity_score": {
                        "type": "INTEGER",
                    },
                    "reason": {
                        "type": "STRING",
                    },
                },
                "required": ["decision", "positivity_score", "reason"],
            },
        },
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        GEMINI_GENERATE_CONTENT_URL.format(model=model, api_key=api_key),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Gemini API error {exc.code}: {detail}") from exc

    output_text = extract_gemini_response_text(data)
    result = json.loads(output_text)
    score = max(0, min(100, int(result["positivity_score"])))
    return {
        "decision": result["decision"],
        "positivity_score": score,
        "reason": result["reason"][:240],
    }


def extract_gemini_response_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    for candidate in candidates:
        for part in candidate.get("content", {}).get("parts", []):
            if part.get("text"):
                return part["text"]
    raise ValueError("Gemini response did not include text")


def build_positive_news_filter_prompt() -> str:
    return f"""
あなたはポジティブニュースサイトのニュース選定AIです。以下の定義に従い、記事を include / exclude で判定してください。

定義:
{POSITIVE_NEWS_DEFINITION["summary"]}

採用に必要な要素:
- {POSITIVE_NEWS_DEFINITION["required_signals"][0]}
- {POSITIVE_NEWS_DEFINITION["required_signals"][1]}
- {POSITIVE_NEWS_DEFINITION["required_signals"][2]}

除外する要素:
- {POSITIVE_NEWS_DEFINITION["exclude_signals"][0]}
- {POSITIVE_NEWS_DEFINITION["exclude_signals"][1]}
- {POSITIVE_NEWS_DEFINITION["exclude_signals"][2]}

判定ルール:
- positivity_score は 0 から 100。
- {POSITIVE_NEWS_DEFINITION["threshold"]} 点以上かつ前向きな根拠が明確な場合だけ include。
- 課題を扱っていても、改善策や回復が記事の中心なら include できる。
- 理由は日本語で短く、採用・除外の根拠を具体的に書く。
""".strip()


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
