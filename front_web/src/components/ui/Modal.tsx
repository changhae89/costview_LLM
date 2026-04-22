import { X } from 'lucide-react'
import { type ReactNode } from 'react'

export function Modal({ open, onClose, title, children }: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

export function ConfirmDialog({ open, onClose, onConfirm, title, message, confirmLabel = '확인', danger = false }: {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title?: string
  message: string
  confirmLabel?: string
  danger?: boolean
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative rounded-2xl bg-white shadow-2xl p-6 w-80">
        {title && <p className="font-semibold text-gray-900 mb-2">{title}</p>}
        <p className="text-sm text-gray-700 mb-5">{message}</p>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">취소</button>
          <button onClick={onConfirm}
            className={`px-4 py-2 text-sm text-white rounded-lg ${danger ? 'bg-red-500 hover:bg-red-600' : 'bg-primary hover:bg-primary/90'}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
