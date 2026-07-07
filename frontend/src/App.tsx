import { useState } from 'react'
import TicketsPage from './pages/TicketsPage'
import DomiciliosPage from './pages/DomiciliosPage'

type Tab = 'tickets' | 'domicilios'

export default function App() {
  const [tab, setTab] = useState<Tab>('tickets')

  return (
    <div className="min-h-full bg-slate-900 flex flex-col max-w-md mx-auto">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 pt-4 safe-top">
        <h1 className="text-lg font-bold text-white mb-3">Salchicha 🌭</h1>

        {/* Tabs */}
        <div className="flex gap-1 bg-slate-900 rounded-xl p-1">
          <button
            onClick={() => setTab('tickets')}
            className={`flex-1 text-sm font-semibold rounded-lg py-2 transition-colors ${
              tab === 'tickets' ? 'bg-indigo-600 text-white' : 'text-slate-400'
            }`}
          >
            🎫 Tickets
          </button>
          <button
            onClick={() => setTab('domicilios')}
            className={`flex-1 text-sm font-semibold rounded-lg py-2 transition-colors ${
              tab === 'domicilios' ? 'bg-indigo-600 text-white' : 'text-slate-400'
            }`}
          >
            📍 Domicilios
          </button>
        </div>
      </header>

      {/* Content */}
      {tab === 'tickets' ? <TicketsPage /> : <DomiciliosPage />}
    </div>
  )
}
