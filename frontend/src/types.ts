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

// ---------------------------------------------------------------------------
// Domicilios
// ---------------------------------------------------------------------------

export type RepartidorColor =
  | 'orange' | 'green' | 'blue' | 'purple' | 'pink' | 'yellow' | 'red' | 'teal' | 'indigo' | 'slate'

export interface Repartidor {
  id: number
  nombre: string
  color: RepartidorColor
  zonas: string
}

export interface Domicilio {
  id: number
  batch_id: number
  direccion: string
  cliente: string
  telefono: string
  zona_detectada: string
  repartidor_id: number | null
  repartidor_nombre: string | null
  repartidor_color: RepartidorColor | null
  confianza: number
  created_at: string
}

export interface DomicilioBatch {
  id: number
  filename: string
  total: number
  clasificados: number
  created_at: string
}

export interface DomicilioImportResult {
  batch: DomicilioBatch
  domicilios: Domicilio[]
}

export const COLOR_CONFIG: Record<RepartidorColor, { dot: string; bg: string; border: string; text: string; badge: string }> = {
  orange: { dot: 'bg-orange-500', bg: 'bg-orange-950', border: 'border-orange-700', text: 'text-orange-400', badge: 'bg-orange-800 text-orange-200' },
  green: { dot: 'bg-green-500', bg: 'bg-green-950', border: 'border-green-700', text: 'text-green-400', badge: 'bg-green-800 text-green-200' },
  blue: { dot: 'bg-blue-500', bg: 'bg-blue-950', border: 'border-blue-700', text: 'text-blue-400', badge: 'bg-blue-800 text-blue-200' },
  purple: { dot: 'bg-purple-500', bg: 'bg-purple-950', border: 'border-purple-700', text: 'text-purple-400', badge: 'bg-purple-800 text-purple-200' },
  pink: { dot: 'bg-pink-500', bg: 'bg-pink-950', border: 'border-pink-700', text: 'text-pink-400', badge: 'bg-pink-800 text-pink-200' },
  yellow: { dot: 'bg-yellow-500', bg: 'bg-yellow-950', border: 'border-yellow-700', text: 'text-yellow-400', badge: 'bg-yellow-800 text-yellow-200' },
  red: { dot: 'bg-red-500', bg: 'bg-red-950', border: 'border-red-700', text: 'text-red-400', badge: 'bg-red-800 text-red-200' },
  teal: { dot: 'bg-teal-500', bg: 'bg-teal-950', border: 'border-teal-700', text: 'text-teal-400', badge: 'bg-teal-800 text-teal-200' },
  indigo: { dot: 'bg-indigo-500', bg: 'bg-indigo-950', border: 'border-indigo-700', text: 'text-indigo-400', badge: 'bg-indigo-800 text-indigo-200' },
  slate: { dot: 'bg-slate-500', bg: 'bg-slate-800', border: 'border-slate-600', text: 'text-slate-400', badge: 'bg-slate-700 text-slate-300' },
}

export const COLOR_OPTIONS: RepartidorColor[] = [
  'orange', 'green', 'blue', 'purple', 'pink', 'yellow', 'red', 'teal', 'indigo', 'slate',
]
