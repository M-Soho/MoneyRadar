import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import Card from '../components/Card'
import StatCard from '../components/StatCard'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { format } from 'date-fns'

export default function Revenue() {
  const [timeRange, setTimeRange] = useState('90')
  
  const { data: mrrData, loading: mrrLoading, error: mrrError } = useApi(
    () => api.getMRR({ days: timeRange }),
    [timeRange]
  )
  
  const { data: snapshots, loading: snapshotsLoading, error: snapshotsError, refetch } = useApi(
    () => api.getMRRSnapshots({ days: timeRange }),
    [timeRange]
  )

  if (mrrLoading || snapshotsLoading) {
    return <LoadingSpinner size="lg" />
  }

  if (mrrError || snapshotsError) {
    return <ErrorMessage message={mrrError || snapshotsError} onRetry={refetch} />
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
    new: s.new_mrr || 0,
    expansion: s.expansion_mrr || 0,
    contraction: s.contraction_mrr || 0,
    churned: Math.abs(s.churned_mrr || 0),
  })) || []

  const movementData = [
    { name: 'New MRR', value: mrrData?.new_mrr || 0, color: '#10B981' },
    { name: 'Expansion', value: mrrData?.expansion_mrr || 0, color: '#3B82F6' },
    { name: 'Contraction', value: Math.abs(mrrData?.contraction_mrr || 0), color: '#F59E0B' },
    { name: 'Churned', value: Math.abs(mrrData?.churned_mrr || 0), color: '#EF4444' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Revenue Analytics
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Track MRR and revenue movements
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-4 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="180">Last 6 months</option>
            <option value="365">Last year</option>
          </select>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Current MRR"
          value={formatCurrency(mrrData?.mrr || 0)}
          change={`${mrrData?.change_percent > 0 ? '+' : ''}${(mrrData?.change_percent || 0).toFixed(1)}%`}
          trend={mrrData?.change_percent > 0 ? 'up' : mrrData?.change_percent < 0 ? 'down' : 'neutral'}
          icon="💰"
        />
        <StatCard
          title="New MRR"
          value={formatCurrency(mrrData?.new_mrr || 0)}
          trend="up"
          icon="✨"
        />
        <StatCard
          title="Expansion MRR"
          value={formatCurrency(mrrData?.expansion_mrr || 0)}
          trend="up"
          icon="📈"
        />
        <StatCard
          title="Churn Rate"
          value={`${((Math.abs(mrrData?.churned_mrr || 0) / (mrrData?.mrr || 1)) * 100).toFixed(1)}%`}
          trend="down"
          icon="📉"
        />
      </div>

      {/* MRR Trend */}
      <Card title="MRR Growth Trend" subtitle={`MRR over the last ${timeRange} days`}>
        <ResponsiveContainer width="100%" height={350}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" tickFormatter={formatCurrency} />
            <Tooltip
              formatter={(value) => formatCurrency(value)}
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
              strokeWidth={3}
              dot={{ fill: '#0EA5E9', r: 4 }}
              name="Total MRR"
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* MRR Movement Breakdown */}
      <Card title="MRR Movement" subtitle="Breakdown of revenue changes">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={movementData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9CA3AF" />
              <YAxis stroke="#9CA3AF" tickFormatter={formatCurrency} />
              <Tooltip
                formatter={(value) => formatCurrency(value)}
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '0.5rem',
                  color: '#F9FAFB'
                }}
              />
              <Bar dataKey="value" fill="#0EA5E9" />
            </BarChart>
          </ResponsiveContainer>

          <div className="space-y-4">
            {movementData.map((item) => (
              <div key={item.name} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="font-medium text-gray-900 dark:text-white">
                    {item.name}
                  </span>
                </div>
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  {formatCurrency(item.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* Component Breakdown */}
      <Card title="MRR Components Over Time" subtitle="Track revenue movements">
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" tickFormatter={formatCurrency} />
            <Tooltip
              formatter={(value) => formatCurrency(value)}
              contentStyle={{
                backgroundColor: '#1F2937',
                border: '1px solid #374151',
                borderRadius: '0.5rem',
                color: '#F9FAFB'
              }}
            />
            <Legend />
            <Bar dataKey="new" stackId="a" fill="#10B981" name="New" />
            <Bar dataKey="expansion" stackId="a" fill="#3B82F6" name="Expansion" />
            <Bar dataKey="contraction" stackId="b" fill="#F59E0B" name="Contraction" />
            <Bar dataKey="churned" stackId="b" fill="#EF4444" name="Churned" />
          </BarChart>
        </ResponsiveContainer>
      </Card>
    </div>
  )
}
