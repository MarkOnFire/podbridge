import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

interface CompletedJob {
  id: number
  project_name: string
  project_path: string
  status: string
  completed_at: string
  actual_cost: number
  phases: Array<{
    name: string
    status: string
    cost: number
    tokens: number
  }>
}

interface ProjectArtifact {
  name: string
  path: string
  type: 'directory' | 'file'
  size?: number
  modified?: string
}

export default function Projects() {
  const [jobs, setJobs] = useState<CompletedJob[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedProject, setSelectedProject] = useState<CompletedJob | null>(null)
  const [artifacts, setArtifacts] = useState<ProjectArtifact[]>([])
  const [loadingArtifacts, setLoadingArtifacts] = useState(false)

  useEffect(() => {
    const fetchCompletedJobs = async () => {
      try {
        const response = await fetch('/api/queue/?status=completed')
        if (response.ok) {
          const data = await response.json()
          setJobs(Array.isArray(data) ? data : [])
        }
      } catch (err) {
        console.error('Failed to fetch completed jobs:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchCompletedJobs()
  }, [])

  const selectProject = async (job: CompletedJob) => {
    setSelectedProject(job)
    setLoadingArtifacts(true)

    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(job.project_name)}/files`)
      if (response.ok) {
        const data = await response.json()
        setArtifacts(data.files || [])
      } else {
        // Fallback: show expected artifacts based on phases
        setArtifacts(getExpectedArtifacts(job))
      }
    } catch {
      setArtifacts(getExpectedArtifacts(job))
    } finally {
      setLoadingArtifacts(false)
    }
  }

  const getExpectedArtifacts = (job: CompletedJob): ProjectArtifact[] => {
    // Generate expected artifacts based on completed phases
    const artifacts: ProjectArtifact[] = []
    const basePath = job.project_path

    job.phases?.forEach(phase => {
      if (phase.status === 'completed') {
        switch (phase.name) {
          case 'analyst':
            artifacts.push({
              name: 'analysis.md',
              path: `${basePath}/analysis.md`,
              type: 'file'
            })
            break
          case 'formatter':
            artifacts.push({
              name: 'formatted_transcript.md',
              path: `${basePath}/formatted_transcript.md`,
              type: 'file'
            })
            break
          case 'seo':
            artifacts.push({
              name: 'seo_metadata.json',
              path: `${basePath}/seo_metadata.json`,
              type: 'file'
            })
            break
          case 'copy_editor':
            artifacts.push({
              name: 'copy_edited.md',
              path: `${basePath}/copy_edited.md`,
              type: 'file'
            })
            break
        }
      }
    })

    // Always include manifest if job completed
    if (job.status === 'completed') {
      artifacts.unshift({
        name: 'manifest.json',
        path: `${basePath}/manifest.json`,
        type: 'file'
      })
    }

    return artifacts
  }

  const formatCost = (cost: number) => `$${cost.toFixed(4)}`
  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString()

  const getPhaseIcon = (status: string) => {
    switch (status) {
      case 'completed': return <span className="text-green-400">✓</span>
      case 'failed': return <span className="text-red-400">✗</span>
      case 'in_progress': return <span className="text-blue-400 animate-pulse">●</span>
      default: return <span className="text-gray-500">○</span>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading projects...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Completed Projects</h1>
        <span className="text-gray-400 text-sm">{jobs.length} projects</span>
      </div>

      {jobs.length === 0 ? (
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
          <p className="text-gray-400">No completed projects yet.</p>
          <p className="text-gray-500 text-sm mt-2">
            Projects will appear here once jobs finish processing.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Project List */}
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
              Projects
            </h2>
            <div className="space-y-2">
              {jobs.map(job => (
                <button
                  key={job.id}
                  onClick={() => selectProject(job)}
                  className={`w-full text-left p-4 rounded-lg border transition-colors ${
                    selectedProject?.id === job.id
                      ? 'bg-blue-900/30 border-blue-500/50'
                      : 'bg-gray-800 border-gray-700 hover:border-gray-600'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-white">{job.project_name}</div>
                      <div className="text-sm text-gray-500">
                        {job.completed_at ? formatDate(job.completed_at) : 'Processing...'}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-green-400 font-mono text-sm">
                        {formatCost(job.actual_cost || 0)}
                      </div>
                      <div className="text-xs text-gray-500">total cost</div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Project Details */}
          <div className="space-y-4">
            {selectedProject ? (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                    Project Details
                  </h2>
                  <Link
                    to={`/jobs/${selectedProject.id}`}
                    className="text-sm text-blue-400 hover:text-blue-300"
                  >
                    View full job →
                  </Link>
                </div>

                {/* Phase Stats */}
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-3">
                    Agent Phases
                  </h3>
                  <div className="space-y-2">
                    {selectedProject.phases?.map((phase, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0"
                      >
                        <div className="flex items-center space-x-3">
                          {getPhaseIcon(phase.status)}
                          <span className="text-white capitalize">{phase.name}</span>
                        </div>
                        <div className="flex items-center space-x-4 text-sm">
                          <span className="text-green-400 font-mono">
                            {formatCost(phase.cost || 0)}
                          </span>
                          <span className="text-gray-500">
                            {(phase.tokens || 0).toLocaleString()} tokens
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Artifacts */}
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-3">
                    Artifacts
                  </h3>
                  {loadingArtifacts ? (
                    <div className="text-gray-500 text-sm">Loading artifacts...</div>
                  ) : artifacts.length === 0 ? (
                    <div className="text-gray-500 text-sm">No artifacts found</div>
                  ) : (
                    <div className="space-y-1">
                      {artifacts.map((artifact, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2 px-3 rounded hover:bg-gray-700/50"
                        >
                          <div className="flex items-center space-x-3">
                            <span className="text-gray-400">
                              {artifact.type === 'directory' ? '📁' : '📄'}
                            </span>
                            <span className="text-white font-mono text-sm">
                              {artifact.name}
                            </span>
                          </div>
                          <a
                            href={`/api/projects/${encodeURIComponent(selectedProject.project_name)}/files/${encodeURIComponent(artifact.name)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 text-sm"
                          >
                            Open →
                          </a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Project Path */}
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                  <h3 className="text-sm font-medium text-gray-400 mb-2">
                    Output Location
                  </h3>
                  <code className="text-sm text-emerald-400 font-mono break-all">
                    {selectedProject.project_path}
                  </code>
                </div>
              </>
            ) : (
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
                <p className="text-gray-500">
                  Select a project to view details and artifacts
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
