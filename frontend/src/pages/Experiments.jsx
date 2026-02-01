import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Card from '../components/Card'
import { format } from 'date-fns'

export default function Experiments() {
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    hypothesis: '',
    change_type: 'price_increase',
  })
  const [creating, setCreating] = useState(false)

  const { data, loading, error, refetch } = useApi(() => api.getExperiments(), [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      setCreating(true)
      await api.createExperiment(formData)
      await refetch()
      setShowCreateForm(false)
      setFormData({
        name: '',
        description: '',
        hypothesis: '',
        change_type: 'price_increase',
      })
    } catch (err) {
      console.error('Failed to create experiment:', err)
    } finally {
      setCreating(false)
    }
  }

  const handleStart = async (experimentId) => {
    try {
      await api.startExperiment(experimentId)
      await refetch()
    } catch (err) {
      console.error('Failed to start experiment:', err)
    }
  }

  const handleComplete = async (experimentId) => {
    try {
      await api.completeExperiment(experimentId, {
        outcome: 'Manual completion from UI',
        impact_mrr: 0,
      })
      await refetch()
    } catch (err) {
      console.error('Failed to complete experiment:', err)
    }
  }

  if (loading) {
    return <LoadingSpinner size="lg" />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  const experiments = data?.experiments || []

  const getStatusColor = (status) => {
    switch (status) {
      case 'draft': return 'badge-info'
      case 'running': return 'badge-warning'
      case 'completed': return 'badge-success'
      case 'cancelled': return 'badge-danger'
      default: return 'badge-info'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'draft': return '📝'
      case 'running': return '🏃'
      case 'completed': return '✅'
      case 'cancelled': return '❌'
      default: return '📊'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Pricing Experiments
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Track pricing changes and measure their impact
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn btn-primary"
        >
          {showCreateForm ? '✕ Cancel' : '+ New Experiment'}
        </button>
      </div>

      {/* Create Form */}
      {showCreateForm && (
        <Card title="Create New Experiment">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Experiment Name
              </label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="e.g., Pro Plan Price Increase Q1 2026"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Description
              </label>
              <textarea
                required
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="What are you changing and why?"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Hypothesis
              </label>
              <textarea
                required
                value={formData.hypothesis}
                onChange={(e) => setFormData({ ...formData, hypothesis: e.target.value })}
                rows={2}
                className="w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="What do you expect to happen?"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Change Type
              </label>
              <select
                value={formData.change_type}
                onChange={(e) => setFormData({ ...formData, change_type: e.target.value })}
                className="w-full px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="price_increase">Price Increase</option>
                <option value="price_decrease">Price Decrease</option>
                <option value="new_plan">New Plan</option>
                <option value="feature_change">Feature Change</option>
                <option value="packaging">Packaging Change</option>
              </select>
            </div>

            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="btn btn-primary"
              >
                {creating ? 'Creating...' : 'Create Experiment'}
              </button>
            </div>
          </form>
        </Card>
      )}

      {/* Experiments List */}
      <Card>
        {experiments.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <span className="text-6xl mb-4 block">🧪</span>
            <p className="text-lg">No experiments yet</p>
            <p className="text-sm mt-2">Create your first pricing experiment to track changes</p>
          </div>
        ) : (
          <div className="space-y-4">
            {experiments.map((exp) => (
              <div
                key={exp.id}
                className="p-6 rounded-lg border-2 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <span className="text-3xl">{getStatusIcon(exp.status)}</span>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {exp.name}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {exp.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`badge ${getStatusColor(exp.status)}`}>
                      {exp.status}
                    </span>
                    {exp.status === 'draft' && (
                      <button
                        onClick={() => handleStart(exp.id)}
                        className="btn btn-primary btn-sm"
                      >
                        Start
                      </button>
                    )}
                    {exp.status === 'running' && (
                      <button
                        onClick={() => handleComplete(exp.id)}
                        className="btn btn-success btn-sm"
                      >
                        Complete
                      </button>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                      Hypothesis
                    </div>
                    <div className="text-sm text-gray-900 dark:text-white">
                      {exp.hypothesis}
                    </div>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                      Change Type
                    </div>
                    <div className="text-sm text-gray-900 dark:text-white">
                      {exp.change_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-gray-500 dark:text-gray-400">Created</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {format(new Date(exp.created_at), 'MMM dd, yyyy')}
                    </div>
                  </div>
                  {exp.started_at && (
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Started</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {format(new Date(exp.started_at), 'MMM dd, yyyy')}
                      </div>
                    </div>
                  )}
                  {exp.completed_at && (
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">Completed</div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {format(new Date(exp.completed_at), 'MMM dd, yyyy')}
                      </div>
                    </div>
                  )}
                  {exp.impact_mrr !== undefined && exp.impact_mrr !== null && (
                    <div>
                      <div className="text-gray-500 dark:text-gray-400">MRR Impact</div>
                      <div className={`font-medium ${exp.impact_mrr >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {exp.impact_mrr >= 0 ? '+' : ''}{exp.impact_mrr.toFixed(2)}
                      </div>
                    </div>
                  )}
                </div>

                {exp.outcome && (
                  <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
                    <div className="text-xs font-medium text-blue-900 dark:text-blue-300 mb-1">
                      Outcome
                    </div>
                    <div className="text-sm text-blue-800 dark:text-blue-400">
                      {exp.outcome}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Summary Stats */}
      {experiments.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card text-center">
            <div className="text-3xl font-bold text-gray-600 dark:text-gray-400">
              {experiments.filter(e => e.status === 'draft').length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Draft
            </div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
              {experiments.filter(e => e.status === 'running').length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Running
            </div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {experiments.filter(e => e.status === 'completed').length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Completed
            </div>
          </div>
          <div className="card text-center">
            <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {experiments.length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Total
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
