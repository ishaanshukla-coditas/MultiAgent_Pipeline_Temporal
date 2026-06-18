import { useState, useEffect, useRef } from 'react'
import { Zap, Loader2, AlertCircle, LayoutDashboard } from 'lucide-react'
import { createPipeline, listPipelines } from '../api/pipelines.js'
import PipelineCard from '../components/PipelineCard.jsx'

const SUGGESTIONS = [
  'AI Agents in production 2025',
  'The future of remote work',
  'Sustainable tech startups in 2026',
]

export default function Dashboard() {
  const [topic, setTopic] = useState('')
  const [pipelines, setPipelines] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  const fetchPipelines = async () => {
    try {
      const data = await listPipelines()
      setPipelines(data)
    } catch {
      // silently fail on background refresh
    }
  }

  useEffect(() => {
    fetchPipelines()
    intervalRef.current = setInterval(fetchPipelines, 3000)
    return () => clearInterval(intervalRef.current)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!topic.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await createPipeline(topic.trim())
      setTopic('')
      await fetchPipelines()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to start pipeline. Is the backend running?')
    } finally {
      setSubmitting(false)
    }
  }

  const running = pipelines.filter(p =>
    !['completed', 'rejected'].includes(p.status)
  ).length

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-80 flex-shrink-0 bg-white border-r border-gray-200 p-6 flex flex-col gap-6 sticky top-0 h-screen overflow-y-auto">
        {/* Brand */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 text-sm leading-tight">Content Pipeline</p>
            <p className="text-xs text-gray-400">Multi-Agent AI</p>
          </div>
        </div>

        {/* New Pipeline Form */}
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">New Pipeline</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <textarea
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="Enter a topic to research and write about..."
              rows={3}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
            />
            {error && (
              <div className="flex items-start gap-2 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                <AlertCircle size={12} className="mt-0.5 flex-shrink-0" />
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={submitting || !topic.trim()}
              className="w-full bg-blue-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Starting...
                </>
              ) : (
                'Start Pipeline'
              )}
            </button>
          </form>
        </div>

        {/* Quick suggestions */}
        <div>
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-2">Quick Topics</p>
          <div className="flex flex-col gap-1.5">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={() => setTopic(s)}
                className="text-left text-xs text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div className="mt-auto grid grid-cols-2 gap-3">
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-gray-900">{pipelines.length}</p>
            <p className="text-xs text-gray-500 mt-0.5">Total</p>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-center">
            <p className="text-2xl font-bold text-blue-700">{running}</p>
            <p className="text-xs text-blue-500 mt-0.5">Running</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-8">
        <div className="flex items-center gap-2 mb-6">
          <LayoutDashboard size={20} className="text-gray-400" />
          <h1 className="text-xl font-semibold text-gray-900">All Pipelines</h1>
        </div>

        {pipelines.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
              <Zap size={28} className="text-gray-300" />
            </div>
            <p className="text-gray-500 font-medium">No pipelines yet</p>
            <p className="text-gray-400 text-sm mt-1">Enter a topic on the left to get started</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {pipelines.map(p => (
              <PipelineCard key={p.pipeline_id} pipeline={p} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
