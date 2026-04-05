const API_BASE = import.meta.env.VITE_API_BASE_URL

// Routes available per SKU — matches backend seeded data
export const ROUTE_MAP = {
  'SKU-001': 'SUEZ-ROTTERDAM',
  'SKU-002': 'PANAMA-LA',
  'SKU-003': 'TAIWAN-LA',
}

export const SKU_LIST = ['SKU-001', 'SKU-002', 'SKU-003']

export const fetchForecast = async (sku) => {
  const cid = localStorage.getItem('company_id');
  const query = cid ? `sku=${sku}&company_id=${cid}` : `sku=${sku}`;
  const res = await fetch(`${API_BASE}/demand/forecast?${query}`)
  if (!res.ok) throw new Error(`Forecast unavailable for ${sku} — server returned ${res.status}`)
  return res.json()
}

export const fetchDSRatio = async (sku) => {
  const cid = localStorage.getItem('company_id');
  const route = ROUTE_MAP[sku] || 'SUEZ-ROTTERDAM';
  const queryCompany = cid ? `&company_id=${cid}` : '';
  const res = await fetch(`${API_BASE}/supply/ds-ratio?sku=${sku}&route_id=${route}${queryCompany}`)
  if (!res.ok) throw new Error(`D/S ratio unavailable for ${sku} — server returned ${res.status}`)
  return res.json()
}

export const fetchAgentSense = async (query, baselineUnits = 1000) => {
  const controller = new AbortController()
  // 90-second timeout — multi-source pipeline can be slow on cold start
  const timeoutId = setTimeout(() => controller.abort(), 90_000)
  try {
    const res = await fetch(`${API_BASE}/demand/agent-sense`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, baseline_units: baselineUnits }),
      signal: controller.signal,
    })
    if (!res.ok) throw new Error(`Agent sensing failed — server returned ${res.status}`)
    return res.json()
  } catch (err) {
    if (err.name === 'AbortError') {
      throw new Error('Market sensing timed out (>90s). The AI pipeline may be rate-limited. Try again in a moment.')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

export const fetchCompanyProfile = async () => {
  // Fallback from localStorage so the page works even if the API is slow/down
  const lsName     = localStorage.getItem('company_name') || ''
  const lsIndustry = localStorage.getItem('company_industry') || ''
  const cid        = localStorage.getItem('company_id')

  try {
    const query = cid ? `?company_id=${cid}` : ''
    const res = await fetch(`${API_BASE}/onboarding/profile${query}`)
    if (!res.ok) throw new Error('profile fetch failed')
    const data = await res.json()
    // Merge localStorage values as fallback so name/industry is always present
    return {
      ...data,
      name:     data.name     || lsName,
      industry: data.industry || lsIndustry,
    }
  } catch {
    // Server unreachable — return what we have in localStorage
    return { id: cid ? parseInt(cid) : null, name: lsName, industry: lsIndustry, skus: [] }
  }
}
