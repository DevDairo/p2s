const BASE = '/api/v1'

export async function searchSongs(q) {
  try {
    const res  = await fetch(`${BASE}/search?q=${encodeURIComponent(q)}`)
    const data = await res.json()
    return data.results || []
  } catch { return [] }
}

export async function startDownload(url, format = 'm4a') {
  try {
    const res  = await fetch(`${BASE}/download`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ url, format }),
    })
    return await res.json()
  } catch (e) {
    return { error: e.message }
  }
}

export async function fetchLibrary() {
  try {
    const res  = await fetch(`${BASE}/library`)
    const data = await res.json()
    return data.songs || []
  } catch { return [] }
}

export async function deleteSong(id) {
  const res = await fetch(`${BASE}/library/${id}`, { method: 'DELETE' })
  return res.ok
}
