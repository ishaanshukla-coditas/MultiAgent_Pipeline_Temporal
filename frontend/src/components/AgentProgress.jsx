import { Search, TrendingUp, PenLine, Check, RefreshCw, FlaskConical, X } from 'lucide-react'

const STEPS = [
  {
    key: 'research',
    label: 'Research Agent',
    description: 'Web search + fact synthesis',
    Icon: Search,
  },
  {
    key: 'competitor',
    label: 'Competitor Agent',
    description: 'Content gap analysis',
    Icon: TrendingUp,
  },
  {
    key: 'writer',
    label: 'SEO + Writer Agent',
    description: 'Keyword strategy + full article',
    Icon: PenLine,
  },
]

function getStepStatuses(status, simulateFailure) {
  switch (status) {
    case 'started':
      return ['pending', 'pending', 'pending']
    case 'running_research_and_competitor':
      return ['running', 'running', 'pending']
    case 'writing_article':
      return ['done', 'done', simulateFailure ? 'retrying' : 'running']
    case 'failed':
      return ['failed', 'failed', 'failed']
    default: // waiting_for_approval, completed, rejected
      return ['done', 'done', 'done']
  }
}

function StepIndicator({ stepStatus }) {
  if (stepStatus === 'done') {
    return (
      <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
        <Check size={16} className="text-green-600" />
      </div>
    )
  }
  if (stepStatus === 'running') {
    return (
      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
        <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
      </div>
    )
  }
  if (stepStatus === 'retrying') {
    return (
      <div className="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
        <RefreshCw size={14} className="text-amber-600 animate-spin" />
      </div>
    )
  }
  if (stepStatus === 'failed') {
    return (
      <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
        <X size={15} className="text-red-600" />
      </div>
    )
  }
  return (
    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
      <div className="w-3 h-3 rounded-full bg-gray-300" />
    </div>
  )
}

function StatusPill({ stepStatus }) {
  if (stepStatus === 'done') return (
    <span className="text-xs font-medium capitalize px-2 py-0.5 rounded-full bg-green-100 text-green-700">done</span>
  )
  if (stepStatus === 'running') return (
    <span className="text-xs font-medium capitalize px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">running</span>
  )
  if (stepStatus === 'retrying') return (
    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">retrying</span>
  )
  if (stepStatus === 'failed') return (
    <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">failed</span>
  )
  return (
    <span className="text-xs font-medium capitalize px-2 py-0.5 rounded-full bg-gray-100 text-gray-400">pending</span>
  )
}

export default function AgentProgress({ status, simulateFailure = false }) {
  const statuses = getStepStatuses(status, simulateFailure)
  const isRetrying = statuses.includes('retrying')

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Agent Progress</h2>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">3 LLM calls</span>
      </div>

      {/* Failure simulation banner */}
      {simulateFailure && (
        <div className={`flex items-start gap-2.5 mb-4 px-3 py-2.5 rounded-lg border text-xs ${
          isRetrying
            ? 'bg-amber-50 border-amber-200 text-amber-800'
            : 'bg-green-50 border-green-200 text-green-800'
        }`}>
          <FlaskConical size={13} className={`mt-0.5 flex-shrink-0 ${isRetrying ? 'text-amber-500' : 'text-green-500'}`} />
          <div>
            {isRetrying ? (
              <>
                <span className="font-semibold">Writer failed on attempt 1</span>
                <span className="text-amber-600"> · Temporal is retrying automatically. Research &amp; competitor results are cached — not re-run.</span>
              </>
            ) : (
              <>
                <span className="font-semibold">Writer recovered on attempt 2</span>
                <span className="text-green-700"> · Research &amp; competitor were served from event history.</span>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {STEPS.map((step, i) => {
          const stepStatus = statuses[i]
          const { Icon } = step
          const isCached = simulateFailure && stepStatus === 'done' && i < 2 && isRetrying

          return (
            <div key={step.key} className="flex items-center gap-4">
              <StepIndicator stepStatus={stepStatus} />
              <div className="flex items-center gap-3 flex-1">
                <div className={`p-2 rounded-lg ${
                  stepStatus === 'done' ? 'bg-green-50' :
                  stepStatus === 'running' ? 'bg-blue-50' :
                  stepStatus === 'retrying' ? 'bg-amber-50' :
                  stepStatus === 'failed' ? 'bg-red-50' :
                  'bg-gray-50'
                }`}>
                  <Icon size={16} className={
                    stepStatus === 'done' ? 'text-green-600' :
                    stepStatus === 'running' ? 'text-blue-600' :
                    stepStatus === 'retrying' ? 'text-amber-600' :
                    stepStatus === 'failed' ? 'text-red-500' :
                    'text-gray-400'
                  } />
                </div>
                <div>
                  <p className={`text-sm font-medium ${stepStatus === 'pending' ? 'text-gray-400' : 'text-gray-900'}`}>
                    {step.label}
                  </p>
                  <p className="text-xs text-gray-400">
                    {stepStatus === 'retrying'
                      ? 'Attempt 1 failed · retrying now'
                      : stepStatus === 'failed'
                      ? 'All retry attempts exhausted'
                      : step.description}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                {isCached && (
                  <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-50 text-blue-500 border border-blue-100">
                    cached
                  </span>
                )}
                <StatusPill stepStatus={stepStatus} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
