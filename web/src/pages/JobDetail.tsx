import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

interface JobPhase {
  name: string
  status: string
  cost?: number
  tokens?: number
  started_at?: string
  completed_at?: string
}

interface JobDetail {
  id: number
  transcript_name: string
  status: string
  priority: number
  created_at: string
  updated_at: string
  last_heartbeat?: string
  retry_count: number
  max_retries: number
  phases?: JobPhase[]
  total_cost?: number
  total_tokens?: number
  error_message?: string
}

export default function JobDetail() {
  const { id } = useParams()
  const [job, setJob] = useState<JobDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const response = await fetch(`/api/jobs/${id}`)
        if (!response.ok) {
          throw new Error('Job not found')
        }
        setJob(await response.json())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load job')
      } finally {
        setLoading(false)
      }
    }

    fetchJob()
  }, [id])

  const handleAction = async (action: string) => {
    try {
      const response = await fetch(`/api/jobs/${id}/${action}`, {
        method: 'POST',
      })
      if (response.ok) {
        // Refresh job data
        const updated = await fetch(`/api/jobs/${id}`)
        if (updated.ok) {
          setJob(await updated.json())
        }
      }
    } catch (err) {
      console.error(`Failed to ${action} job:`, err)
    }
  }

  const phaseStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="text-green-400">&#10003;</span>
      case 'in_progress':
        return <span className="text-blue-400 animate-pulse">&#9679;</span>
      case 'failed':
        return <span className="text-red-400">&#10007;</span>
      case 'skipped':
        return <span className="text-gray-500">&#8212;</span>
      default:
        return <span className="text-gray-600">&#9675;</span>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error || !job) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 mb-4">{error || 'Job not found'}</div>
        <Link to="/queue" className="text-blue-400 hover:text-blue-300">
          Back to queue
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link
            to="/queue"
            className="text-sm text-gray-400 hover:text-white mb-2 inline-block"
          >
            &#8592; Back to queue
          </Link>
          <h1 className="text-2xl font-bold text-white">
            {job.transcript_name}
          </h1>
          <p className="text-gray-500">Job #{job.id}</p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          {job.status === 'in_progress' && (
            <button
              onClick={() => handleAction('pause')}
              className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded-md text-sm"
            >
              Pause
            </button>
          )}
          {job.status === 'paused' && (
            <button
              onClick={() => handleAction('resume')}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-md text-sm"
            >
              Resume
            </button>
          )}
          {job.status === 'failed' && (
            <button
              onClick={() => handleAction('retry')}
              className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-white rounded-md text-sm"
            >
              Retry
            </button>
          )}
          {['pending', 'paused'].includes(job.status) && (
            <button
              onClick={() => handleAction('cancel')}
              className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white rounded-md text-sm"
            >
              Cancel
            </button>
          )}
        </div>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCard label="Status" value={job.status} />
        <InfoCard label="Priority" value={String(job.priority)} />
        <InfoCard
          label="Cost"
          value={job.total_cost ? `$${job.total_cost.toFixed(4)}` : '-'}
        />
        <InfoCard
          label="Tokens"
          value={job.total_tokens?.toLocaleString() ?? '-'}
        />
      </div>

      {/* Phases */}
      {job.phases && job.phases.length > 0 && (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
          <h2 className="text-lg font-medium text-white mb-4">
            Processing Phases
          </h2>
          <div className="space-y-3">
            {job.phases.map((phase, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0"
              >
                <div className="flex items-center space-x-3">
                  {phaseStatusIcon(phase.status)}
                  <span className="text-white">{phase.name}</span>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-400">
                  {phase.cost !== undefined && (
                    <span>${phase.cost.toFixed(4)}</span>
                  )}
                  {phase.tokens !== undefined && (
                    <span>{phase.tokens.toLocaleString()} tokens</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Message */}
      {job.error_message && (
        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
          <h3 className="text-red-400 font-medium mb-2">Error</h3>
          <pre className="text-sm text-red-300 whitespace-pre-wrap">
            {job.error_message}
          </pre>
        </div>
      )}

      {/* Timestamps */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h2 className="text-lg font-medium text-white mb-4">Timeline</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Created:</span>
            <span className="ml-2 text-white">
              {new Date(job.created_at).toLocaleString()}
            </span>
          </div>
          <div>
            <span className="text-gray-400">Updated:</span>
            <span className="ml-2 text-white">
              {new Date(job.updated_at).toLocaleString()}
            </span>
          </div>
          {job.last_heartbeat && (
            <div>
              <span className="text-gray-400">Last heartbeat:</span>
              <span className="ml-2 text-white">
                {new Date(job.last_heartbeat).toLocaleString()}
              </span>
            </div>
          )}
          <div>
            <span className="text-gray-400">Retries:</span>
            <span className="ml-2 text-white">
              {job.retry_count} / {job.max_retries}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
      <div className="text-xs text-gray-400 uppercase tracking-wide">
        {label}
      </div>
      <div className="text-lg font-medium text-white mt-1">{value}</div>
    </div>
  )
}
