import { NavLink } from 'react-router-dom'

const navigation = [
  { name: 'Dashboard', path: '/', icon: '📊' },
  { name: 'Revenue', path: '/revenue', icon: '💰' },
  { name: 'Alerts', path: '/alerts', icon: '⚠️' },
  { name: 'Mismatches', path: '/mismatches', icon: '🎯' },
  { name: 'Customers', path: '/customers', icon: '👥' },
  { name: 'Experiments', path: '/experiments', icon: '🧪' },
]

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-3xl">💰</span>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  MoneyRadar
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Revenue Intelligence Dashboard
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Status:{' '}
                <span className="text-green-600 dark:text-green-400 font-medium">
                  Active
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {navigation.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  `flex items-center space-x-2 px-3 py-4 text-sm font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-primary-600 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`
                }
              >
                <span>{item.icon}</span>
                <span>{item.name}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
