import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Newspaper, GitBranch, BarChart2, Tag, ShoppingBag, BookOpen } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/',           icon: LayoutDashboard, label: '대시보드' },
  { to: '/briefing',   icon: BookOpen,        label: '오늘의 물가 브리핑' },
  { to: '/news',       icon: Newspaper,       label: '뉴스 관리' },
  { to: '/causal',     icon: GitBranch,       label: '물가 영향 분석' },
  { to: '/indicators', icon: BarChart2,       label: '경제 지표' },
]
const ADMIN_NAV = [
  { to: '/settings/categories',     icon: Tag,         label: '카테고리' },
  { to: '/settings/consumer-items', icon: ShoppingBag, label: '품목' },
]

export function Sidebar() {
  const { isAdmin } = useAuth()

  return (
    <aside className="flex h-screen w-60 flex-shrink-0 flex-col bg-white border-r border-gray-100">
      <div className="flex h-14 items-center px-5 border-b border-gray-100">
        <span className="text-base font-bold text-gray-900 tracking-tight">
          Costview
        </span>
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-0.5 px-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                    isActive
                      ? 'bg-surface text-primary-dark border-l-2 border-primary pl-[10px]'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                  }`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>

        {isAdmin && (
          <>
            <div className="mx-4 my-3 border-t border-gray-100" />
            <p className="px-5 pb-1 text-xs text-gray-400 uppercase tracking-wider">설정</p>
            <ul className="space-y-0.5 px-2">
              {ADMIN_NAV.map(({ to, icon: Icon, label }) => (
                <li key={to}>
                  <NavLink
                    to={to}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                        isActive
                          ? 'bg-surface text-primary-dark border-l-2 border-primary pl-[10px]'
                          : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700'
                      }`
                    }
                  >
                    <Icon size={16} />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </>
        )}
      </nav>
    </aside>
  )
}
