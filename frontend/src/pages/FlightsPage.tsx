import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTasks, getFlights, uploadFlights, assignPilot, runScoring,
  getPilots, Flight,
} from '../services/api'

function fmtTime(secs: number | null) {
  if (!secs) return '—'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function FlightsPage() {
  const qc = useQueryClient()
  const [taskId, setTaskId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  const { data: tasks = [] } = useQuery({ queryKey: ['tasks'], queryFn: getTasks })
  const { data: pilots = [] } = useQuery({ queryKey: ['pilots'], queryFn: getPilots })
  const { data: flights = [], isLoading } = useQuery({
    queryKey: ['flights', taskId],
    queryFn: () => getFlights(taskId!),
    enabled: taskId !== null,
  })

  const invalidate = () => qc.invalidateQueries({ queryKey: ['flights', taskId] })

  const upload = useMutation({
    mutationFn: (files: File[]) => uploadFlights(taskId!, files),
    onSuccess: invalidate,
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Upload failed'),
  })

  const assign = useMutation({
    mutationFn: ({ flightId, pilotId }: { flightId: number; pilotId: number }) =>
      assignPilot(taskId!, flightId, pilotId),
    onSuccess: invalidate,
  })

  const score = useMutation({
    mutationFn: () => runScoring(taskId!),
    onSuccess: () => {
      invalidate()
      qc.invalidateQueries({ queryKey: ['results', taskId] })
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Scoring failed'),
  })

  const handleFiles = (files: FileList | null) => {
    if (!files || !taskId) return
    upload.mutate(Array.from(files).filter(f => f.name.toLowerCase().endsWith('.igc')))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-800">Flights</h1>

      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

      {/* Task selector */}
      <div className="bg-white rounded-xl shadow p-4 flex gap-4 items-end">
        <label className="text-sm font-semibold text-slate-700 space-y-1">
          <span>Select Task</span>
          <select value={taskId ?? ''} onChange={e => setTaskId(Number(e.target.value))}
            className="block w-64 border border-slate-300 rounded px-3 py-2 text-sm">
            <option value="">— select a task —</option>
            {tasks.map(t => (
              <option key={t.id} value={t.id}>
                {t.date} (DTD: {t.declared_task_distance?.toFixed(1)} km)
              </option>
            ))}
          </select>
        </label>

        {taskId && (
          <button onClick={() => score.mutate()} disabled={score.isPending || flights.length === 0}
            className="bg-emerald-600 text-white px-5 py-2 rounded text-sm font-medium hover:bg-emerald-700 disabled:opacity-50">
            {score.isPending ? 'Scoring…' : 'Run Scoring'}
          </button>
        )}
      </div>

      {taskId && (
        <>
          {/* Drop zone */}
          <div
            ref={dropRef}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files) }}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragging ? 'border-sky-400 bg-sky-50' : 'border-slate-300 bg-white'
            }`}
          >
            <p className="text-slate-500 text-sm mb-2">Drag &amp; drop IGC files here</p>
            <label className="cursor-pointer bg-sky-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-sky-700">
              Browse
              <input type="file" multiple accept=".igc" className="hidden"
                onChange={e => handleFiles(e.target.files)} />
            </label>
            {upload.isPending && <p className="text-slate-400 text-xs mt-2">Uploading…</p>}
          </div>

          {/* Flights table */}
          <div className="bg-white rounded-xl shadow overflow-hidden">
            {isLoading ? (
              <p className="p-4 text-slate-500">Loading…</p>
            ) : flights.length === 0 ? (
              <p className="p-4 text-slate-400 text-sm">No flights uploaded yet.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 text-left">
                  <tr>
                    {['IGC File', 'IGC Reg', 'Assigned Pilot', 'Status', 'Marking Dist', 'Speed', 'Score'].map(h => (
                      <th key={h} className="px-3 py-3 font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {flights.map((f, i) => (
                    <tr key={f.id} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                      <td className="px-3 py-2 font-mono text-xs text-slate-500 max-w-32 truncate">{f.igc_filename.slice(33)}</td>
                      <td className="px-3 py-2 font-mono text-xs">{f.igc_registration ?? '—'}</td>
                      <td className="px-3 py-2">
                        <select
                          value={f.pilot_id ?? ''}
                          onChange={e => assign.mutate({ flightId: f.id, pilotId: Number(e.target.value) })}
                          className="border border-slate-300 rounded px-2 py-1 text-xs w-36"
                        >
                          <option value="">— assign —</option>
                          {pilots.map(p => (
                            <option key={p.id} value={p.id}>{p.name} ({p.registration})</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-2">
                        {f.finisher === null ? (
                          <span className="text-slate-400 text-xs">Not scored</span>
                        ) : f.finisher ? (
                          <span className="text-emerald-600 font-semibold text-xs">Finisher</span>
                        ) : (
                          <span className="text-amber-600 text-xs">Landout</span>
                        )}
                      </td>
                      <td className="px-3 py-2">{f.marking_distance != null ? `${f.marking_distance.toFixed(1)} km` : '—'}</td>
                      <td className="px-3 py-2">{f.handicapped_speed != null ? `${f.handicapped_speed.toFixed(1)} km/h` : '—'}</td>
                      <td className="px-3 py-2 font-bold">{f.day_score != null ? f.day_score : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}
