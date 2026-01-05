import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatTime } from '../utils/formatTime'

interface HealthStatus {
  status: string
  queue?: {
    pending: number
    in_progress: number
    completed?: number
    failed?: number
  }
  llm?: {
    active_model: string | null
    active_backend: string | null
    active_preset: string | null
    primary_backend: string | null
    configured_preset: string | null
    fallback_model: string | null
  }
  last_run?: {
    total_cost: number
    total_tokens: number
  } | null
}

export default function StatusBar() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [expanded, setExpanded] = useState(false)

  const fetchHealth = async () => {
    try {
      const response = await fetch('/api/system/health')
      if (!response.ok) throw new Error('API unavailable')
      const data = await response.json()
      setHealth(data)
      setError(null)
      setLastUpdated(new Date())
    } catch {
      setError('API offline')
      setHealth(null)
    }
  }

  useEffect(() => {
    fetchHealth()
    const interval = setInterval(fetchHealth, 10000) // Poll every 10s
    return () => clearInterval(interval)
  }, [])

  const formatCost = (cost: number) => `$${cost.toFixed(4)}`
  const formatTokens = (tokens: number) => tokens.toLocaleString()

  // Calculate total queue items
  const queueTotal = health?.queue
    ? health.queue.pending + health.queue.in_progress
    : 0

  return (
    <div className="bg-gray-950 border-b border-gray-800 px-4 py-2">
      <div className="max-w-7xl mx-auto flex items-center justify-between text-xs">
        {/* Left: System Status + Queue Summary */}
        <div className="flex items-center space-x-4">
          <Link
            to="/system"
            className="flex items-center space-x-2 hover:bg-gray-800 px-2 py-1 rounded transition-colors"
            title="View system status and diagnostics"
          >
            <div
              className={`w-2 h-2 rounded-full ${
                error ? 'bg-red-500 animate-pulse' : 'bg-green-500'
              }`}
            />
            <span className={error ? 'text-red-400' : 'text-gray-300'}>
              {error ? 'Offline' : 'Connected'}
            </span>
          </Link>

          {/* Simplified Queue Display */}
          {health?.queue && (
            <Link
              to="/queue"
              className="flex items-center space-x-2 text-gray-300 hover:bg-gray-800 px-2 py-1 rounded transition-colors"
              title={`${health.queue.pending} pending, ${health.queue.in_progress} processing`}
            >
              <span className="text-yellow-400 font-medium">{queueTotal}</span>
              <span>in queue</span>
              {health.queue.in_progress > 0 && (
                <span className="text-blue-400 animate-pulse">●</span>
              )}
            </Link>
          )}
        </div>

        {/* Center: Expandable Details Toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center space-x-1 text-gray-400 hover:text-gray-200 px-2 py-1 rounded hover:bg-gray-800 transition-colors"
          aria-expanded={expanded}
          aria-label={expanded ? 'Hide system details' : 'Show system details'}
        >
          <span>{expanded ? 'Less' : 'More'}</span>
          <span className={`transform transition-transform ${expanded ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>

        {/* Right: Last Updated */}
        <div className="flex items-center text-gray-400">
          {lastUpdated && (
            <span title="Last health check">
              {formatTime(lastUpdated)}
            </span>
          )}
        </div>
      </div>

      {/* Expanded Details Panel */}
      {expanded && (
        <div className="max-w-7xl mx-auto mt-2 pt-2 border-t border-gray-800 flex items-center justify-between text-xs">
          {/* Queue Details */}
          {health?.queue && (
            <div className="flex items-center space-x-4 text-gray-300">
              <span>
                <span className="text-yellow-400">{health.queue.pending}</span> pending
              </span>
              <span>
                <span className="text-blue-400">{health.queue.in_progress}</span> processing
              </span>
              {health.queue.completed !== undefined && (
                <span>
                  <span className="text-green-400">{health.queue.completed}</span> completed
                </span>
              )}
              {health.queue.failed !== undefined && health.queue.failed > 0 && (
                <span>
                  <span className="text-red-400">{health.queue.failed}</span> failed
                </span>
              )}
            </div>
          )}

          {/* LLM Configuration */}
          {health?.llm && (
            <div className="flex items-center space-x-2 text-gray-300">
              <span>Backend:</span>
              <span className="text-cyan-400 font-mono">
                {health.llm.active_backend || health.llm.primary_backend || 'none'}
              </span>
              {health.llm.configured_preset && (
                <>
                  <span className="text-gray-500">|</span>
                  <span>Preset:</span>
                  <span className="text-purple-400 font-mono">
                    {health.llm.configured_preset}
                  </span>
                </>
              )}
            </div>
          )}

          {/* Last Run Stats */}
          {health?.last_run && (
            <div className="flex items-center space-x-3 text-gray-300">
              <span>
                Last run: <span className="text-green-400">{formatCost(health.last_run.total_cost)}</span>
              </span>
              <span>
                <span className="text-gray-300">{formatTokens(health.last_run.total_tokens)}</span> tokens
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
