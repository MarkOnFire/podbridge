import { Outlet, NavLink } from 'react-router-dom'
import StatusBar from './StatusBar'

export default function Layout() {
  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? 'bg-gray-700 text-white'
        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
    }`

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Status Bar */}
      <StatusBar />

      {/* Navigation */}
      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center space-x-4">
              <span className="text-lg font-semibold text-white">
                Editorial Assistant
              </span>
              <span className="text-xs text-gray-500">v3.0</span>
            </div>
            <div className="flex items-center space-x-1">
              <NavLink to="/" className={navLinkClass} end>
                Dashboard
              </NavLink>
              <NavLink to="/queue" className={navLinkClass}>
                Queue
              </NavLink>
              <NavLink to="/projects" className={navLinkClass}>
                Projects
              </NavLink>
              <NavLink to="/settings" className={navLinkClass}>
                Settings
              </NavLink>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  )
}
