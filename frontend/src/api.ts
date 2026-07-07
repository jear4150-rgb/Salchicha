import type { Ticket, Summary, Repartidor, RepartidorColor, DomicilioBatch, DomicilioImportResult, Domicilio, Zona, Reporte } from './types'

const BASE = '/api'

export async function uploadTicket(file: File): Promise<Ticket> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/tickets`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error desconocido' }))
    throw new Error(err.detail || 'Error procesando ticket')
  }
  return res.json()
}

export async function getTickets(): Promise<Ticket[]> {
  const res = await fetch(`${BASE}/tickets`)
  if (!res.ok) throw new Error('Error obteniendo tickets')
  return res.json()
}

export async function deleteTicket(id: number): Promise<void> {
  const res = await fetch(`${BASE}/tickets/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Error eliminando ticket')
}

export async function getSummary(): Promise<Summary> {
  const res = await fetch(`${BASE}/summary`)
  if (!res.ok) throw new Error('Error obteniendo resumen')
  return res.json()
}

// ---------------------------------------------------------------------------
// Repartidores
// ---------------------------------------------------------------------------

export async function getRepartidores(): Promise<Repartidor[]> {
  const res = await fetch(`${BASE}/repartidores`)
  if (!res.ok) throw new Error('Error obteniendo repartidores')
  return res.json()
}

export async function createRepartidor(nombre: string, color: RepartidorColor, zonas: string): Promise<Repartidor> {
  const res = await fetch(`${BASE}/repartidores`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, color, zonas }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error creando repartidor' }))
    throw new Error(err.detail || 'Error creando repartidor')
  }
  return res.json()
}

export async function updateRepartidor(id: number, changes: Partial<Pick<Repartidor, 'nombre' | 'color' | 'zonas'>>): Promise<Repartidor> {
  const res = await fetch(`${BASE}/repartidores/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (!res.ok) throw new Error('Error actualizando repartidor')
  return res.json()
}

export async function deleteRepartidor(id: number): Promise<void> {
  const res = await fetch(`${BASE}/repartidores/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Error eliminando repartidor')
}

// ---------------------------------------------------------------------------
// Domicilios
// ---------------------------------------------------------------------------

export async function importarDomicilios(file: File): Promise<DomicilioImportResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/domicilios/importar`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error procesando la planilla' }))
    throw new Error(err.detail || 'Error procesando la planilla')
  }
  return res.json()
}

export async function getBatches(): Promise<DomicilioBatch[]> {
  const res = await fetch(`${BASE}/domicilios/batches`)
  if (!res.ok) throw new Error('Error obteniendo lotes')
  return res.json()
}

export async function getBatch(id: number): Promise<DomicilioImportResult> {
  const res = await fetch(`${BASE}/domicilios/batches/${id}`)
  if (!res.ok) throw new Error('Error obteniendo lote')
  return res.json()
}

export async function deleteBatch(id: number): Promise<void> {
  const res = await fetch(`${BASE}/domicilios/batches/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Error eliminando lote')
}

export async function updateDomicilio(id: number, repartidorId: number | null): Promise<Domicilio> {
  const res = await fetch(`${BASE}/domicilios/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repartidor_id: repartidorId }),
  })
  if (!res.ok) throw new Error('Error actualizando domicilio')
  return res.json()
}

export function exportBatchUrl(id: number): string {
  return `${BASE}/domicilios/batches/${id}/export`
}

export async function getReporte(): Promise<Reporte> {
  const res = await fetch(`${BASE}/domicilios/reporte`)
  if (!res.ok) throw new Error('Error obteniendo el reporte')
  return res.json()
}

// ---------------------------------------------------------------------------
// Zonas (valor de comisión por zona)
// ---------------------------------------------------------------------------

export async function getZonas(): Promise<Zona[]> {
  const res = await fetch(`${BASE}/zonas`)
  if (!res.ok) throw new Error('Error obteniendo zonas')
  return res.json()
}

export async function createZona(nombre: string, valor: number): Promise<Zona> {
  const res = await fetch(`${BASE}/zonas`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nombre, valor }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Error creando zona' }))
    throw new Error(err.detail || 'Error creando zona')
  }
  return res.json()
}

export async function updateZona(id: number, changes: Partial<Pick<Zona, 'nombre' | 'valor'>>): Promise<Zona> {
  const res = await fetch(`${BASE}/zonas/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
  if (!res.ok) throw new Error('Error actualizando zona')
  return res.json()
}

export async function deleteZona(id: number): Promise<void> {
  const res = await fetch(`${BASE}/zonas/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Error eliminando zona')
}
