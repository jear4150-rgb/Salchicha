import { useState } from 'react'
import type { Repartidor, RepartidorColor } from '../types'
import { COLOR_CONFIG, COLOR_OPTIONS } from '../types'
import { createRepartidor, deleteRepartidor, updateRepartidor } from '../api'

interface Props {
  repartidores: Repartidor[]
  onChange: (repartidores: Repartidor[]) => void
}

export default function RepartidorManager({ repartidores, onChange }: Props) {
  const [open, setOpen] = useState(repartidores.length === 0)
  const [nombre, setNombre] = useState('')
  const [zonas, setZonas] = useState('')
  const [color, setColor] = useState<RepartidorColor>('orange')
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)

  async function handleAdd() {
    if (!nombre.trim()) return
    setSaving(true)
    try {
      const repartidor = await createRepartidor(nombre.trim(), color, zonas.trim())
      onChange([...repartidores, repartidor].sort((a, b) => a.nombre.localeCompare(b.nombre)))
      setNombre('')
      setZonas('')
      const usedColors = new Set(repartidores.map((r) => r.color))
      const nextColor = COLOR_OPTIONS.find((c) => c !== 'slate' && !usedColors.has(c)) ?? 'slate'
      setColor(nextColor)
    } catch {
      // ignore, user can retry
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteRepartidor(id)
      onChange(repartidores.filter((r) => r.id !== id))
    } catch {
      // ignore
    }
  }

  async function handleUpdateZonas(id: number, nuevasZonas: string) {
    try {
      const updated = await updateRepartidor(id, { zonas: nuevasZonas })
      onChange(repartidores.map((r) => (r.id === id ? updated : r)))
    } catch {
      // ignore
    } finally {
      setEditingId(null)
    }
  }

  return (
    <div className="bg-slate-800 rounded-2xl border border-slate-700 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3"
      >
        <span className="text-slate-200 font-semibold text-sm">
          🧑‍✈️ Repartidores ({repartidores.length})
        </span>
        <svg className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          {repartidores.length === 0 && (
            <p className="text-slate-500 text-xs">
              Todavía no cargaste repartidores. Podés importar domicilios igual y clasificarlos por zona,
              o cargar repartidores acá para que la app los asigne automáticamente por color.
            </p>
          )}

          <div className="space-y-2">
            {repartidores.map((r) => {
              const cfg = COLOR_CONFIG[r.color]
              return (
                <div key={r.id} className={`rounded-xl border ${cfg.border} ${cfg.bg} p-3`}>
                  <div className="flex items-center gap-2">
                    <span className={`w-3 h-3 rounded-full flex-shrink-0 ${cfg.dot}`} />
                    <span className="text-white font-semibold text-sm flex-1 truncate">{r.nombre}</span>
                    <button
                      onClick={() => setEditingId(editingId === r.id ? null : r.id)}
                      className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded-lg hover:bg-slate-800"
                    >
                      Editar zonas
                    </button>
                    <button
                      onClick={() => handleDelete(r.id)}
                      className="text-slate-400 hover:text-red-400 p-1 rounded-lg hover:bg-slate-800"
                      aria-label={`Eliminar ${r.nombre}`}
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  {editingId === r.id ? (
                    <EditZonas
                      initial={r.zonas}
                      onSave={(v) => handleUpdateZonas(r.id, v)}
                      onCancel={() => setEditingId(null)}
                    />
                  ) : (
                    <p className="text-slate-400 text-xs mt-1 pl-5">
                      {r.zonas ? r.zonas : 'Sin zonas definidas — se le puede asignar manualmente'}
                    </p>
                  )}
                </div>
              )
            })}
          </div>

          {/* Add form */}
          <div className="border-t border-slate-700 pt-3 space-y-2">
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Nombre del repartidor"
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
            <input
              value={zonas}
              onChange={(e) => setZonas(e.target.value)}
              placeholder="Zonas que cubre, ej: Palermo, Belgrano, Nuñez"
              className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
            <div className="flex items-center gap-2 flex-wrap">
              {COLOR_OPTIONS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-6 h-6 rounded-full ${COLOR_CONFIG[c].dot} ${color === c ? 'ring-2 ring-white' : 'opacity-60'}`}
                  aria-label={c}
                />
              ))}
            </div>
            <button
              onClick={handleAdd}
              disabled={saving || !nombre.trim()}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm rounded-lg py-2 transition-colors"
            >
              {saving ? 'Agregando…' : '+ Agregar repartidor'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function EditZonas({ initial, onSave, onCancel }: { initial: string; onSave: (v: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState(initial)
  return (
    <div className="mt-2 pl-5 flex gap-2">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-2 py-1 text-xs text-white"
        autoFocus
      />
      <button onClick={() => onSave(value)} className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-1 rounded-lg">
        Guardar
      </button>
      <button onClick={onCancel} className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 px-2 py-1 rounded-lg">
        Cancelar
      </button>
    </div>
  )
}
