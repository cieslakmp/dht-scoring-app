import { useState, lazy, Suspense } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTasks, createTask, updateTask, getBarrels, importCupFile,
  Task, TurnpointIn,
} from '../services/api'

const TaskMap = lazy(() => import('../components/TaskMap'))

const today = () => new Date().toISOString().slice(0, 10)

export default function TaskPage() {
  const qc = useQueryClient()
  const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const selected = tasks.find(t => t.id === selectedId) ?? null
  const { data: barrels = [] } = useQuery({
    queryKey: ['barrels', selectedId],
    queryFn: () => getBarrels(selectedId!),
    enabled: selectedId !== null,
  })

  // ── New task form ────────────────────────────────────────────────────────
  const [date, setDate] = useState(today())
  const [windSpeed, setWindSpeed] = useState(0)
  const [windDir, setWindDir] = useState(0)
  const [waf, setWaf] = useState(1.0)
  const [notes, setNotes] = useState('')
  const [tpRows, setTpRows] = useState<TurnpointIn[]>([
    { name: '', lat: 0, lon: 0, order: 0 },
    { name: '', lat: 0, lon: 0, order: 1 },
    { name: '', lat: 0, lon: 0, order: 2 },
  ])
  const [error, setError] = useState('')

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['tasks'] })
    qc.invalidateQueries({ queryKey: ['barrels'] })
  }

  const create = useMutation({
    mutationFn: () => createTask({
      date, wind_speed: windSpeed, wind_direction: windDir,
      wind_adjustment_factor: waf, notes,
      turnpoints: tpRows.filter(r => r.name),
    }),
    onSuccess: (t) => { invalidate(); setSelectedId(t.id); setError('') },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Create failed'),
  })

  const patchWind = useMutation({
    mutationFn: () => updateTask(selectedId!, {
      wind_speed: windSpeed, wind_direction: windDir, wind_adjustment_factor: waf,
    }),
    onSuccess: invalidate,
  })

  const importCup = useMutation({
    mutationFn: (file: File) => importCupFile(file, windSpeed, windDir, waf),
    onSuccess: (t) => { invalidate(); setSelectedId(t.id); setError('') },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Import failed'),
  })

  const addRow = () =>
    setTpRows(r => [...r, { name: '', lat: 0, lon: 0, order: r.length }])

  const removeRow = (i: number) =>
    setTpRows(r => r.filter((_, j) => j !== i).map((tp, j) => ({ ...tp, order: j })))

  const updateRow = (i: number, key: keyof TurnpointIn, val: string) =>
    setTpRows(r => r.map((tp, j) =>
      j === i ? { ...tp, [key]: key === 'name' ? val : parseFloat(val) || 0 } : tp
    ))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Task Definition</h1>

      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left: form */}
        <div className="space-y-4">

          {/* Task selector */}
          {tasks.length > 0 && (
            <div className="bg-white rounded-xl shadow p-4">
              <label className="block text-sm font-semibold text-slate-700 mb-1">Load existing task</label>
              <select value={selectedId ?? ''} onChange={e => setSelectedId(Number(e.target.value))}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm">
                <option value="">— select —</option>
                {tasks.map(t => (
                  <option key={t.id} value={t.id}>{t.date} (DTD: {t.declared_task_distance?.toFixed(1)} km)</option>
                ))}
              </select>
            </div>
          )}

          {/* Wind + WAF */}
          <div className="bg-white rounded-xl shadow p-4 space-y-3">
            <h2 className="font-semibold text-slate-700">Wind &amp; Conditions</h2>
            <div className="grid grid-cols-3 gap-3">
              <label className="text-xs text-slate-500 space-y-1">
                <span>Speed (km/h)</span>
                <input type="number" value={windSpeed} min={0}
                  onChange={e => setWindSpeed(parseFloat(e.target.value) || 0)}
                  className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm" />
              </label>
              <label className="text-xs text-slate-500 space-y-1">
                <span>Direction (°)</span>
                <input type="number" value={windDir} min={0} max={359}
                  onChange={e => setWindDir(parseFloat(e.target.value) || 0)}
                  className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm" />
              </label>
              <label className="text-xs text-slate-500 space-y-1">
                <span>Wind Adj. Factor</span>
                <input type="number" value={waf} step={0.01} min={0.5} max={1.5}
                  onChange={e => setWaf(parseFloat(e.target.value) || 1)}
                  className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm" />
              </label>
            </div>
            {selectedId && (
              <button onClick={() => patchWind.mutate()} disabled={patchWind.isPending}
                className="text-sm bg-amber-500 text-white px-3 py-1.5 rounded hover:bg-amber-600 disabled:opacity-50">
                Update wind on selected task
              </button>
            )}
          </div>

          {/* Turnpoints */}
          <div className="bg-white rounded-xl shadow p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-slate-700">Turnpoints</h2>
              <label className="cursor-pointer text-xs bg-slate-600 text-white px-3 py-1.5 rounded hover:bg-slate-700">
                Import .cup
                <input type="file" accept=".cup" className="hidden"
                  onChange={e => { if (e.target.files?.[0]) importCup.mutate(e.target.files[0]); e.target.value = '' }} />
              </label>
            </div>

            <div className="space-y-2">
              {tpRows.map((tp, i) => (
                <div key={i} className="flex gap-2 items-center">
                  <span className="text-xs text-slate-400 w-14 shrink-0">
                    {i === 0 ? 'Start' : i === tpRows.length - 1 ? 'Finish' : `TP ${i}`}
                  </span>
                  <input value={tp.name} onChange={e => updateRow(i, 'name', e.target.value)}
                    placeholder="Name" className="flex-1 border border-slate-300 rounded px-2 py-1 text-sm" />
                  <input type="number" value={tp.lat || ''} onChange={e => updateRow(i, 'lat', e.target.value)}
                    placeholder="Lat" step={0.0001}
                    className="w-24 border border-slate-300 rounded px-2 py-1 text-sm" />
                  <input type="number" value={tp.lon || ''} onChange={e => updateRow(i, 'lon', e.target.value)}
                    placeholder="Lon" step={0.0001}
                    className="w-24 border border-slate-300 rounded px-2 py-1 text-sm" />
                  {tpRows.length > 2 && (
                    <button onClick={() => removeRow(i)} className="text-red-400 hover:text-red-600 text-lg leading-none">×</button>
                  )}
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <button onClick={addRow}
                className="text-sm text-sky-600 hover:underline">+ Add TP</button>
            </div>

            <div className="flex gap-3 items-center">
              <input value={date} type="date" onChange={e => setDate(e.target.value)}
                className="border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <input value={notes} onChange={e => setNotes(e.target.value)} placeholder="Notes (optional)"
                className="flex-1 border border-slate-300 rounded px-2 py-1.5 text-sm" />
              <button onClick={() => create.mutate()} disabled={create.isPending}
                className="bg-sky-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-sky-700 disabled:opacity-50">
                {create.isPending ? 'Creating…' : 'Create Task'}
              </button>
            </div>
          </div>
        </div>

        {/* Right: map + barrels */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl shadow overflow-hidden" style={{ height: 380 }}>
            <Suspense fallback={<div className="h-full flex items-center justify-center text-slate-400">Loading map…</div>}>
              <TaskMap
                turnpoints={selected?.turnpoints ?? []}
                barrels={barrels}
              />
            </Suspense>
          </div>

          {selected && (
            <div className="bg-white rounded-xl shadow p-4">
              <h2 className="font-semibold text-slate-700 mb-3">Task Summary</h2>
              <div className="grid grid-cols-2 gap-2 text-sm mb-4">
                <div className="text-slate-500">Declared Distance</div>
                <div className="font-semibold">{selected.declared_task_distance?.toFixed(1) ?? '—'} km</div>
                <div className="text-slate-500">Handicapped Distance</div>
                <div className="font-semibold text-sky-700">{selected.handicapped_task_distance?.toFixed(1) ?? '—'} km</div>
                <div className="text-slate-500">Wind Adj. Factor</div>
                <div>{selected.wind_adjustment_factor}</div>
              </div>

              {barrels.length > 0 && (
                <>
                  <h3 className="text-sm font-semibold text-slate-600 mb-2">Barrel Sizes per Pilot</h3>
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50">
                      <tr>
                        {['Pilot', 'Glider', 'H/C', 'Barrel (km)', 'Target FD (km)'].map(h => (
                          <th key={h} className="px-2 py-1 text-left text-slate-500 font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {barrels.map(b => (
                        <tr key={b.pilot.id} className="border-t border-slate-100">
                          <td className="px-2 py-1">{b.pilot.name}</td>
                          <td className="px-2 py-1 text-slate-500">{b.pilot.glider_type}</td>
                          <td className="px-2 py-1 font-semibold">{b.pilot.handicap}</td>
                          <td className="px-2 py-1 font-mono">{b.barrel_radius_km.toFixed(2)}</td>
                          <td className="px-2 py-1 font-mono">{b.target_flown_distance.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
