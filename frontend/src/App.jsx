import { useState, useEffect, useCallback } from 'react'

function App() {
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(false)
  
  // Filters and Sorting
  const [searchQuery, setSearchQuery] = useState('')
  const [category, setCategory] = useState('All')
  const [pricing, setPricing] = useState('All')
  const [sortBy, setSortBy] = useState('highest_rated')

  const [showSubmitModal, setShowSubmitModal] = useState(false)
  const [submitUrl, setSubmitUrl] = useState('')
  const [submitLoading, setSubmitLoading] = useState(false)
  const [submitMessage, setSubmitMessage] = useState('')

  const API_URL = import.meta.env.DEV ? 'http://localhost:8000/api' : '/api'

  const fetchTools = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (searchQuery && category === 'All' && pricing === 'All' && sortBy === 'highest_rated') {
         // It's handled by handleSearchSubmit now, but if homepage loads with query:
      }
      if (searchQuery) params.append('search', searchQuery)
      if (category !== 'All') params.append('category', category)
      if (pricing !== 'All') params.append('pricing', pricing)
      params.append('sort', sortBy)

      const res = await fetch(`${API_URL}/tools?${params.toString()}`)
      const data = await res.json()
      setTools(data)
    } catch (err) {
      console.error('Failed to fetch tools:', err)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, category, pricing, sortBy])

  useEffect(() => {
    if (!searchQuery) {
      fetchTools()
    }
  }, [fetchTools, searchQuery])

  const handleSearchSubmit = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) {
      fetchTools()
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(searchQuery)}`)
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      setTools(data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpvote = async (id) => {
    try {
      const res = await fetch(`${API_URL}/tools/${id}/upvote`, { method: 'POST' })
      if (!res.ok) throw new Error('Upvote failed')
      
      const data = await res.json()
      // Optimistically update
      setTools(tools.map(t => t.id === id ? { ...t, upvotes: data.upvotes } : t))
    } catch (err) {
      console.error(err)
    }
  }

  const handleSubmitTool = async (e) => {
    e.preventDefault()
    if (!submitUrl) return
    setSubmitLoading(true)
    setSubmitMessage('')
    try {
      const res = await fetch(`${API_URL}/tools/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: submitUrl })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to submit')
      setSubmitMessage(data.message || 'Tool submitted successfully!')
      setSubmitUrl('')
      fetchTools() // Refresh the list
    } catch (err) {
      setSubmitMessage(err.message)
    } finally {
      setSubmitLoading(false)
    }
  }

  return (
    <>
      <div className="bg-shape bg-shape-1"></div>
      <div className="bg-shape bg-shape-2"></div>

      <div className="container">
        <header className="hero">
          <h1 className="hero-title">Extreme <span className="gradient-text">AI Tools</span></h1>
          <p className="hero-subtitle">The ultimate community-driven platform to discover, sort, and upvote the top Artificial Intelligence platforms and software.</p>
          
          <form onSubmit={handleSearchSubmit} className="search-container">
            <input 
              type="text" 
              className="search-input" 
              placeholder="Search by name or description..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <button type="submit" className="search-btn">
              <span>Search</span>
            </button>
          </form>
          <div style={{ marginTop: '1.5rem' }}>
            <button className="search-btn" style={{ background: 'transparent', border: '1px solid var(--accent-primary)' }} onClick={() => setShowSubmitModal(true)}>
              + Submit New Tool
            </button>
          </div>
        </header>

        <main className="main-content">
          {loading ? (
            <div className="loader">
              <div className="spinner"></div>
            </div>
          ) : tools.length === 0 ? (
            <div className="status-msg">
              <h3>No tools found matching your criteria.</h3>
            </div>
          ) : (
            <div className="results-list">
              {tools.map((tool) => (
                <div className="ph-card" key={tool.id}>
                  <img src={tool.favicon} alt={tool.title} className="tool-favicon" />
                  
                  <div className="tool-info">
                    <h3 className="card-title">
                      <a href={tool.url} target="_blank" rel="noopener noreferrer">{tool.title}</a>
                    </h3>
                    <p className="card-desc">{tool.description}</p>
                    <div className="badges">
                      <span className="badge badge-category">{tool.category}</span>
                      <span className="badge badge-pricing">{tool.pricing}</span>
                    </div>
                  </div>

                  <button className="upvote-btn" onClick={() => handleUpvote(tool.id)}>
                    <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                    <span>{tool.upvotes}</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </main>
        
        <footer>
        </footer>
      </div>

      {showSubmitModal && (
        <div className="modal-overlay" onClick={() => setShowSubmitModal(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Submit a New Tool</h2>
              <button className="close-btn" onClick={() => setShowSubmitModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmitTool}>
              <div className="form-group">
                <label>Tool URL</label>
                <input 
                  type="url" 
                  className="form-input" 
                  placeholder="https://example.com"
                  value={submitUrl}
                  onChange={(e) => setSubmitUrl(e.target.value)}
                  required
                />
              </div>
              <button type="submit" className="submit-btn" disabled={submitLoading}>
                {submitLoading ? 'Submitting...' : 'Submit Tool'}
              </button>
              {submitMessage && <p className="submit-message">{submitMessage}</p>}
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default App
