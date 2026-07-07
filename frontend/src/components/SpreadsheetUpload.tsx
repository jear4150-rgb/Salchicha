import { useRef } from 'react'

interface Props {
  onFile: (file: File) => void
  loading: boolean
}

export default function SpreadsheetUpload({ onFile, loading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onFile(file)
    e.target.value = ''
  }

  return (
    <div>
      <button
        onClick={() => inputRef.current?.click()}
        disabled={loading}
        className="w-full flex items-center justify-center gap-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-2xl py-5 px-4 transition-colors active:scale-95"
      >
        {loading ? (
          <svg className="w-6 h-6 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg className="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
          </svg>
        )}
        <span className="text-sm">{loading ? 'Clasificando domicilios…' : 'Subir planilla (CSV / Excel)'}</span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx,.xlsm"
        className="hidden"
        onChange={handleChange}
      />
    </div>
  )
}
