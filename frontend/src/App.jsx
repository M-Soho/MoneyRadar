import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Revenue from './pages/Revenue'
import Alerts from './pages/Alerts'
import Customers from './pages/Customers'
import Experiments from './pages/Experiments'
import Mismatches from './pages/Mismatches'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/revenue" element={<Revenue />} />
        <Route path="/alerts" element={<Alerts />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/mismatches" element={<Mismatches />} />
      </Routes>
    </Layout>
  )
}

export default App
