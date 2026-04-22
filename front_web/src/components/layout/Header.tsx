import { LogOut, User } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { formatDate } from '../../lib/helpers'

export function Header() {
  const { user, signOut } = useAuth()
  const [open, setOpen] = useState(false)

  return (
    <header
      className="flex h-14 items-center justify-between px-6"
      style={{
        background: '#0D9488',
        backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\' opacity=\'0.05\'/%3E%3C/svg%3E")',
      }}
    >
      <span className="font-mono text-xs font-medium tracking-widest uppercase text-white/80">
        COSTVIEW ADMIN
      </span>

      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-white/60">{formatDate(new Date().toISOString())}</span>

        <div className="relative">
          <button
            onClick={() => setOpen(v => !v)}
            className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-white/80 hover:bg-white/10 transition-colors"
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
