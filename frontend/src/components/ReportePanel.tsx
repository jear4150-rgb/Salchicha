import type { Reporte } from '../types'
import { COLOR_CONFIG } from '../types'

interface Props {
  reporte: Reporte | null
}

function fmt(n: number) {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ReportePanel({ reporte }: Props) {
  if (!reporte || reporte.total_domicilios === 0) return null

  return (
    <div className="bg-slate-800 rounded-2xl border border-slate-700 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-slate-200 font-semibold text-sm">📊 Reporte total (todos los lotes)</h2>
        <span className="text-slate-500 text-xs">{reporte.total_domicilios} domicilios</span>
      </div>

      <p className="text-3xl font-bold text-emerald-400">${fmt(reporte.total_comision)}</p>

      <div className="space-y-2">
        {reporte.por_repartidor.map((r) => {
          const cfg = COLOR_CONFIG[r.repartidor_color ?? 'slate']
          return (
            <div key={r.repartidor_id ?? 'sin-asignar'} className={`rounded-xl border ${cfg.border} ${cfg.bg} p-3 flex items-center gap-3`}>
              <span className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
              <div className="flex-1 min-w-0">
                <p className="text-white text-sm font-semibold truncate">{r.repartidor_nombre}</p>
                <p className="text-slate-400 text-xs">{r.cantidad_domicilios} domicilio{r.cantidad_domicilios !== 1 ? 's' : ''}</p>
              </div>
              <p className="text-white font-bold text-sm flex-shrink-0">${fmt(r.total_comision)}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
