import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Card from '../components/Card'
import { format } from 'date-fns'

export default function Mismatches() {
  const [severity, setSeverity] = useState('all')
  
  const { data, loading, error, refetch } = useApi(
    () => api.getMismatches({ min_severity: severity !== 'all' ? severity : undefined }),
    [severity]
  )

  if (loading) {
    return <LoadingSpinner size="lg" />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={refetch} />
  }

  const mismatches = data?.mismatches || []

  const getSeverityColor = (sev) => {
    if (sev >= 0.7) return 'badge-danger'
    if (sev >= 0.4) return 'badge-warning'
    return 'badge-info'
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Usage vs Price Mismatches
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Identify customers who should upgrade or downgrade
          </p>
        </div>
        <select
          value={severity}
          onChange={(e) => setSeverity(e.target.value)}
          className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="all">All Severities</option>
          <option value="0.7">High (≥0.7)</option>
          <option value="0.4">Medium (≥0.4)</option>
        </select>
      </div>

      {/* Mismatches List */}
      <Card>
        {mismatches.length === 0 ? (
          <div className="text-center py-12 text-gray-500 dark:text-gray-400">
            <span className="text-6xl mb-4 block">✅</span>
            <p className="text-lg">No significant mismatches detected</p>
            <p className="text-sm mt-2">All customers appear to be on appropriate plans</p>
          </div>
        ) : (
          <div className="space-y-4">
            {mismatches.map((mismatch, index) => (
              <div
                key={index}
                className="p-6 rounded-lg border-2 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <span className="text-3xl">
                      {mismatch.direction === 'overusing' ? '📈' : '📉'}
                    </span>
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        Customer: {mismatch.customer_id}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {mismatch.direction === 'overusing' ? 'Upgrade Opportunity' : 'Potential Downgrade'}
                      </p>
                    </div>
                  </div>
                  <span className={`badge ${getSeverityColor(mismatch.severity)}`}>
                    {(mismatch.severity * 100).toFixed(0)}% severity
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Current Plan</div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {mismatch.current_plan}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Current Price</div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {formatCurrency(mismatch.current_price)}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Usage Ratio</div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {(mismatch.usage_ratio * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Detected</div>
                    <div className="text-sm font-medium text-gray-900 dark:text-white">
                      {format(new Date(mismatch.detected_at), 'MMM dd, yyyy')}
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 rounded p-4">
                  <div className="flex items-start space-x-3">
                    <span className="text-xl">💡</span>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white mb-1">
                        Recommendation
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {mismatch.direction === 'overusing' ? (
                          <>This customer is using {(mismatch.usage_ratio * 100).toFixed(0)}% of their plan limits. Consider reaching out about an upgrade to better match their usage.</>
                        ) : (
                          <>This customer is only using {(mismatch.usage_ratio * 100).toFixed(0)}% of their plan capacity. They may be overpaying for unused features.</>
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Summary Stats */}
      {mismatches.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card text-center">
            <div className="text-4xl mb-2">📈</div>
            <div className="text-3xl font-bold text-green-600 dark:text-green-400">
              {mismatches.filter(m => m.direction === 'overusing').length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Upgrade Opportunities
            </div>
          </div>
          <div className="card text-center">
            <div className="text-4xl mb-2">📉</div>
            <div className="text-3xl font-bold text-blue-600 dark:text-blue-400">
              {mismatches.filter(m => m.direction === 'underusing').length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Potential Downgrades
            </div>
          </div>
          <div className="card text-center">
            <div className="text-4xl mb-2">🎯</div>
            <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {mismatches.length}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Total Mismatches
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
