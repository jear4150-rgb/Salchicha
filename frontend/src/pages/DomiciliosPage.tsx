import { useCallback, useEffect, useState } from 'react'
import type { Repartidor, Domicilio, DomicilioBatch, Zona, Reporte } from '../types'
import { getRepartidores, importarDomicilios, getBatches, getBatch, deleteBatch, updateDomicilio, exportBatchUrl, getZonas, getReporte } from '../api'
import RepartidorManager from '../components/RepartidorManager'
import ZonaManager from '../components/ZonaManager'
import ReportePanel from '../components/ReportePanel'
import SpreadsheetUpload from '../components/SpreadsheetUpload'
import DomicilioList from '../components/DomicilioList'

export default function DomiciliosPage() {
  const [repartidores, setRepartidores] = useState<Repartidor[]>([])
  const [zonas, setZonas] = useState<Zona[]>([])
  const [reporte, setReporte] = useState<Reporte | null>(null)
  const [batches, setBatches] = useState<DomicilioBatch[]>([])
  const [activeBatch, setActiveBatch] = useState<DomicilioBatch | null>(null)
  const [domicilios, setDomicilios] = useState<Domicilio[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshReporte = useCallback(async () => {
    try {
      setReporte(await getReporte())
    } catch {
      // silently fail on background refresh
    }
  }, [])

  const refreshBase = useCallback(async () => {
    try {
      const [r, z, b] = await Promise.all([getRepartidores(), getZonas(), getBatches()])
      setRepartidores(r)
      setZonas(z)
      setBatches(b)
      if (!activeBatch && b.length > 0) {
        const latest = await getBatch(b[0].id)
        setActiveBatch(latest.batch)
        setDomicilios(latest.domicilios)
      }
      await refreshReporte()
    } catch {
      // silently fail on background refresh
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    refreshBase()
  }, [refreshBase])

  function showError(msg: string) {
    setError(msg)
    setTimeout(() => setError(null), 4500)
  }

  async function handleFile(file: File) {
    setLoading(true)
    setError(null)
    try {
      const result = await importarDomicilios(file)
      setActiveBatch(result.batch)
      setDomicilios(result.domicilios)
      setBatches((prev) => [result.batch, ...prev])
      refreshReporte()
    } catch (e) {
      showError(e instanceof Error ? e.message : 'Error procesando la planilla')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectBatch(id: number) {
    try {
      const result = await getBatch(id)
      setActiveBatch(result.batch)
      setDomicilios(result.domicilios)
    } catch {
      showError('No se pudo cargar el lote')
    }
  }

  async function handleDeleteBatch(id: number) {
    try {
      await deleteBatch(id)
      const remaining = batches.filter((b) => b.id !== id)
      setBatches(remaining)
      if (activeBatch?.id === id) {
        if (remaining.length > 0) {
          handleSelectBatch(remaining[0].id)
        } else {
          setActiveBatch(null)
          setDomicilios([])
        }
      }
      refreshReporte()
    } catch {
      showError('No se pudo eliminar el lote')
    }
  }

  async function handleReassign(domicilioId: number, repartidorId: number | null) {
    const prev = domicilios
    const repartidor = repartidorId != null ? repartidores.find((r) => r.id === repartidorId) : null
    setDomicilios((cur) => cur.map((d) => d.id === domicilioId
      ? { ...d, repartidor_id: repartidorId, repartidor_nombre: repartidor?.nombre ?? null, repartidor_color: repartidor?.color ?? null }
      : d))
    try {
      await updateDomicilio(domicilioId, repartidorId)
      refreshReporte()
    } catch {
      setDomicilios(prev)
      showError('No se pudo reasignar el domicilio')
    }
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      <RepartidorManager repartidores={repartidores} onChange={setRepartidores} />

      <ZonaManager zonas={zonas} onChange={setZonas} />

      <ReportePanel reporte={reporte} />

      <SpreadsheetUpload onFile={handleFile} loading={loading} />

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-200 rounded-xl px-4 py-3 text-sm flex items-center gap-2">
          <span>❌</span> {error}
        </div>
      )}

      {batches.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          {batches.map((b) => (
            <button
              key={b.id}
              onClick={() => handleSelectBatch(b.id)}
              className={`flex-shrink-0 text-xs px-3 py-1.5 rounded-full border ${
                activeBatch?.id === b.id
                  ? 'bg-indigo-600 border-indigo-500 text-white'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              {b.filename} ({b.total})
            </button>
          ))}
        </div>
      )}

      {activeBatch && (
        <div className="bg-slate-800 rounded-2xl p-4 border border-slate-700">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1 truncate">
                {activeBatch.filename}
              </p>
              <p className="text-2xl font-bold text-white">
                {activeBatch.clasificados}/{activeBatch.total} <span className="text-sm font-normal text-slate-400">asignados</span>
              </p>
              {activeBatch.total_comision > 0 && (
                <p className="text-emerald-400 text-sm font-semibold mt-0.5">
                  ${activeBatch.total_comision.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} comisión
                </p>
              )}
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <a
                href={exportBatchUrl(activeBatch.id)}
                className="text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-2 rounded-lg font-semibold"
              >
                Descargar CSV
              </a>
              <button
                onClick={() => handleDeleteBatch(activeBatch.id)}
                className="text-slate-400 hover:text-red-400 p-2 rounded-lg hover:bg-slate-900"
                aria-label="Eliminar lote"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}

      <DomicilioList domicilios={domicilios} repartidores={repartidores} onReassign={handleReassign} />

      <div className="h-4 safe-bottom" />
    </div>
  )
}
