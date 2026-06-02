import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPilots, createPilot, updatePilot, deletePilot, importPilotsCSV, Pilot } from '../services/api'

const empty = { name: '', glider_type: '', registration: '', handicap: 100 }

export default function PilotsPage() {
  const qc = useQueryClient()
  const { data: pilots = [], isLoading } = useQuery({ queryKey: ['pilots'], queryFn: getPilots })

  const [form, setForm] = useState(empty)
  const [editing, setEditing] = useState<number | null>(null)
  const [error, setError] = useState('')

  const invalidate = () => qc.invalidateQueries({ queryKey: ['pilots'] })

  const save = useMutation({
    mutationFn: () =>
      editing
        ? updatePilot(editing, form)
        : createPilot(form),
    onSuccess: () => { invalidate(); setForm(empty); setEditing(null); setError('') },
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Save failed'),
  })

  const remove = useMutation({
    mutationFn: deletePilot,
    onSuccess: invalidate,
  })

  const importCSV = useMutation({
    mutationFn: importPilotsCSV,
    onSuccess: invalidate,
    onError: (e: any) => setError(e.response?.data?.detail ?? 'Import failed'),
  })

  const startEdit = (p: Pilot) => {
    setEditing(p.id)
    setForm({ name: p.name, glider_type: p.glider_type, registration: p.registration, handicap: p.handicap })
  }

  const cancelEdit = () => { setEditing(null); setForm(empty); setError('') }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-800">Pilots &amp; Handicaps</h1>
        <label className="cursor-pointer bg-slate-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-slate-700">
          Import CSV
          <input type="file" accept=".csv" className="hidden"
            onChange={e => { if (e.target.files?.[0]) importCSV.mutate(e.target.files[0]); e.target.value = '' }} />
        </label>
      </div>

      {error && <p className="text-red-600 text-sm bg-red-50 px-3 py-2 rounded">{error}</p>}

      {/* Add / Edit form */}
      <div className="bg-white rounded-xl shadow p-4">
        <h2 className="font-semibold text-slate-700 mb-3">{editing ? 'Edit Pilot' : 'Add Pilot'}</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(['name', 'glider_type', 'registration'] as const).map(f => (
            <input key={f} value={form[f]}
              onChange={e => setForm(p => ({ ...p, [f]: e.target.value }))}
              placeholder={f.replace('_', ' ')}
              className="border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
          ))}
          <input type="number" value={form.handicap} min={60} max={130} step={0.1}
            onChange={e => setForm(p => ({ ...p, handicap: parseFloat(e.target.value) }))}
            placeholder="Handicap"
            className="border border-slate-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-400" />
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={() => save.mutate()} disabled={save.isPending}
            className="bg-sky-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-sky-700 disabled:opacity-50">
            {save.isPending ? 'Saving…' : editing ? 'Update' : 'Add Pilot'}
          </button>
          {editing && <button onClick={cancelEdit} className="text-sm text-slate-500 hover:underline px-2">Cancel</button>}
        </div>
      </div>

      {/* Pilot table */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        {isLoading ? (
          <p className="p-4 text-slate-500">Loading…</p>
        ) : pilots.length === 0 ? (
          <p className="p-4 text-slate-400 text-sm">No pilots yet. Add one above or import a CSV.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-left">
              <tr>
                {['Name', 'Glider', 'Registration', 'Handicap', ''].map(h => (
                  <th key={h} className="px-4 py-3 font-semibold">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pilots.map((p, i) => (
                <tr key={p.id} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                  <td className="px-4 py-2">{p.name}</td>
                  <td className="px-4 py-2 text-slate-600">{p.glider_type}</td>
                  <td className="px-4 py-2 font-mono">{p.registration}</td>
                  <td className="px-4 py-2 font-semibold">{p.handicap}</td>
                  <td className="px-4 py-2 text-right space-x-2">
                    <button onClick={() => startEdit(p)} className="text-sky-600 hover:underline">Edit</button>
                    <button onClick={() => remove.mutate(p.id)} className="text-red-500 hover:underline">Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-slate-400">
        CSV format: <code>name,glider_type,registration,handicap</code> (header row required)
      </p>
    </div>
  )
}
