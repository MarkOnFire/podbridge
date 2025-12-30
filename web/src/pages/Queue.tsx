import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface Job {
  id: number
  project_name: string
  transcript_file: string
  status: string
  priority: number
  queued_at: string
  current_phase: string | null
}

export default function Queue() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [loading, setLoading] = useState(true)

  const handlePrioritize = async (jobId: number) => {
    try {
      // Find max priority and set this job higher
      const maxPriority = Math.max(...jobs.map(j => j.priority), 0)
      await fetch(`/api/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priority: maxPriority + 10 })
      })
      fetchJobs() // Refresh
    } catch (err) {
      console.error('Failed to prioritize job:', err)
    }
  }

  const handleCancel = async (jobId: number) => {
    if (!confirm('Are you sure you want to cancel this job?')) return
    try {
      await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
      fetchJobs() // Refresh
    } catch (err) {
      console.error('Failed to cancel job:', err)
    }
  }

  const fetchJobs = async () => {
    try {
      // Note: filter=all means no status filter, omit parameter entirely
      const url = filter === 'all' ? '/api/queue/' : `/api/queue/?status=${filter}`
      const response = await fetch(url)
      if (response.ok) {
        const data = await response.json()
        setJobs(Array.isArray(data) ? data : [])
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [filter])

  const statusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'in_progress':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'completed':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'paused':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Job Queue</h1>

        {/* Filter Tabs */}
        <div className="flex items-center space-x-1 bg-gray-800 rounded-lg p-1">
          {['all', 'pending', 'in_progress', 'completed', 'failed'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                filter === status
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {status === 'all' ? 'All' : status.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        {loading ? (
          <div className="px-4 py-8 text-center text-gray-500">Loading...</div>
        ) : jobs.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500">
            No jobs found
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-850 border-b border-gray-700">
              <tr className="text-left text-sm text-gray-400">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Transcript</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Phase</th>
                <th className="px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3 font-medium">Priority</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {jobs.map((job) => (
                <tr
                  key={job.id}
                  className="hover:bg-gray-750 transition-colors"
                >
                  <td className="px-4 py-3">
                    <Link
                      to={`/jobs/${job.id}`}
                      className="text-blue-400 hover:text-blue-300"
                    >
                      #{job.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 font-medium text-white">
                    {job.project_name}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${statusColor(
                        job.status
                      )}`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">
                    {job.current_phase || '-'}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">
                    {new Date(job.queued_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">
                    {job.priority}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center space-x-2">
                      {job.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handlePrioritize(job.id)}
                            className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors"
                            title="Move to top of queue"
                          >
                            ↑ Prioritize
                          </button>
                          <button
                            onClick={() => handleCancel(job.id)}
                            className="px-2 py-1 text-xs bg-red-600/50 hover:bg-red-600 text-red-100 rounded transition-colors"
                            title="Cancel job"
                          >
                            Cancel
                          </button>
                        </>
                      )}
                      {job.status === 'in_progress' && (
                        <span className="text-xs text-gray-500">Processing...</span>
                      )}
                      {['completed', 'failed', 'cancelled'].includes(job.status) && (
                        <Link
                          to={`/jobs/${job.id}`}
                          className="text-xs text-gray-400 hover:text-white"
                        >
                          View details
                        </Link>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
