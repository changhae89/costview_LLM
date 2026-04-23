import { LogOut, User } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { formatDate } from '../../lib/helpers'

export function Header() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)

  return (
    <header className="flex h-14 items-center justify-between px-6 bg-white border-b border-gray-100">
      <span className="text-sm font-semibold text-gray-700 tracking-wide">
        Costview Admin
      </span>

      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-gray-400">{formatDate(new Date().toISOString())}</span>

        <div className="relative">
          <button
            onClick={() => setOpen(v => !v)}
            className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <User size={14} />
            {user?.email?.split('@')[0] ?? 'account'}
          </button>

          {open && (
            <div className="absolute right-0 top-full mt-1 w-44 rounded-xl bg-white shadow-lg border border-gray-100 py-1 z-50">
              <p className="px-3 py-1.5 text-xs text-gray-400 truncate">{user?.email}</p>
              <hr className="my-1 border-gray-100" />
              <button
                onClick={() => { signOut(); setOpen(false) }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <LogOut size={13} />
                로그아웃
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
