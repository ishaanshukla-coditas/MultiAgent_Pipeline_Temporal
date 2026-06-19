const STATUS_CONFIG = {
  started: {
    label: 'Started',
    bg: 'bg-gray-100',
    text: 'text-gray-600',
    dot: 'bg-gray-400',
    pulse: false,
  },
  running_research_and_competitor: {
    label: 'Researching',
    bg: 'bg-blue-50',
    text: 'text-blue-700',
    dot: 'bg-blue-500',
    pulse: true,
  },
  writing_article: {
    label: 'Writing',
    bg: 'bg-purple-50',
    text: 'text-purple-700',
    dot: 'bg-purple-500',
    pulse: true,
  },
  waiting_for_approval: {
    label: 'Awaiting Approval',
    bg: 'bg-orange-50',
    text: 'text-orange-700',
    dot: 'bg-orange-500',
    pulse: false,
  },
  completed: {
    label: 'Completed',
    bg: 'bg-green-50',
    text: 'text-green-700',
    dot: 'bg-green-500',
    pulse: false,
  },
  rejected: {
    label: 'Rejected',
    bg: 'bg-red-50',
    text: 'text-red-700',
    dot: 'bg-red-500',
    pulse: false,
  },
  failed: {
    label: 'Failed',
    bg: 'bg-red-100',
    text: 'text-red-800',
    dot: 'bg-red-600',
    pulse: false,
  },
}

export default function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? {
    label: status,
    bg: 'bg-gray-100',
    text: 'text-gray-600',
    dot: 'bg-gray-400',
    pulse: false,
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot} ${cfg.pulse ? 'animate-pulse' : ''}`} />
      {cfg.label}
    </span>
  )
}
