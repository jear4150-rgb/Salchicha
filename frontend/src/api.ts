import type { Ticket, Summary } from './types'

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
