import { useEffect, useMemo, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5000'

function hasArticleUrl(url) {
  return Boolean(url) && !url.includes('example.com')
}

function App() {
  const [news, setNews] = useState([])
  const [definition, setDefinition] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE_URL}/api/news`),
      fetch(`${API_BASE_URL}/api/positive-definition`),
    ])
      .then(async ([newsResponse, definitionResponse]) => {
        if (!newsResponse.ok || !definitionResponse.ok) {
          throw new Error('ニュースを取得できませんでした')
        }
        const newsData = await newsResponse.json()
        const definitionData = await definitionResponse.json()
        setNews(newsData.items ?? [])
        setDefinition(definitionData)
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [])

  const todayText = useMemo(() => {
    return new Intl.DateTimeFormat('ja-JP', {
      month: 'long',
      day: 'numeric',
      weekday: 'short',
    }).format(new Date())
  }, [])

  const averageScore = news.length
    ? Math.round(
        news.reduce((sum, item) => sum + item.positivity_score, 0) / news.length,
      )
    : '-'

  return (
    <main className="app-shell">
      <header className="page-header">
        <p className="eyebrow">{todayText}</p>
        <h1>今日のポジティブニュース</h1>
        <p className="lead">
          前向きな変化、挑戦、改善、解決策が見えるニュースだけを集めました。
        </p>
      </header>

      {definition && (
        <section className="definition-panel" aria-label="ポジティブニュースの定義">
          <div>
            <p className="section-label">{definition.title}</p>
            <p>{definition.summary}</p>
          </div>
          <ul>
            {definition.required_signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="toolbar" aria-label="ニュース概要">
        <div>
          <span className="metric">{news.length}</span>
          <span className="metric-label">件のニュース</span>
        </div>
        <div>
          <span className="metric">{averageScore}</span>
          <span className="metric-label">平均ポジティブ度</span>
        </div>
      </section>

      {isLoading && <p className="status">ニュースを読み込んでいます。</p>}
      {error && <p className="status error">{error}</p>}

      {!isLoading && !error && (
        <section className="news-grid" aria-label="ポジティブニュース一覧">
          {news.map((item) => (
            <article className="news-card" key={item.id}>
              <div className="card-meta">
                <span className="category">{item.category}</span>
                <span className="score">{item.positivity_score}/100</span>
              </div>
              <h2>{item.title}</h2>
              <p className="summary">{item.summary}</p>
              {item.ai_reason && (
                <p className="filter-reason">
                  <span>AIフィルタ</span>
                  {item.ai_reason}
                </p>
              )}
              <div className="card-footer">
                <span className="source">{item.source_name}</span>
                {hasArticleUrl(item.source_url) ? (
                  <a href={item.source_url} target="_blank" rel="noreferrer">
                    元記事を読む
                  </a>
                ) : (
                  <span className="link-disabled">元記事は未設定</span>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </main>
  )
}

export default App
