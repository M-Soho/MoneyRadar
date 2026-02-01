const API_BASE = import.meta.env.VITE_API_URL || '/api'

class ApiClient {
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'API request failed')
      }

      return data
    } catch (error) {
      console.error('API Error:', error)
      throw error
    }
  }

  // Revenue endpoints
  getMRR(params = {}) {
    const query = new URLSearchParams(params).toString()
    return this.request(`/revenue/mrr${query ? `?${query}` : ''}`)
  }

  getMRRSnapshots(params = {}) {
    const query = new URLSearchParams(params).toString()
    return this.request(`/revenue/snapshots${query ? `?${query}` : ''}`)
  }

  // Alerts endpoints
  getAlerts(params = {}) {
    const query = new URLSearchParams(params).toString()
    return this.request(`/alerts${query ? `?${query}` : ''}`)
  }

  scanAlerts() {
    return this.request('/alerts/scan', { method: 'POST' })
  }

  resolveAlert(alertId, notes) {
    return this.request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    })
  }

  // Analysis endpoints
  getMismatches(params = {}) {
    const query = new URLSearchParams(params).toString()
    return this.request(`/analysis/mismatches${query ? `?${query}` : ''}`)
  }

  // Customer endpoints
  getCustomerScore(customerId) {
    return this.request(`/customers/${customerId}/score`)
  }

  // Experiments endpoints
  getExperiments(params = {}) {
    const query = new URLSearchParams(params).toString()
    return this.request(`/experiments${query ? `?${query}` : ''}`)
  }

  createExperiment(data) {
    return this.request('/experiments', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getExperiment(experimentId) {
    return this.request(`/experiments/${experimentId}`)
  }

  startExperiment(experimentId) {
    return this.request(`/experiments/${experimentId}/start`, {
      method: 'POST',
    })
  }

  completeExperiment(experimentId, results) {
    return this.request(`/experiments/${experimentId}/complete`, {
      method: 'POST',
      body: JSON.stringify(results),
    })
  }

  // Admin endpoints
  syncStripe() {
    return this.request('/admin/sync-stripe', { method: 'POST' })
  }

  calculateMRRSnapshot(date) {
    return this.request('/admin/calculate-mrr-snapshot', {
      method: 'POST',
      body: JSON.stringify({ snapshot_date: date }),
    })
  }

  // Health check
  healthCheck() {
    return this.request('/health')
  }
}

export const api = new ApiClient()
