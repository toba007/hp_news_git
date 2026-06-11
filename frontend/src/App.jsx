import { useEffect, useMemo, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:5000'

function hasArticleUrl(url) {
  return Boolean(url) && !url.includes('example.com')
}

function App() {
  const [news, setNews] = useState([])
  const [definition, setDefinition] = useState(null)
  const [meta, setMeta] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selectedArticle, setSelectedArticle] = useState(null)

  async function loadNews() {
    const [newsResponse, definitionResponse] = await Promise.all([
      fetch(`${API_BASE_URL}/api/news`),
      fetch(`${API_BASE_URL}/api/positive-definition`),
    ])
    if (!newsResponse.ok || !definitionResponse.ok) {
      throw new Error('ニュースを取得できませんでした')
    }
    const newsData = await newsResponse.json()
    const definitionData = await definitionResponse.json()
    setNews(newsData.items ?? [])
    setMeta(newsData.meta ?? null)
    setDefinition(definitionData)
  }

  useEffect(() => {
    loadNews()
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedArticle) {
      return undefined
    }
    function handleEscape(event) {
      if (event.key === 'Escape') {
        setSelectedArticle(null)
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [selectedArticle])

  async function handleRefresh() {
    setIsRefreshing(true)
    setError('')
    setNotice('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/news/refresh`, {
        method: 'POST',
      })
      if (!response.ok) {
        throw new Error('ニュース更新に失敗しました')
      }
      const result = await response.json()
      await loadNews()
      setNotice(
        result.warning ||
          `${result.source_label ?? 'ニュース'}から${result.fetched ?? 0}件を確認しました`,
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setIsRefreshing(false)
    }
  }

  function handleCardKeyDown(event, item) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setSelectedArticle(item)
    }
  }

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
  const decisionCounts = meta?.decision_counts ?? {}

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">{todayText}</p>
          <h1>今日のポジティブニュース</h1>
          <p className="lead">
            前向きな変化、挑戦、改善、解決策が見えるニュースだけを集めました。
          </p>
        </div>
        <button
          className="refresh-button"
          type="button"
          onClick={handleRefresh}
          disabled={isLoading || isRefreshing}
        >
          {isRefreshing ? '更新中' : 'ニュース更新'}
        </button>
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
        <div>
          <span className="metric">{decisionCounts.review ?? 0}</span>
          <span className="metric-label">要確認で非表示</span>
        </div>
      </section>

      {meta && (
        <section className="source-strip" aria-label="API状態">
          <span>NewsAPI: {meta.news_api_configured ? '有効' : '未設定'}</span>
          <span>Gemini: {meta.gemini_configured ? '有効' : '未設定'}</span>
          <span>採用 {decisionCounts.include ?? 0}</span>
          <span>除外 {decisionCounts.exclude ?? 0}</span>
        </section>
      )}

      {isLoading && <p className="status">ニュースを読み込んでいます。</p>}
      {error && <p className="status error">{error}</p>}
      {notice && !error && <p className="status notice">{notice}</p>}

      {!isLoading && !error && (
        <section className="news-grid" aria-label="ポジティブニュース一覧">
          {news.map((item) => (
            <article className="news-card" key={item.id}>
              <div
                className="card-content"
                role="button"
                tabIndex={0}
                onClick={() => setSelectedArticle(item)}
                onKeyDown={(event) => handleCardKeyDown(event, item)}
                aria-label={`${item.title} の内容を確認`}
              >
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
              </div>
              <div className="card-footer">
                <span className="source">{item.source_name}</span>
                <div className="card-actions">
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => setSelectedArticle(item)}
                  >
                    詳細を見る
                  </button>
                  {hasArticleUrl(item.source_url) ? (
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      元記事を読む
                    </a>
                  ) : (
                    <span className="link-disabled">元記事は未設定</span>
                  )}
                </div>
              </div>
            </article>
          ))}
        </section>
      )}

      {selectedArticle && (
        <div
          className="detail-overlay"
          role="presentation"
          onClick={() => setSelectedArticle(null)}
        >
          <article
            className="detail-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="article-detail-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="card-meta">
              <span className="category">{selectedArticle.category}</span>
              <span className="score">{selectedArticle.positivity_score}/100</span>
            </div>
            <h2 id="article-detail-title">{selectedArticle.title}</h2>
            <p className="detail-summary">{selectedArticle.summary}</p>
            {selectedArticle.ai_reason && (
              <p className="filter-reason">
                <span>AIフィルタ</span>
                {selectedArticle.ai_reason}
              </p>
            )}
            <div className="detail-actions">
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSelectedArticle(null)}
              >
                閉じる
              </button>
              {hasArticleUrl(selectedArticle.source_url) && (
                <a
                  className="primary-link"
                  href={selectedArticle.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  元記事を読む
                </a>
              )}
            </div>
          </article>
        </div>
      )}
    </main>
  )
}

export default App
