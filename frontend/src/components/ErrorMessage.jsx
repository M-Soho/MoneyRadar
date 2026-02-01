export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
      <div className="flex items-start">
        <span className="text-2xl mr-3">⚠️</span>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-red-800 dark:text-red-300">
            Error
          </h3>
          <p className="mt-1 text-sm text-red-700 dark:text-red-400">
            {message}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 btn btn-secondary text-sm"
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
