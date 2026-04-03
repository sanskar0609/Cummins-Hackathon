import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AppLayout } from './components/layout/AppLayout'
import { PageTransition } from './components/ui/PageTransition'
import Dashboard from './pages/Dashboard'
import Suppliers from './pages/Suppliers'
import Demand from './pages/Demand'
import Simulator from './pages/Simulator'


import Copilot from './pages/Copilot'

import Alerts from './pages/Alerts'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000
    }
  }
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="suppliers" element={<Suppliers />} />
            <Route path="demand" element={<Demand />} />
            <Route path="simulator" element={<Simulator />} />
            <Route path="copilot" element={<Copilot />} />
            <Route path="alerts" element={<Alerts />} />
          </Route>
        </Routes>
      </Router>
      <Toaster
        position="bottom-right"
        toastOptions={{
          className: 'bg-sc_card border border-white/10 text-white shadow-xl',
          style: { background: '#0b0f17', color: '#fff', border: '1px solid rgba(255,255,255,0.1)' }
        }}
      />
    </QueryClientProvider>
  )
}

export default App
