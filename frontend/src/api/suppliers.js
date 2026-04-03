const API_BASE = import.meta.env.VITE_API_BASE_URL

export const fetchSupplierGraph = async () => {
  const res = await fetch(`${API_BASE}/suppliers/graph`)
  if (!res.ok) throw new Error(`Supplier graph unavailable (${res.status}) — check Neo4j connection`)
  return res.json()
}

export const fetchSupplierNarrative = async (supplierId, companyName) => {
  const res = await fetch(
    `${API_BASE}/suppliers/${supplierId}/narrative?company_name=${encodeURIComponent(companyName)}`,
    { method: 'POST' }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Narrative generation failed (${res.status})`)
  }
  return res.json()
}
