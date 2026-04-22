import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

export function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex h-screen items-center justify-center text-textMuted">로딩 중...</div>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}

export function RequireAdmin() {
  const { isAdmin, loading } = useAuth()
  if (loading) return null
  if (!isAdmin) return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-textMuted">
      <span className="text-4xl">🔒</span>
      <p className="font-semibold">접근 권한이 없습니다.</p>
      <p className="text-sm">관리자에게 문의하세요.</p>
    </div>
  )
  return <Outlet />
}
