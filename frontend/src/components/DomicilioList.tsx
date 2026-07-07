import { useMemo, useState } from 'react'
import type { Domicilio, Repartidor } from '../types'
import { COLOR_CONFIG } from '../types'

interface Props {
  domicilios: Domicilio[]
  repartidores: Repartidor[]
  onReassign: (domicilioId: number, repartidorId: number | null) => void
}

const SIN_ASIGNAR_KEY = 'sin-asignar'

export default function DomicilioList({ domicilios, repartidores, onReassign }: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, Domicilio[]>()
    for (const d of domicilios) {
      const key = d.repartidor_id != null ? String(d.repartidor_id) : SIN_ASIGNAR_KEY
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(d)
    }
    const entries = Array.from(map.entries())
    entries.sort(([a], [b]) => {
      if (a === SIN_ASIGNAR_KEY) return 1
      if (b === SIN_ASIGNAR_KEY) return -1
      return a.localeCompare(b)
    })
    return entries
  }, [domicilios])

  if (domicilios.length === 0) {
    return (
      <div className="text-center py-10 text-slate-600">
        <p className="text-4xl mb-3">📍</p>
        <p className="text-sm">Sin domicilios cargados aún.<br />Subí una planilla para empezar.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {groups.map(([key, items]) => {
        const repartidor = key === SIN_ASIGNAR_KEY ? null : repartidores.find((r) => String(r.id) === key)
        const color = repartidor?.color ?? 'slate'
        const cfg = COLOR_CONFIG[color]
        const label = repartidor?.nombre ?? 'Sin asignar'
        return (
          <div key={key}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-2.5 h-2.5 rounded-full ${cfg.dot}`} />
              <h3 className="text-slate-300 text-xs font-semibold uppercase tracking-wider">
                {label} · {items.length}
              </h3>
            </div>
            <div className="space-y-2">
              {items.map((d) => (
                <DomicilioRow key={d.id} domicilio={d} repartidores={repartidores} onReassign={onReassign} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function DomicilioRow({ domicilio, repartidores, onReassign }: {
  domicilio: Domicilio
  repartidores: Repartidor[]
  onReassign: (domicilioId: number, repartidorId: number | null) => void
}) {
  const [open, setOpen] = useState(false)
  const color = domicilio.repartidor_color ?? 'slate'
  const cfg = COLOR_CONFIG[color]

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} p-3`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-white text-sm font-medium">{domicilio.direccion}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            {domicilio.cliente && <span className="text-slate-400 text-xs">{domicilio.cliente}</span>}
            {domicilio.zona_detectada && (
              <span className="text-slate-500 text-xs">· {domicilio.zona_detectada}</span>
            )}
          </div>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className={`flex-shrink-0 text-xs font-semibold px-2 py-1 rounded-full ${cfg.badge}`}
        >
          {domicilio.repartidor_nombre ?? 'Asignar'}
        </button>
      </div>
      {open && (
        <div className="mt-2 flex gap-1.5 flex-wrap">
          <button
            onClick={() => { onReassign(domicilio.id, null); setOpen(false) }}
            className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded-lg"
          >
            Sin asignar
          </button>
          {repartidores.map((r) => (
            <button
              key={r.id}
              onClick={() => { onReassign(domicilio.id, r.id); setOpen(false) }}
              className={`text-xs px-2 py-1 rounded-lg ${COLOR_CONFIG[r.color].badge}`}
            >
              {r.nombre}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
