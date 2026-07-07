import { useState, useEffect, useCallback } from 'react'
import type { Ticket, Summary } from '../types'
import { uploadTicket, getTickets, deleteTicket, getSummary } from '../api'
import SummaryPanel from '../components/SummaryPanel'
import TicketCard from '../components/TicketCard'
import CameraCapture from '../components/CameraCapture'

const EMPTY_SUMMARY: Summary = {
  efectivo: 0, tarjeta: 0, transferencia: 0, otro: 0, total: 0, cantidad_tickets: 0,
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [summary, setSummary] = useState<Summary>(EMPTY_SUMMARY)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [t, s] = await Promise.all([getTickets(), getSummary()])
      setTickets(t)
      setSummary(s)
    } catch {
      // silently fail on background refresh
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  function showToast(msg: string, type: 'success' | 'error') {
    if (type === 'success') {
      setSuccess(msg)
      setTimeout(() => setSuccess(null), 3000)
    } else {
      setError(msg)
      setTimeout(() => setError(null), 4000)
    }
  }

  async function handleFile(file: File) {
    setLoading(true)
    setError(null)
    try {
      const ticket = await uploadTicket(file)
      setTickets((prev) => [ticket, ...prev])
      setSummary((prev) => {
        const tipo = ticket.tipo_pago
        return {
          ...prev,
          [tipo]: (prev[tipo] ?? 0) + ticket.monto,
          total: prev.total + ticket.monto,
          cantidad_tickets: prev.cantidad_tickets + 1,
        }
      })
      showToast(`Ticket agregado: $${ticket.monto.toFixed(2)} (${ticket.tipo_pago})`, 'success')
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Error procesando imagen', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteTicket(id)
      const deleted = tickets.find((t) => t.id === id)
      setTickets((prev) => prev.filter((t) => t.id !== id))
      if (deleted) {
        setSummary((prev) => {
          const tipo = deleted.tipo_pago
          return {
            ...prev,
            [tipo]: Math.max(0, (prev[tipo] ?? 0) - deleted.monto),
            total: Math.max(0, prev.total - deleted.monto),
            cantidad_tickets: Math.max(0, prev.cantidad_tickets - 1),
          }
        })
      }
    } catch {
      showToast('No se pudo eliminar el ticket', 'error')
    }
  }

  const today = new Date().toLocaleDateString('es-AR', {
    weekday: 'long', day: 'numeric', month: 'long',
  })

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      <p className="text-slate-400 text-xs capitalize -mb-2">{today}</p>

      {/* Summary */}
      <SummaryPanel summary={summary} />

      {/* Upload buttons */}
      <CameraCapture onFile={handleFile} loading={loading} />

      {/* Toasts */}
      {success && (
        <div className="bg-green-900 border border-green-700 text-green-200 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          <span>✅</span> {success}
        </div>
      )}
      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          <span>❌</span> {error}
        </div>
      )}

      {/* Ticket list */}
      <div>
        <h2 className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
          Tickets de hoy
        </h2>
        {tickets.length === 0 ? (
          <div className="text-center py-10 text-slate-600">
            <p className="text-4xl mb-3">📋</p>
            <p className="text-sm">Sin tickets aún.<br />Sacá una foto para empezar.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {tickets.map((t) => (
              <TicketCard key={t.id} ticket={t} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>

      {/* Bottom safe area spacer */}
      <div className="h-4 safe-bottom" />
    </div>
  )
}
