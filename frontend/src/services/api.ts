import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Types ──────────────────────────────────────────────────────────────────

export interface Pilot {
  id: number
  name: string
  glider_type: string
  registration: string
  handicap: number
}

export interface TurnpointOut {
  id: number
  name: string
  lat: number
  lon: number
}

export interface TaskTurnpointOut {
  order: number
  turnpoint: TurnpointOut
  leg_distance: number | null
}

export interface Task {
  id: number
  date: string
  declared_task_distance: number | null
  wind_speed: number
  wind_direction: number
  wind_adjustment_factor: number
  handicapped_task_distance: number | null
  notes: string | null
  turnpoints: TaskTurnpointOut[]
}

export interface BarrelOut {
  pilot: Pilot
  barrel_radius_km: number
  target_flown_distance: number
}

export interface Flight {
  id: number
  task_id: number
  pilot_id: number | null
  igc_filename: string
  igc_registration: string | null
  igc_glider_type: string | null
  start_time: string | null
  finish_time: string | null
  task_time_seconds: number | null
  raw_distance: number | null
  marking_distance: number | null
  finisher: boolean | null
  handicapped_speed: number | null
  day_score: number | null
  pilot: Pilot | null
}

export interface ResultRow {
  position: number
  pilot_name: string
  glider_type: string
  registration: string
  handicap: number
  marking_distance: number | null
  handicapped_speed: number | null
  finisher: boolean
  day_score: number
}

export interface TurnpointIn {
  name: string
  lat: number
  lon: number
  order: number
}

export interface TaskCreate {
  date: string
  wind_speed: number
  wind_direction: number
  wind_adjustment_factor: number
  notes?: string
  turnpoints: TurnpointIn[]
}

// ── Pilots ─────────────────────────────────────────────────────────────────

export const getPilots = () => api.get<Pilot[]>('/pilots').then(r => r.data)

export const createPilot = (data: Omit<Pilot, 'id'>) =>
  api.post<Pilot>('/pilots', data).then(r => r.data)

export const updatePilot = (id: number, data: Partial<Omit<Pilot, 'id'>>) =>
  api.put<Pilot>(`/pilots/${id}`, data).then(r => r.data)

export const deletePilot = (id: number) =>
  api.delete(`/pilots/${id}`)

export const importPilotsCSV = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<Pilot[]>('/pilots/import', form).then(r => r.data)
}

// ── Tasks ──────────────────────────────────────────────────────────────────

export const getTasks = () => api.get<Task[]>('/tasks').then(r => r.data)

export const getTask = (id: number) =>
  api.get<Task>(`/tasks/${id}`).then(r => r.data)

export const createTask = (data: TaskCreate) =>
  api.post<Task>('/tasks', data).then(r => r.data)

export const updateTask = (id: number, data: Partial<Task>) =>
  api.put<Task>(`/tasks/${id}`, data).then(r => r.data)

export const importCupFile = (file: File, wind_speed = 0, wind_direction = 0, wind_adjustment_factor = 1) => {
  const form = new FormData()
  form.append('file', file)
  return api.post<Task>(
    `/tasks/import-cup?wind_speed=${wind_speed}&wind_direction=${wind_direction}&wind_adjustment_factor=${wind_adjustment_factor}`,
    form
  ).then(r => r.data)
}

export const getBarrels = (taskId: number) =>
  api.get<BarrelOut[]>(`/tasks/${taskId}/barrels`).then(r => r.data)

// ── Flights / Scoring ──────────────────────────────────────────────────────

export const getFlights = (taskId: number) =>
  api.get<Flight[]>(`/tasks/${taskId}/flights`).then(r => r.data)

export const uploadFlights = (taskId: number, files: File[]) => {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  return api.post<Flight[]>(`/tasks/${taskId}/flights`, form).then(r => r.data)
}

export const assignPilot = (taskId: number, flightId: number, pilotId: number) =>
  api.put<Flight>(`/tasks/${taskId}/flights/${flightId}/assign`, { pilot_id: pilotId }).then(r => r.data)

export const runScoring = (taskId: number) =>
  api.post<Flight[]>(`/tasks/${taskId}/score`).then(r => r.data)

export const getResults = (taskId: number) =>
  api.get<ResultRow[]>(`/tasks/${taskId}/results`).then(r => r.data)

export const getResultsCsvUrl = (taskId: number) =>
  `/api/tasks/${taskId}/results/csv`
