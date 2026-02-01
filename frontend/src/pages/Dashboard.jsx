import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import StatCard from '../components/StatCard'
import Card from '../components/Card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState('30')
  
  const { data: mrrData, loading: mrrLoading, error: mrrError } = useApi(
    () => api.getMRR({ days: timeRange }),
    [timeRange]
  )
  
  const { data: alerts, loading: alertsLoading, error: alertsError } = useApi(
    () => api.getAlerts({ status: 'active', limit: 5 }),
    []
  )
  
  const { data: snapshots, loading: snapshotsLoading, error: snapshotsError } = useApi(
    () => api.getMRRSnapshots({ days: timeRange }),
    [timeRange]
  )

  if (mrrLoading || alertsLoading || snapshotsLoading) {
    return <LoadingSpinner size="lg" />
  }

  if (mrrError || alertsError || snapshotsError) {
    return <ErrorMessage message={mrrError || alertsError || snapshotsError} />
  }

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value)
  }

  const chartData = snapshots?.snapshots?.map(s => ({
    date: format(new Date(s.snapshot_date), 'MMM dd'),
    mrr: s.mrr,
  })) || []

  const latestMRR = mrrData?.mrr || 0
  const mrrChange = mrrData?.change_percent || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Revenue intelligence overview
          </p>
        </div>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Monthly Recurring Revenue"
          value={formatCurrency(latestMRR)}
          change={`${mrrChange > 0 ? '+' : ''}${mrrChange.toFixed(1)}%`}
          trend={mrrChange > 0 ? 'up' : mrrChange < 0 ? 'down' : 'neutral'}
          icon="💰"
        />
        <StatCard
          title="Active Alerts"
          value={alerts?.alerts?.length || 0}
          icon="⚠️"
        />
        <StatCard
          title="New Revenue"
          value={formatCurrency(mrrData?.new_mrr || 0)}
          trend="up"
          icon="📈"
        />
        <StatCard
          title="Churned Revenue"
          value={formatCurrency(Math.abs(mrrData?.churned_mrr || 0))}
          trend="down"
          icon="📉"
        />
      </div>

      {/* MRR Trend Chart */}
      <Card title="MRR Trend" subtitle={`Last ${timeRange} days`}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" tickFormatter={formatCurrency} />
            <Tooltip
              formatter={(value) => [formatCurrency(value), 'MRR']}
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '0.5rem',
                color: '#F9FAFB'
              }}
            />
            <Line
              type="monotone"
              dataKey="mrr"
              stroke="#0EA5E9"
              strokeWidth={2}
              dot={{ fill: '#0EA5E9' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Recent Alerts */}
      <Card
        title="Recent Alerts"
        subtitle="Active revenue signals requiring attention"
        action={
          <a href="/alerts" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
            View all →
          </a>
        }
      >
        {alerts?.alerts?.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <span className="text-4xl mb-2 block">✅</span>
            No active alerts
          </div>
        ) : (
          <div className="space-y-3">
            {alerts?.alerts?.slice(0, 5).map((alert) => (
              <div
                key={alert.id}
                className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className={`badge badge-${
                      alert.severity === 'critical' ? 'danger' :
                      alert.severity === 'high' ? 'warning' : 'info'
                    }`}>
                      {alert.severity}
                    </span>
                    <span className={`badge badge-info`}>
                      {alert.alert_type}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-900 dark:text-white">
                    {alert.message}
                  </p>
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Customer: {alert.customer_id}
                  </p>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {format(new Date(alert.created_at), 'MMM dd, HH:mm')}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
