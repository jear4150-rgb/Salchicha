import { useState } from 'react'
import type { Zona } from '../types'
import { createZona, deleteZona, updateZona } from '../api'

interface Props {
  zonas: Zona[]
  onChange: (zonas: Zona[]) => void
}

function fmt(n: number) {
  return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function ZonaManager({ zonas, onChange }: Props) {
  const [open, setOpen] = useState(zonas.length === 0)
  const [nombre, setNombre] = useState('')
  const [valor, setValor] = useState('')
  const [saving, setSaving] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValor, setEditValor] = useState('')

  async function handleAdd() {
    const monto = parseFloat(valor)
    if (!nombre.trim() || Number.isNaN(monto)) return
    setSaving(true)
    try {
      const zona = await createZona(nombre.trim(), monto)
      onChange([...zonas, zona].sort((a, b) => a.nombre.localeCompare(b.nombre)))
      setNombre('')
      setValor('')
    } catch {
      // ignore, user can retry
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    try {
      await deleteZona(id)
      onChange(zonas.filter((z) => z.id !== id))
    } catch {
      // ignore
    }
  }

  async function handleSaveValor(id: number) {
    const monto = parseFloat(editValor)
    if (Number.isNaN(monto)) {
      setEditingId(null)
      return
    }
    try {
      const updated = await updateZona(id, { valor: monto })
      onChange(zonas.map((z) => (z.id === id ? updated : z)))
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
          💰 Valor por zona ({zonas.length})
        </span>
        <svg className={`w-4 h-4 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3">
          {zonas.length === 0 && (
            <p className="text-slate-500 text-xs">
              Definí cuánto se gana por cada domicilio de cada zona. Al importar una planilla,
              la IA va a usar estos nombres de zona y calcular la comisión automáticamente.
            </p>
          )}

          <div className="space-y-2">
            {zonas.map((z) => (
              <div key={z.id} className="rounded-xl border border-slate-700 bg-slate-900 p-3 flex items-center gap-2">
                <span className="text-white text-sm flex-1 truncate">{z.nombre}</span>
                {editingId === z.id ? (
                  <>
                    <input
                      type="number"
                      value={editValor}
                      onChange={(e) => setEditValor(e.target.value)}
                      className="w-24 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-sm text-white"
                      autoFocus
                    />
                    <button onClick={() => handleSaveValor(z.id)} className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-1 rounded-lg">
                      Guardar
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => { setEditingId(z.id); setEditValor(String(z.valor)) }}
                    className="text-emerald-400 font-semibold text-sm px-2 py-1 rounded-lg hover:bg-slate-800"
                  >
                    ${fmt(z.valor)}
                  </button>
                )}
                <button
                  onClick={() => handleDelete(z.id)}
                  className="text-slate-500 hover:text-red-400 p-1 rounded-lg hover:bg-slate-800"
                  aria-label={`Eliminar zona ${z.nombre}`}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>

          {/* Add form */}
          <div className="border-t border-slate-700 pt-3 flex gap-2">
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              placeholder="Zona, ej: Palermo"
              className="flex-1 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
            <input
              type="number"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              placeholder="$"
              className="w-20 bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500"
            />
            <button
              onClick={handleAdd}
              disabled={saving || !nombre.trim() || !valor}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold text-sm rounded-lg px-3 transition-colors"
            >
              +
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
