import { getActiveApiBase } from './api'

export type SettingsSectionInfo = {
  id: string
  label: string
  path: string
  filename: string
}

export type SettingsDocument = {
  section: string
  label: string
  path: string
  content: string
  data: Record<string, unknown>
}

async function requestJson(path: string, init?: RequestInit) {
  const res = await fetch(`${getActiveApiBase()}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    let detail = text.trim()
    if (detail) {
      try {
        const parsed = JSON.parse(detail)
        if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
          detail = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail)
        }
      } catch {
        // Keep the raw response body when it is not JSON.
      }
    }
    throw new Error(detail ? `HTTP ${res.status}: ${detail}` : `HTTP ${res.status}`)
  }
  return res.json()
}

export async function listSettingsSections(): Promise<SettingsSectionInfo[]> {
  const res = await requestJson('/api/settings')
  return (res.sections || []) as SettingsSectionInfo[]
}

export async function getSettingsSection(section: string): Promise<SettingsDocument> {
  return requestJson(`/api/settings/${encodeURIComponent(section)}`) as Promise<SettingsDocument>
}

export async function updateSettingsSection(section: string, content: string): Promise<SettingsDocument> {
  return requestJson(`/api/settings/${encodeURIComponent(section)}`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  }) as Promise<SettingsDocument>
}
