import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Card from '../components/Card'

export default function Customers() {
  const [customerId, setCustomerId] = useState('')
  const [scoreData, setScoreData] = useState(null)
  const [loadingScore, setLoadingScore] = useState(false)
  const [scoreError, setScoreError] = useState(null)

  const handleGetScore = async (e) => {
    e.preventDefault()
    if (!customerId.trim()) return

    try {
      setLoadingScore(true)
      setScoreError(null)
      const data = await api.getCustomerScore(customerId)
      setScoreData(data)
    } catch (err) {
      setScoreError(err.message)
      setScoreData(null)
    } finally {
      setLoadingScore(false)
    }
  }

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'text-green-600 dark:text-green-400'
    if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getScoreLabel = (score) => {
    if (score >= 0.7) return 'High Potential'
    if (score >= 0.4) return 'Medium Potential'
    return 'Low Potential'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Customer Expansion Scoring
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Analyze customer expansion readiness and upsell potential
        </p>
      </div>

      {/* Customer Score Lookup */}
      <Card title="Get Customer Score" subtitle="Enter a customer ID to view their expansion score">
        <form onSubmit={handleGetScore} className="space-y-4">
          <div className="flex space-x-3">
            <input
              type="text"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
              placeholder="Enter customer ID (e.g., cus_xxxxx)"
              className="flex-1 px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            <button
              type="submit"
              disabled={loadingScore || !customerId.trim()}
              className="btn btn-primary"
            >
              {loadingScore ? 'Loading...' : '🔍 Get Score'}
            </button>
          </div>
        </form>

        {scoreError && (
          <div className="mt-4">
            <ErrorMessage message={scoreError} />
          </div>
        )}

        {scoreData && (
          <div className="mt-6 space-y-4">
            <div className="bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20 rounded-lg p-6 border border-primary-200 dark:border-primary-800">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                    Expansion Score
                  </div>
                  <div className={`text-6xl font-bold ${getScoreColor(scoreData.score)}`}>
                    {(scoreData.score * 100).toFixed(0)}
                  </div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-2">
                    {getScoreLabel(scoreData.score)}
                  </div>
                </div>
                <div className="text-6xl">
                  {scoreData.score >= 0.7 ? '🌟' : scoreData.score >= 0.4 ? '⭐' : '📊'}
                </div>
              </div>
            </div>

            {scoreData.factors && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(scoreData.factors).map(([key, value]) => (
                  <div key={key} className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                    <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div className="text-2xl font-bold text-gray-900 dark:text-white">
                      {typeof value === 'number' ? value.toFixed(2) : value}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {scoreData.recommendation && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <span className="text-2xl">💡</span>
                  <div>
                    <div className="font-medium text-blue-900 dark:text-blue-300 mb-1">
                      Recommendation
                    </div>
                    <p className="text-sm text-blue-800 dark:text-blue-400">
                      {scoreData.recommendation}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* About Expansion Scoring */}
      <Card title="About Expansion Scoring" subtitle="How we calculate expansion readiness">
        <div className="space-y-4 text-sm text-gray-600 dark:text-gray-400">
          <p>
            The expansion score is calculated based on multiple factors:
          </p>
          <ul className="list-disc list-inside space-y-2 ml-4">
            <li><strong>Usage Growth:</strong> Recent increase in product usage</li>
            <li><strong>Payment History:</strong> Consistent, on-time payments</li>
            <li><strong>Engagement Level:</strong> Active feature adoption and usage</li>
            <li><strong>Plan Fit:</strong> Current usage relative to plan limits</li>
            <li><strong>Revenue Stability:</strong> MRR consistency over time</li>
          </ul>
          <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="font-medium text-gray-900 dark:text-white mb-2">Score Interpretation:</div>
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="text-green-600 dark:text-green-400">●</span>
                <span><strong>70-100%:</strong> High expansion potential - safe to upsell</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-yellow-600 dark:text-yellow-400">●</span>
                <span><strong>40-69%:</strong> Medium potential - proceed with caution</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-red-600 dark:text-red-400">●</span>
                <span><strong>0-39%:</strong> Low potential - focus on retention</span>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
