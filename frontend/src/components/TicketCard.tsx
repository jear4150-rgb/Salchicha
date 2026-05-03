import { useState } from 'react'
import type { Ticket } from '../types'
import { TIPO_CONFIG } from '../types'

interface Props {
  ticket: Ticket
  onDelete: (id: number) => void
}

function fmt(n: number) {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

export default function TicketCard({ ticket, onDelete }: Props) {
  const [showImage, setShowImage] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const cfg = TIPO_CONFIG[ticket.tipo_pago] ?? TIPO_CONFIG.otro

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} overflow-hidden`}>
      <div className="flex items-center gap-3 p-3">
        {/* Thumbnail */}
        {ticket.imagen_path && (
          <button
            onClick={() => setShowImage(true)}
            className="flex-shrink-0 w-14 h-14 rounded-lg overflow-hidden bg-slate-800 border border-slate-600"
          >
            <img
              src={`/api/uploads/${ticket.imagen_path}`}
              alt="ticket"
              className="w-full h-full object-cover"
            />
          </button>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className={`text-xs font-bold uppercase tracking-wide ${cfg.badge} px-2 py-0.5 rounded-full`}>
              {cfg.icon} {cfg.label}
            </span>
            <span className="text-slate-500 text-xs">{fmtTime(ticket.created_at)}</span>
          </div>
          {ticket.descripcion && (
            <p className="text-slate-300 text-sm truncate">{ticket.descripcion}</p>
          )}
          <p className="text-white font-bold text-lg">${fmt(ticket.monto)}</p>
        </div>

        {/* Delete */}
        <div className="flex-shrink-0">
          {confirmDelete ? (
            <div className="flex flex-col gap-1">
              <button
                onClick={() => onDelete(ticket.id)}
                className="text-xs bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded-lg font-semibold"
              >
                Borrar
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded-lg"
              >
                No
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="text-slate-500 hover:text-red-400 p-2 rounded-lg hover:bg-slate-800 transition-colors"
              aria-label="Eliminar ticket"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Full image modal */}
      {showImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setShowImage(false)}
        >
          <img
            src={`/api/uploads/${ticket.imagen_path}`}
            alt="ticket completo"
            className="max-w-full max-h-full rounded-xl object-contain"
          />
        </div>
      )}
    </div>
  )
}
