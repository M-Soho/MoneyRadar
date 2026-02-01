export default function StatCard({ title, value, change, icon, trend }) {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-gray-600'
  const trendIcon = trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
          {change && (
            <p className={`mt-2 text-sm ${trendColor} dark:opacity-90`}>
              <span className="font-medium">{trendIcon} {change}</span>
            </p>
          )}
        </div>
        {icon && (
          <div className="text-4xl opacity-80">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}
