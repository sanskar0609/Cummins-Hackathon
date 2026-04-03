const API_BASE = import.meta.env.VITE_API_BASE_URL

export const CHOKEPOINTS = [
  { id: 'SUEZ-ROTTERDAM',  label: 'Suez Canal',           region: 'Middle East' },
  { id: 'PANAMA-LA',       label: 'Panama Canal',          region: 'Central America' },
  { id: 'TAIWAN-LA',       label: 'Taiwan Strait',         region: 'East Asia' },
  { id: 'MALACCA',         label: 'Strait of Malacca',     region: 'Southeast Asia' },
  { id: 'HORMUZ',          label: 'Strait of Hormuz',      region: 'Persian Gulf' },
  { id: 'BOSPORUS',        label: 'Bosphorus Strait',      region: 'Turkey' },
  { id: 'DOVER',           label: 'Strait of Dover',       region: 'Northern Europe' },
  { id: 'BABELM',          label: 'Bab-el-Mandeb',         region: 'Red Sea' },
]

export const SUPPLIERS = [
  { id: 'SUP-T1-A', label: 'Foxx Assembly',       tier: 'T1' },
  { id: 'SUP-T1-B', label: 'EuroMotor Parts',     tier: 'T1' },
  { id: 'SUP-T1-C', label: 'AmeriCasting',        tier: 'T1' },
  { id: 'SUP-T2-A', label: 'TSMC Advanced',       tier: 'T2' },
  { id: 'SUP-T2-B', label: 'Nvidia IC',           tier: 'T2' },
  { id: 'SUP-T2-C', label: 'Bosch Sensors',       tier: 'T2' },
  { id: 'SUP-T2-D', label: 'Shenzhen Circuits',   tier: 'T2' },
  { id: 'SUP-T3-A', label: 'Aus Mining',          tier: 'T3' },
  { id: 'SUP-T3-B', label: 'Chile Copper Ltd',    tier: 'T3' },
  { id: 'SUP-T3-C', label: 'DRC Cobalt',          tier: 'T3' },
  { id: 'SUP-T3-D', label: 'Lithium Corp',        tier: 'T3' },
]

/**
 * POST /api/v1/simulate/whatif
 * Body: { chokepoint_id, lock_days, supplier_failure_id, demand_spike_percent }
 * Returns: { iterations, probability_of_stockout_percent, avg_nodes_failed_cascading,
 *             estimated_cost_impact_usd, parameters }
 */
export const runSimulation = async (params) => {
  const res = await fetch(`${API_BASE}/simulate/whatif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Simulation engine error (${res.status}) — check backend logs`)
  }
  return res.json()
}
