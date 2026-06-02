import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getTasks, getResults, getResultsCsvUrl } from '../services/api'

export default function ResultsPage() {
  const [taskId, setTaskId] = useState<number | null>(null)
  const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: results = [], isLoading } = useQuery({
    queryKey: ['results', taskId],
    queryFn: () => getResults(taskId!),
    enabled: taskId !== null,
  })

  const task = tasks.find(t => t.id === taskId)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Results</h1>
        {taskId && results.length > 0 && (
          <a href={getResultsCsvUrl(taskId)} download
            className="bg-slate-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-700">
            Export CSV
          </a>
        )}
      </div>

      <div className="bg-white rounded-xl shadow p-4">
        <label className="text-sm font-semibold text-slate-700 space-y-1">
          <span>Select Task</span>
          <select value={taskId ?? ''} onChange={e => setTaskId(Number(e.target.value))}
            className="block w-64 border border-slate-300 rounded px-3 py-2 text-sm mt-1">
            <option value="">— select a task —</option>
            {tasks.map(t => (
              <option key={t.id} value={t.id}>
                {t.date} (DTD: {t.declared_task_distance?.toFixed(1)} km)
              </option>
            ))}
          </select>
        </label>
      </div>

      {task && (
        <div className="grid grid-cols-3 gap-4 text-sm">
          {[
            { label: 'Date', value: task.date },
            { label: 'Declared Distance', value: `${task.declared_task_distance?.toFixed(1) ?? '—'} km` },
            { label: 'Handicapped Distance', value: `${task.handicapped_task_distance?.toFixed(1) ?? '—'} km` },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white rounded-xl shadow p-3">
              <div className="text-slate-500 text-xs">{label}</div>
              <div className="font-bold text-slate-800 mt-0.5">{value}</div>
            </div>
          ))}
        </div>
      )}

      {taskId && (
        <div className="bg-white rounded-xl shadow overflow-hidden">
          {isLoading ? (
            <p className="p-4 text-slate-500">Loading…</p>
          ) : results.length === 0 ? (
            <p className="p-4 text-slate-400 text-sm">No scored results yet. Run scoring on the Flights page first.</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600 text-left">
                <tr>
                  {['Pos', 'Pilot', 'Glider', 'Reg', 'H/C', 'Marking Dist', 'Speed', 'Status', 'Score'].map(h => (
                    <th key={h} className="px-3 py-3 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={i} className={`${i % 2 === 0 ? 'bg-white' : 'bg-slate-50'} ${r.position === 1 ? 'ring-1 ring-inset ring-amber-300' : ''}`}>
                    <td className="px-3 py-2 font-bold text-center">
                      {r.position === 1 ? '🥇' : r.position === 2 ? '🥈' : r.position === 3 ? '🥉' : r.position}
                    </td>
                    <td className="px-3 py-2 font-medium">{r.pilot_name}</td>
                    <td className="px-3 py-2 text-slate-500">{r.glider_type}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.registration}</td>
                    <td className="px-3 py-2">{r.handicap}</td>
                    <td className="px-3 py-2">{r.marking_distance?.toFixed(1) ?? '—'} km</td>
                    <td className="px-3 py-2">{r.handicapped_speed?.toFixed(1) ?? '—'} km/h</td>
                    <td className="px-3 py-2">
                      {r.finisher
                        ? <span className="text-emerald-600 font-semibold">Finisher</span>
                        : <span className="text-amber-600">Landout</span>}
                    </td>
                    <td className="px-3 py-2 font-bold text-sky-700 text-base">{r.day_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
