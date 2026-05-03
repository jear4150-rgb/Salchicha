export type TipoPago = 'efectivo' | 'tarjeta' | 'transferencia' | 'otro'

export interface Ticket {
  id: number
  monto: number
  tipo_pago: TipoPago
  descripcion: string
  imagen_path: string
  fecha: string
  created_at: string
}

export interface Summary {
  efectivo: number
  tarjeta: number
  transferencia: number
  otro: number
  total: number
  cantidad_tickets: number
}

export const TIPO_CONFIG: Record<TipoPago, { label: string; icon: string; color: string; bg: string; border: string; badge: string }> = {
  efectivo: {
    label: 'Efectivo',
    icon: '💵',
    color: 'text-green-400',
    bg: 'bg-green-950',
    border: 'border-green-700',
    badge: 'bg-green-800 text-green-200',
  },
  tarjeta: {
    label: 'Tarjeta',
    icon: '💳',
    color: 'text-blue-400',
    bg: 'bg-blue-950',
    border: 'border-blue-700',
    badge: 'bg-blue-800 text-blue-200',
  },
  transferencia: {
    label: 'Transferencia',
    icon: '📲',
    color: 'text-purple-400',
    bg: 'bg-purple-950',
    border: 'border-purple-700',
    badge: 'bg-purple-800 text-purple-200',
  },
  otro: {
    label: 'Otro',
    icon: '🔖',
    color: 'text-orange-400',
    bg: 'bg-orange-950',
    border: 'border-orange-700',
    badge: 'bg-orange-800 text-orange-200',
  },
}
