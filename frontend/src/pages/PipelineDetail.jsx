import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2, CheckCircle, XCircle, FileText, AlertCircle, Hash, AlertTriangle } from 'lucide-react'
import { getPipeline, approvePipeline, rejectPipeline } from '../api/pipelines.js'
import StatusBadge from '../components/StatusBadge.jsx'
import AgentProgress from '../components/AgentProgress.jsx'

const TERMINAL_STATUSES = ['completed', 'rejected', 'failed']
const SHOW_PROGRESS_STATUSES = ['started', 'running_research_and_competitor', 'writing_article', 'failed']
const SHOW_ARTICLE_STATUSES = ['writing_article', 'waiting_for_approval', 'completed', 'rejected']

function ArticleContent({ content }) {
  if (!content) return null
  const paragraphs = content.split('\n').filter(line => line.trim())
  return (
    <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed space-y-3">
      {paragraphs.map((para, i) => {
        if (para.startsWith('# ')) return <h1 key={i} className="text-xl font-bold text-gray-900 mt-4">{para.slice(2)}</h1>
        if (para.startsWith('## ')) return <h2 key={i} className="text-lg font-semibold text-gray-800 mt-3">{para.slice(3)}</h2>
        if (para.startsWith('### ')) return <h3 key={i} className="text-base font-semibold text-gray-800 mt-2">{para.slice(4)}</h3>
        if (para.startsWith('- ') || para.startsWith('* ')) return (
          <li key={i} className="ml-4 list-disc text-sm">{para.slice(2)}</li>
        )
        if (para.startsWith('**') && para.endsWith('**')) return (
          <p key={i} className="font-semibold text-gray-900 text-sm">{para.slice(2, -2)}</p>
        )
        return <p key={i} className="text-sm">{para}</p>
      })}
    </div>
  )
}

export default function PipelineDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [pipeline, setPipeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [feedback, setFeedback] = useState('')
  const [acting, setActing] = useState(false)
  const [actionError, setActionError] = useState(null)
  const intervalRef = useRef(null)

  const fetchPipeline = async () => {
    try {
      const data = await getPipeline(id)
      setPipeline(data)
      if (TERMINAL_STATUSES.includes(data.status)) {
        clearInterval(intervalRef.current)
      }
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Pipeline not found')
      clearInterval(intervalRef.current)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPipeline()
    intervalRef.current = setInterval(fetchPipeline, 2000)
    return () => clearInterval(intervalRef.current)
  }, [id])

  const handleApprove = async () => {
    setActing(true)
    setActionError(null)
    try {
      await approvePipeline(id)
      clearInterval(intervalRef.current)
      await fetchPipeline()
    } catch (err) {
      setActionError(err.response?.data?.detail ?? 'Failed to approve')
    } finally {
      setActing(false)
    }
  }

  const handleReject = async () => {
    if (!feedback.trim()) return
    setActing(true)
    setActionError(null)
    try {
      await rejectPipeline(id, feedback.trim())
      clearInterval(intervalRef.current)
      await fetchPipeline()
    } catch (err) {
      setActionError(err.response?.data?.detail ?? 'Failed to reject')
    } finally {
      setActing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <Loader2 size={32} className="animate-spin text-blue-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 gap-4">
        <AlertCircle size={40} className="text-red-400" />
        <p className="text-gray-600 font-medium">{error}</p>
        <button onClick={() => navigate('/')} className="text-blue-600 text-sm hover:underline">
          Back to Dashboard
        </button>
      </div>
    )
  }

  const showProgress = SHOW_PROGRESS_STATUSES.includes(pipeline.status) || pipeline.status === 'waiting_for_approval'
  const showArticle = SHOW_ARTICLE_STATUSES.includes(pipeline.status)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-6 py-8 flex flex-col gap-6">

        {/* Header */}
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 transition-colors mb-4"
          >
            <ArrowLeft size={16} />
            Back to Dashboard
          </button>

          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Hash size={14} className="text-gray-400" />
                <span className="font-mono text-xs text-gray-400">{pipeline.pipeline_id}</span>
              </div>
              <h1 className="text-xl font-bold text-gray-900 leading-snug">{pipeline.topic}</h1>
              <p className="text-xs text-gray-400 font-mono mt-2">
                Workflow: {pipeline.temporal_workflow_id}
              </p>
            </div>
            <StatusBadge status={pipeline.status} />
          </div>
        </div>

        {/* Agent Progress */}
        {showProgress && (
          <AgentProgress
            status={pipeline.status}
            simulateFailure={pipeline.simulate_writer_failure}
          />
        )}

        {/* Article Preview */}
        {showArticle && pipeline.title && (
          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex items-start justify-between gap-4 mb-4 pb-4 border-b border-gray-100">
              <div>
                <h2 className="text-lg font-bold text-gray-900">{pipeline.title}</h2>
                {pipeline.meta_description && (
                  <p className="text-sm text-gray-500 mt-1 italic">{pipeline.meta_description}</p>
                )}
              </div>
              {pipeline.word_count && (
                <span className="flex-shrink-0 inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 bg-gray-100 px-3 py-1.5 rounded-full">
                  <FileText size={12} />
                  {pipeline.word_count.toLocaleString()} words
                </span>
              )}
            </div>
            <ArticleContent content={pipeline.content} />
          </div>
        )}

        {/* Approval Panel */}
        {pipeline.status === 'waiting_for_approval' && (
          <div className="bg-white border border-orange-200 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-2 h-2 rounded-full bg-orange-500" />
              <h2 className="font-semibold text-gray-900">Article Ready for Review</h2>
            </div>

            {actionError && (
              <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mb-4">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                {actionError}
              </div>
            )}

            <div className="flex flex-col gap-4">
              {/* Approve */}
              <button
                onClick={handleApprove}
                disabled={acting}
                className="flex items-center justify-center gap-2 w-full bg-green-600 text-white font-medium py-3 rounded-xl hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {acting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
                Approve & Publish
              </button>

              {/* Reject */}
              <div className="border border-gray-200 rounded-xl p-4">
                <p className="text-sm font-medium text-gray-700 mb-2">Request Changes</p>
                <textarea
                  value={feedback}
                  onChange={e => setFeedback(e.target.value)}
                  placeholder="Describe what needs to be changed..."
                  rows={3}
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent mb-3"
                />
                <button
                  onClick={handleReject}
                  disabled={acting || !feedback.trim()}
                  className="flex items-center justify-center gap-2 w-full bg-red-50 text-red-700 border border-red-200 font-medium py-2.5 rounded-xl hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  {acting ? <Loader2 size={14} className="animate-spin" /> : <XCircle size={14} />}
                  Reject & Request Revision
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Final State */}
        {pipeline.status === 'completed' && (
          <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl px-6 py-4">
            <CheckCircle size={20} className="text-green-600 flex-shrink-0" />
            <div>
              <p className="font-semibold text-green-800">Article Published</p>
              <p className="text-sm text-green-600">
                {pipeline.word_count?.toLocaleString()} words · Approved and completed
              </p>
            </div>
          </div>
        )}

        {pipeline.status === 'rejected' && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-6 py-4">
            <XCircle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-800">Article Rejected</p>
              <p className="text-sm text-red-600 mt-0.5">Revision has been requested.</p>
            </div>
          </div>
        )}

        {pipeline.status === 'failed' && (
          <div className="flex items-start gap-3 bg-red-50 border border-red-300 rounded-xl px-6 py-4">
            <AlertTriangle size={20} className="text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-red-800">Workflow Failed</p>
              <p className="text-sm text-red-600 mt-0.5">
                All retry attempts were exhausted. Check the{' '}
                <a
                  href={`http://localhost:8233/namespaces/default/workflows/${pipeline.temporal_workflow_id}`}
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-red-800"
                >
                  Temporal UI
                </a>
                {' '}for the full failure trace.
              </p>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
