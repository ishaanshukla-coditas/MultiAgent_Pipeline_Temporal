import { Search, TrendingUp, PenLine, Check } from 'lucide-react'

// SEO is now merged into the Writer agent (1 LLM call instead of 3+2)
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

function getStepStatuses(status) {
  switch (status) {
    case 'started':
      return ['pending', 'pending', 'pending']
    case 'running_research_and_competitor':
      return ['running', 'running', 'pending']
    case 'writing_article':
      return ['done', 'done', 'running']
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
  return (
    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
      <div className="w-3 h-3 rounded-full bg-gray-300" />
    </div>
  )
}

export default function AgentProgress({ status }) {
  const statuses = getStepStatuses(status)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Agent Progress</h2>
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-1 rounded-full">3 LLM calls</span>
      </div>
      <div className="flex flex-col gap-4">
        {STEPS.map((step, i) => {
          const stepStatus = statuses[i]
          const { Icon } = step
          return (
            <div key={step.key} className="flex items-center gap-4">
              <StepIndicator stepStatus={stepStatus} />
              <div className="flex items-center gap-3 flex-1">
                <div className={`p-2 rounded-lg ${
                  stepStatus === 'done' ? 'bg-green-50' :
                  stepStatus === 'running' ? 'bg-blue-50' :
                  'bg-gray-50'
                }`}>
                  <Icon size={16} className={
                    stepStatus === 'done' ? 'text-green-600' :
                    stepStatus === 'running' ? 'text-blue-600' :
                    'text-gray-400'
                  } />
                </div>
                <div>
                  <p className={`text-sm font-medium ${stepStatus === 'pending' ? 'text-gray-400' : 'text-gray-900'}`}>
                    {step.label}
                  </p>
                  <p className="text-xs text-gray-400">{step.description}</p>
                </div>
              </div>
              <span className={`text-xs font-medium capitalize px-2 py-0.5 rounded-full ${
                stepStatus === 'done' ? 'bg-green-100 text-green-700' :
                stepStatus === 'running' ? 'bg-blue-100 text-blue-700' :
                'bg-gray-100 text-gray-400'
              }`}>
                {stepStatus}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
