import { useEffect, useState, useCallback } from 'react'

interface DurationThreshold {
  max_minutes: number | null
  tier: number
}

interface EscalationConfig {
  enabled: boolean
  on_failure: boolean
  on_timeout: boolean
  timeout_seconds: number
  max_retries_per_tier: number
}

interface RoutingConfig {
  tiers: string[]
  tier_labels: string[]
  duration_thresholds: DurationThreshold[]
  phase_base_tiers: Record<string, number>
  escalation: EscalationConfig
}

interface WorkerConfig {
  max_concurrent_jobs: number
  poll_interval_seconds: number
  heartbeat_interval_seconds: number
}

interface AgentInfo {
  id: string
  name: string
  icon: string
  description: string
}

const AGENT_INFO: AgentInfo[] = [
  {
    id: 'analyst',
    name: 'Analyst',
    icon: '🔍',
    description: 'Analyzes transcripts to identify key topics, themes, speakers and structural elements.'
  },
  {
    id: 'formatter',
    name: 'Formatter',
    icon: '📝',
    description: 'Transforms raw transcripts into clean, readable markdown with proper structure.'
  },
  {
    id: 'seo',
    name: 'SEO Specialist',
    icon: '🎯',
    description: 'Generates search-optimized metadata for streaming platform discovery.'
  },
  {
    id: 'manager',
    name: 'QA Manager',
    icon: '✅',
    description: 'Reviews all outputs for quality. Always runs on big-brain tier for accurate oversight.'
  },
  {
    id: 'copy_editor',
    name: 'Copy Editor',
    icon: '✏️',
    description: 'Reviews and refines content for clarity, grammar and PBS style guidelines.'
  }
]

const TIER_COLORS = ['green', 'cyan', 'purple'] as const
const TIER_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  green: { bg: 'bg-green-900/20', border: 'border-green-500/30', text: 'text-green-400' },
  cyan: { bg: 'bg-cyan-900/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
  purple: { bg: 'bg-purple-900/20', border: 'border-purple-500/30', text: 'text-purple-400' },
}

type TabId = 'agents' | 'routing' | 'worker'

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'routing', label: 'Routing', icon: '🔀' },
  { id: 'worker', label: 'Worker', icon: '⚙️' },
]

export default function Settings() {
  const [routing, setRouting] = useState<RoutingConfig | null>(null)
  const [worker, setWorker] = useState<WorkerConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('agents')

  // Track unsaved changes
  const [pendingRouting, setPendingRouting] = useState<Partial<RoutingConfig> | null>(null)
  const [pendingWorker, setPendingWorker] = useState<Partial<WorkerConfig> | null>(null)

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true)
      const [routingRes, workerRes] = await Promise.all([
        fetch('/api/config/routing'),
        fetch('/api/config/worker')
      ])

      if (!routingRes.ok) {
        throw new Error('Failed to fetch routing configuration')
      }
      if (!workerRes.ok) {
        throw new Error('Failed to fetch worker configuration')
      }

      const routingData = await routingRes.json()
      const workerData = await workerRes.json()
      setRouting(routingData)
      setWorker(workerData)
      setPendingRouting(null)
      setPendingWorker(null)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  const handlePhaseBaseTierChange = (phase: string, tier: number) => {
    const current = pendingRouting?.phase_base_tiers || routing?.phase_base_tiers || {}
    setPendingRouting({
      ...pendingRouting,
      phase_base_tiers: { ...current, [phase]: tier }
    })
  }

  const handleThresholdChange = (index: number, value: number | null) => {
    const current = pendingRouting?.duration_thresholds || routing?.duration_thresholds || []
    const updated = [...current]
    updated[index] = { ...updated[index], max_minutes: value }
    setPendingRouting({ ...pendingRouting, duration_thresholds: updated })
  }

  const handleEscalationChange = (key: keyof EscalationConfig, value: boolean | number) => {
    const current = pendingRouting?.escalation || routing?.escalation || {
      enabled: true, on_failure: true, on_timeout: true, timeout_seconds: 120, max_retries_per_tier: 1
    }
    setPendingRouting({
      ...pendingRouting,
      escalation: { ...current, [key]: value }
    })
  }

  const handleWorkerChange = (key: keyof WorkerConfig, value: number) => {
    setPendingWorker({
      ...pendingWorker,
      [key]: value
    })
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      // Save routing config if changed
      if (pendingRouting) {
        const res = await fetch('/api/config/routing', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pendingRouting)
        })
        if (!res.ok) {
          let detail = 'Failed to save routing config'
          try {
            const data = await res.json()
            detail = data.detail || detail
          } catch {
            // Response wasn't JSON
          }
          throw new Error(detail)
        }
      }

      // Save worker config if changed
      if (pendingWorker) {
        const res = await fetch('/api/config/worker', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(pendingWorker)
        })
        if (!res.ok) {
          let detail = 'Failed to save worker config'
          try {
            const data = await res.json()
            detail = data.detail || detail
          } catch {
            // Response wasn't JSON
          }
          throw new Error(detail)
        }
      }

      setSuccess('Settings saved successfully. Restart workers to apply changes.')
      await fetchConfig()
      setTimeout(() => setSuccess(null), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    setPendingRouting(null)
    setPendingWorker(null)
  }

  const hasChanges = pendingRouting !== null || pendingWorker !== null

  const getCurrentWorker = (): WorkerConfig => {
    return {
      max_concurrent_jobs: pendingWorker?.max_concurrent_jobs ?? worker?.max_concurrent_jobs ?? 3,
      poll_interval_seconds: pendingWorker?.poll_interval_seconds ?? worker?.poll_interval_seconds ?? 5,
      heartbeat_interval_seconds: pendingWorker?.heartbeat_interval_seconds ?? worker?.heartbeat_interval_seconds ?? 60
    }
  }

  const getCurrentPhaseBaseTier = (phase: string): number => {
    return pendingRouting?.phase_base_tiers?.[phase] ?? routing?.phase_base_tiers?.[phase] ?? 0
  }

  const getCurrentThresholds = (): DurationThreshold[] => {
    return pendingRouting?.duration_thresholds || routing?.duration_thresholds || []
  }

  const getCurrentEscalation = (): EscalationConfig => {
    return pendingRouting?.escalation || routing?.escalation || {
      enabled: true, on_failure: true, on_timeout: true, timeout_seconds: 120, max_retries_per_tier: 1
    }
  }

  const getTierLabel = (tier: number): string => {
    return routing?.tier_labels?.[tier] || `tier-${tier}`
  }

  const getTierColor = (tier: number): string => {
    return TIER_COLORS[tier] || 'cyan'
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
          <p className="text-gray-400 animate-pulse">Loading configuration...</p>
        </div>
      </div>
    )
  }

  // Toggle component for cleaner code
  const Toggle = ({ checked, onChange, label }: { checked: boolean; onChange: () => void; label: string }) => (
    <button
      onClick={onChange}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-blue-600' : 'bg-gray-600'
      }`}
    >
      <span
        aria-hidden="true"
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        {hasChanges && (
          <div className="flex items-center space-x-3">
            <button
              onClick={handleReset}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md text-sm transition-colors"
            >
              Reset
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-md text-sm transition-colors"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}
      </div>

      {/* Status Messages */}
      {error && (
        <div role="alert" aria-live="assertive" className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
          <p className="text-red-400">{error}</p>
        </div>
      )}
      {success && (
        <div role="status" aria-live="polite" className="bg-green-900/20 border border-green-500/30 rounded-lg p-4">
          <p className="text-green-400">{success}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-1" role="tablist" aria-label="Settings sections">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              aria-controls={`panel-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-gray-800 text-white border-b-2 border-blue-500'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Panels */}
      <div role="tabpanel" id={`panel-${activeTab}`} aria-labelledby={activeTab}>
        {/* AGENTS TAB */}
        {activeTab === 'agents' && (
          <div className="space-y-6">
            {/* Agent Base Tier Assignment */}
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Agent Base Tiers</h2>
              <p className="text-sm text-gray-400 mb-6">
                Set the starting tier for each agent. Short transcripts will use this tier.
                Longer transcripts may automatically escalate based on duration thresholds.
              </p>

              <div className="space-y-4">
                {AGENT_INFO.map((agent) => {
                  const currentTier = getCurrentPhaseBaseTier(agent.id)
                  const color = getTierColor(currentTier)
                  const styles = TIER_STYLES[color]

                  return (
                    <div key={agent.id} className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 rounded-full bg-gray-800 flex items-center justify-center text-lg">
                          {agent.icon}
                        </div>
                        <div>
                          <div className="font-medium text-white">{agent.name}</div>
                          <div className="text-sm text-gray-400">{agent.description}</div>
                        </div>
                      </div>

                      <label htmlFor={`tier-${agent.id}`} className="sr-only">
                        Base tier for {agent.name}
                      </label>
                      <select
                        id={`tier-${agent.id}`}
                        value={currentTier}
                        onChange={(e) => handlePhaseBaseTierChange(agent.id, parseInt(e.target.value))}
                        className={`px-3 py-2 rounded-md border text-sm font-medium ${styles.bg} ${styles.border} ${styles.text}`}
                        aria-label={`Select base tier for ${agent.name} agent`}
                      >
                        {routing?.tier_labels?.map((label, idx) => (
                          <option key={idx} value={idx} className="bg-gray-800 text-white">
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  )
                })}
              </div>

              <div className="mt-4 flex items-center space-x-6 text-xs text-gray-400">
                {routing?.tier_labels?.map((label, idx) => {
                  const color = getTierColor(idx)
                  return (
                    <div key={idx} className="flex items-center space-x-2">
                      <span className="w-2 h-2 rounded-full" style={{backgroundColor: color === 'green' ? '#22c55e' : color === 'cyan' ? '#06b6d4' : '#a855f7'}} />
                      <span>{label}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        )}

        {/* ROUTING TAB */}
        {activeTab === 'routing' && (
          <div className="space-y-6">
            {/* Duration-Based Tier Escalation */}
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Duration-Based Tier Selection</h2>
              <p className="text-sm text-gray-400 mb-6">
                Set duration thresholds for automatic tier escalation. Longer transcripts require
                more capable models.
              </p>

              <div className="space-y-4">
                {getCurrentThresholds().map((threshold, idx) => {
                  const label = getTierLabel(threshold.tier)
                  const color = getTierColor(threshold.tier)
                  const styles = TIER_STYLES[color]

                  return (
                    <div key={idx} className={`p-4 rounded-lg border ${styles.bg} ${styles.border}`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-medium ${styles.text}`}>
                          Tier {threshold.tier}: {label}
                        </span>
                        <span className="text-gray-400 text-sm">
                          {threshold.max_minutes === null
                            ? 'Unlimited duration'
                            : `Up to ${threshold.max_minutes} minutes`}
                        </span>
                      </div>
                      {threshold.max_minutes !== null && (
                        <>
                          <label htmlFor={`threshold-${idx}`} className="sr-only">
                            Maximum duration in minutes for {label}
                          </label>
                          <input
                            id={`threshold-${idx}`}
                            type="range"
                            min="5"
                            max="60"
                            step="5"
                            value={threshold.max_minutes}
                            onChange={(e) => handleThresholdChange(idx, parseInt(e.target.value))}
                            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                            aria-valuemin={5}
                            aria-valuemax={60}
                            aria-valuenow={threshold.max_minutes}
                          />
                        </>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Failure-Based Escalation */}
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Failure-Based Escalation</h2>
              <p className="text-sm text-gray-400 mb-6">
                When a model fails or times out, automatically retry with the next tier up.
              </p>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
                  <div>
                    <div className="font-medium text-white">Enable Auto-Escalation</div>
                    <div className="text-sm text-gray-400">Automatically retry with higher tiers on failure</div>
                  </div>
                  <Toggle
                    checked={getCurrentEscalation().enabled}
                    onChange={() => handleEscalationChange('enabled', !getCurrentEscalation().enabled)}
                    label="Enable auto-escalation"
                  />
                </div>

                {getCurrentEscalation().enabled && (
                  <>
                    <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
                      <div>
                        <div className="font-medium text-white">Escalate on Failure</div>
                        <div className="text-sm text-gray-400">Retry with next tier when LLM returns an error</div>
                      </div>
                      <Toggle
                        checked={getCurrentEscalation().on_failure}
                        onChange={() => handleEscalationChange('on_failure', !getCurrentEscalation().on_failure)}
                        label="Escalate on failure"
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
                      <div>
                        <div className="font-medium text-white">Escalate on Timeout</div>
                        <div className="text-sm text-gray-400">Retry with next tier when request times out</div>
                      </div>
                      <Toggle
                        checked={getCurrentEscalation().on_timeout}
                        onChange={() => handleEscalationChange('on_timeout', !getCurrentEscalation().on_timeout)}
                        label="Escalate on timeout"
                      />
                    </div>

                    <div className="p-4 bg-gray-900 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <label htmlFor="timeout-duration" className="font-medium text-white">Timeout Duration</label>
                        <span className="text-gray-400">{getCurrentEscalation().timeout_seconds} seconds</span>
                      </div>
                      <input
                        id="timeout-duration"
                        type="range"
                        min="30"
                        max="300"
                        step="30"
                        value={getCurrentEscalation().timeout_seconds}
                        onChange={(e) => handleEscalationChange('timeout_seconds', parseInt(e.target.value))}
                        className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                        aria-valuemin={30}
                        aria-valuemax={300}
                        aria-valuenow={getCurrentEscalation().timeout_seconds}
                      />
                      <div className="flex justify-between text-xs text-gray-400 mt-1">
                        <span>30s</span>
                        <span>2 min</span>
                        <span>5 min</span>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* OpenRouter Preset Note */}
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <div className="flex items-start space-x-3">
                <span className="text-yellow-400 text-xl">💡</span>
                <div>
                  <h3 className="text-sm font-medium text-white">Managing OpenRouter Presets</h3>
                  <p className="text-xs text-gray-400 mt-1">
                    These presets are configured in your OpenRouter account. To modify the models in each
                    preset tier, visit{' '}
                    <a
                      href="https://openrouter.ai/settings/presets"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300"
                    >
                      openrouter.ai/settings/presets
                    </a>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* WORKER TAB */}
        {activeTab === 'worker' && (
          <div className="space-y-6">
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Worker Settings</h2>
              <p className="text-sm text-gray-400 mb-6">
                Configure job processing concurrency. Changes require worker restart.
              </p>

              <div className="space-y-4">
                {/* Concurrent Jobs */}
                <div className="p-4 bg-gray-900 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label htmlFor="concurrent-jobs" className="font-medium text-white">Concurrent Jobs</label>
                      <div className="text-sm text-gray-400">Process multiple jobs simultaneously</div>
                    </div>
                    <span className="text-2xl font-bold text-cyan-400">{getCurrentWorker().max_concurrent_jobs}</span>
                  </div>
                  <input
                    id="concurrent-jobs"
                    type="range"
                    min="1"
                    max="5"
                    step="1"
                    value={getCurrentWorker().max_concurrent_jobs}
                    onChange={(e) => handleWorkerChange('max_concurrent_jobs', parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    aria-valuemin={1}
                    aria-valuemax={5}
                    aria-valuenow={getCurrentWorker().max_concurrent_jobs}
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>1 (safe)</span>
                    <span>3 (default)</span>
                    <span>5 (max)</span>
                  </div>
                </div>

                {/* Poll Interval */}
                <div className="p-4 bg-gray-900 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <label htmlFor="poll-interval" className="font-medium text-white">Poll Interval</label>
                      <div className="text-sm text-gray-400">Seconds between queue checks</div>
                    </div>
                    <span className="text-gray-300">{getCurrentWorker().poll_interval_seconds}s</span>
                  </div>
                  <input
                    id="poll-interval"
                    type="range"
                    min="1"
                    max="30"
                    step="1"
                    value={getCurrentWorker().poll_interval_seconds}
                    onChange={(e) => handleWorkerChange('poll_interval_seconds', parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                    aria-valuemin={1}
                    aria-valuemax={30}
                    aria-valuenow={getCurrentWorker().poll_interval_seconds}
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>1s</span>
                    <span>15s</span>
                    <span>30s</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
