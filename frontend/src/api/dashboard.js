const API_BASE = import.meta.env.VITE_API_BASE_URL

export const fetchAISLive = async () => {
  const res = await fetch(`${API_BASE}/ais/live`)
  if (!res.ok) throw new Error(`AIS feed unavailable (${res.status}) — showing cached vessel positions`)
  return res.json()
}

export const fetchChokepoints = async () => {
  const res = await fetch(`${API_BASE}/risk/chokepoints`)
  if (!res.ok) throw new Error(`Risk Engine timeout (${res.status}) — chokepoint data unavailable`)
  return res.json()
}

export const fetchDSRatio = async () => {
  const res = await fetch(`${API_BASE}/supply/ds-ratio`)
  if (!res.ok) throw new Error(`D/S ratio feed error (${res.status})`)
  return res.json()
}
