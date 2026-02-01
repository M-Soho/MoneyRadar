import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Card from '../components/Card'
import { format } from 'date-fns'

export default function Alerts() {
  const [filter, setFilter] = useState('active')
  const [resolving, setResolving] = useState(null)
  const [scanning, setScanning] = useState(false)
  
  const { data, loading, error, refetch } = useApi(
    () => api.getAlerts({ status: filter === 'all' ? undefined : filter }),
    [filter]
  )

  const handleScan = async () => {
    try {
      setScanning(true)
      await api.scanAlerts()
      await refetch()
    } catch (err) {
      console.error('Scan failed:', err)
    } finally {
      setScanning(false)
    }
  }

  const handleResolve = async (alertId) => {
    try {
      setResolving(alertId)
      await api.resolveAlert(alertId, 'Resolved from UI')
      await refetch()
    } catch (err) {
      console.error('Resolution failed:', err)
    } finally {
      setResolving(null)
    }
  }

  if (loading) {
    return <LoadingSpinner size="lg" />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  const alerts = data?.alerts || []

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'badge-danger'
      case 'high': return 'badge-warning'
      case 'medium': return 'badge-info'
      case 'low': return 'badge-success'
      default: return 'badge-info'
    }
  }

  const getTypeIcon = (type) => {
    switch (type) {
      case 'revenue_risk': return '⚠️'
      case 'usage_spike': return '📈'
      case 'mismatch': return '🎯'
      case 'expansion': return '💎'
      default: return '📢'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Revenue Alerts
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor revenue signals and take action
          </p>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="btn btn-primary"
        >
          {scanning ? 'Scanning...' : '🔍 Scan for Alerts'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex space-x-2">
        {['active', 'resolved', 'all'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== 'all' && (
              <span className="ml-2 px-2 py-0.5 rounded-full bg-white/20 text-xs">
                {data?.alerts?.filter(a => f === 'active' ? a.status === 'active' : a.status === 'resolved').length || 0}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Alerts List */}
      <Card>
        {alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <span className="text-6xl mb-4 block">
              {filter === 'active' ? '✅' : '📭'}
            </span>
            <p className="text-lg">
              {filter === 'active' 
                ? 'No active alerts! Everything looks good.' 
                : 'No alerts found'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-6 rounded-lg border-2 ${
                  alert.status === 'active'
                    ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
                    : 'bg-gray-50 dark:bg-gray-900 border-gray-100 dark:border-gray-800 opacity-75'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <span className="text-3xl">{getTypeIcon(alert.alert_type)}</span>
                      <div className="flex items-center space-x-2">
                        <span className={`badge ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                        <span className="badge badge-info">
                          {alert.alert_type.replace('_', ' ')}
                        </span>
                        {alert.status === 'resolved' && (
                          <span className="badge badge-success">
                            ✓ Resolved
                          </span>
                        )}
                      </div>
                    </div>

                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                      {alert.message}
                    </h3>

                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Customer:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">
                          {alert.customer_id}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400">Created:</span>
                        <span className="ml-2 font-medium text-gray-900 dark:text-white">
                          {format(new Date(alert.created_at), 'MMM dd, yyyy HH:mm')}
                        </span>
                      </div>
                      {alert.resolved_at && (
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Resolved:</span>
                          <span className="ml-2 font-medium text-gray-900 dark:text-white">
                            {format(new Date(alert.resolved_at), 'MMM dd, yyyy HH:mm')}
                          </span>
                        </div>
                      )}
                      {alert.metadata && (
                        <div className="col-span-2">
                          <span className="text-gray-500 dark:text-gray-400">Details:</span>
                          <pre className="mt-2 p-3 bg-gray-100 dark:bg-gray-700 rounded text-xs overflow-x-auto">
                            {JSON.stringify(alert.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>

                  {alert.status === 'active' && (
                    <button
                      onClick={() => handleResolve(alert.id)}
                      disabled={resolving === alert.id}
                      className="ml-4 btn btn-success"
                    >
                      {resolving === alert.id ? 'Resolving...' : '✓ Resolve'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-3xl font-bold text-red-600 dark:text-red-400">
            {alerts.filter(a => a.severity === 'critical').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Critical
          </div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">
            {alerts.filter(a => a.severity === 'high').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            High
          </div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
            {alerts.filter(a => a.severity === 'medium').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Medium
          </div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-green-600 dark:text-green-400">
            {alerts.filter(a => a.severity === 'low').length}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Low
          </div>
        </div>
      </div>
    </div>
  )
}
