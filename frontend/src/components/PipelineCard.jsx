import { useNavigate } from 'react-router-dom'
import { FileText, Hash } from 'lucide-react'
import StatusBadge from './StatusBadge.jsx'

export default function PipelineCard({ pipeline }) {
  const navigate = useNavigate()

  const createdAt = new Date(pipeline.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div
      onClick={() => navigate(`/pipelines/${pipeline.pipeline_id}`)}
      className="bg-white border border-gray-200 rounded-xl p-5 cursor-pointer transition-all duration-150 hover:shadow-md hover:border-blue-300 flex flex-col gap-3"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-mono text-xs text-gray-400">#{pipeline.pipeline_id}</span>
        <StatusBadge status={pipeline.status} />
      </div>

      <div>
        <p className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2">
          {pipeline.topic}
        </p>
        {pipeline.title && (
          <p className="mt-1 text-blue-600 text-xs italic line-clamp-1">{pipeline.title}</p>
        )}
      </div>

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-100">
        {pipeline.word_count ? (
          <span className="inline-flex items-center gap-1 text-xs text-gray-500">
            <FileText size={12} />
            {pipeline.word_count.toLocaleString()} words
          </span>
        ) : (
          <span />
        )}
        <span className="text-xs text-gray-400">{createdAt}</span>
      </div>
    </div>
  )
}
