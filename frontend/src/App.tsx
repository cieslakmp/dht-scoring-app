import { Routes, Route, NavLink } from 'react-router-dom'
import PilotsPage from './pages/PilotsPage'
import TaskPage from './pages/TaskPage'
import FlightsPage from './pages/FlightsPage'
import ResultsPage from './pages/ResultsPage'

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded text-sm font-medium transition-colors ${
    isActive
      ? 'bg-sky-700 text-white'
      : 'text-sky-100 hover:bg-sky-600 hover:text-white'
  }`

export default function App() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-sky-800 text-white shadow">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-6">
          <span className="text-lg font-bold tracking-wide">DHT Scoring</span>
          <nav className="flex gap-2">
            <NavLink to="/pilots" className={navClass}>Pilots</NavLink>
            <NavLink to="/task" className={navClass}>Task</NavLink>
            <NavLink to="/flights" className={navClass}>Flights</NavLink>
            <NavLink to="/results" className={navClass}>Results</NavLink>
          </nav>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<PilotsPage />} />
          <Route path="/pilots" element={<PilotsPage />} />
          <Route path="/task" element={<TaskPage />} />
          <Route path="/flights" element={<FlightsPage />} />
          <Route path="/results" element={<ResultsPage />} />
        </Routes>
      </main>
    </div>
  )
}
