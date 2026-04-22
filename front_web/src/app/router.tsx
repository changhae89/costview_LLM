import { createBrowserRouter } from 'react-router-dom'
import { AppLayout } from '../components/layout/AppLayout'
import { RequireAuth, RequireAdmin } from '../components/layout/RequireAuth'
import { LoginPage } from '../pages/LoginPage'
import { DashboardPage } from '../pages/DashboardPage'
import { NewsPage } from '../pages/NewsPage'
import { CausalPage } from '../pages/CausalPage'
import { IndicatorPage } from '../pages/IndicatorPage'
import { CategoryPage } from '../pages/CategoryPage'
import { ConsumerItemPage } from '../pages/ConsumerItemPage'

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [{
      element: <AppLayout />,
      children: [
        { path: '/',           element: <DashboardPage /> },
        { path: '/news',       element: <NewsPage /> },
        { path: '/causal',     element: <CausalPage /> },
        { path: '/indicators', element: <IndicatorPage /> },
        {
          element: <RequireAdmin />,
          children: [
            { path: '/settings/categories',     element: <CategoryPage /> },
            { path: '/settings/consumer-items', element: <ConsumerItemPage /> },
          ],
        },
      ],
    }],
  },
])
