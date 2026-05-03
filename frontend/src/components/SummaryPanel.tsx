import type { Summary, TipoPago } from '../types'
import { TIPO_CONFIG } from '../types'

interface Props {
  summary: Summary
}

function fmt(n: number) {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const TIPOS: TipoPago[] = ['efectivo', 'tarjeta', 'transferencia', 'otro']

export default function SummaryPanel({ summary }: Props) {
  return (
    <div className="space-y-3">
      {/* Total general */}
      <div className="bg-slate-800 rounded-2xl p-4 border border-slate-700">
        <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">
          Total del día · {summary.cantidad_tickets} ticket{summary.cantidad_tickets !== 1 ? 's' : ''}
        </p>
        <p className="text-3xl font-bold text-white">
          ${fmt(summary.total)}
        </p>
      </div>

      {/* Por tipo de pago */}
      <div className="grid grid-cols-2 gap-2">
        {TIPOS.map((tipo) => {
          const cfg = TIPO_CONFIG[tipo]
          const monto = summary[tipo]
          return (
            <div
              key={tipo}
              className={`rounded-xl p-3 border ${cfg.bg} ${cfg.border} ${monto === 0 ? 'opacity-50' : ''}`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="text-base">{cfg.icon}</span>
                <span className={`text-xs font-semibold uppercase tracking-wide ${cfg.color}`}>
                  {cfg.label}
                </span>
              </div>
              <p className="text-xl font-bold text-white">${fmt(monto)}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
