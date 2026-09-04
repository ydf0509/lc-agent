const BASE_URL = '/api'

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: getAuthHeaders(),
    ...options,
  })
  if (response.status === 401) {
    localStorage.removeItem('token')
    window.dispatchEvent(new CustomEvent('auth:expired'))
    throw new Error('认证已过期，请重新登录')
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body?.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {}
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return response.json()
}

export const api = {
  health: () => fetchApi<{ status: string; version: string; app_name?: string; config_loaded: boolean }>('/health'),

  getTools: () => fetchApi<{ name: string; group: string; group_description: string; description: string }[]>('/tools'),
  getToolGroups: () => fetchApi<{ id: string; description: string; tools: { name: string; description: string }[]; enabled: boolean }[]>('/tools/groups'),
  toggleToolGroup: (groupId: string) => fetchApi<{ id: string; enabled: boolean }>(`/tools/groups/${groupId}/toggle`, { method: 'POST' }),

  getModels: () => fetchApi<{ id: string; provider: string; base_url: string; context_limit: number }[]>('/models'),

  getMcpServers: () => fetchApi<any[]>('/mcp'),
  refreshMcpServers: () => fetchApi<any[]>('/mcp/refresh', { method: 'POST' }),
  refreshMcpServer: (name: string) => fetchApi<any>(`/mcp/${name}/refresh`, { method: 'POST' }),
  toggleMcpServer: (name: string) => fetchApi<{ name: string; enabled: boolean }>(`/mcp/${name}/toggle`, { method: 'POST' }),
  getSkills: (projectRoot?: string, extraDirs?: string[]) => {
    const params: string[] = []
    if (projectRoot) params.push(`project_root=${encodeURIComponent(projectRoot)}`)
    for (const d of extraDirs || []) {
      if (d && d.trim()) params.push(`extra_dirs=${encodeURIComponent(d.trim())}`)
    }
    const qs = params.length > 0 ? `?${params.join('&')}` : ''
    return fetchApi<any[]>(`/skills${qs}`)
  },
  getSkillDetail: (name: string) => fetchApi<any>(`/skills/${name}`),
  toggleSkill: (name: string) => fetchApi<{ name: string; enabled: boolean }>(`/skills/${name}/toggle`, { method: 'POST' }),

  getAgents: () => fetchApi<any[]>('/agents'),
  createAgent: (data: object) => fetchApi<any>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  updateAgent: (id: string, data: object) => fetchApi<any>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => fetchApi<void>(`/agents/${id}`, { method: 'DELETE' }),
  activateAgent: (id: string) => fetchApi<any>(`/agents/${id}/activate`, { method: 'POST' }),
  checkPaths: (paths: string[]) => fetchApi<{ path: string; exists: boolean }[]>('/check-paths', {
    method: 'POST',
    body: JSON.stringify({ paths }),
  }),

  getSessions: (params?: { days?: number; includeSessionId?: string }) => {
    const qs = new URLSearchParams()
    if (params?.days !== undefined) qs.set('days', String(params.days))
    if (params?.includeSessionId) qs.set('include_session_id', params.includeSessionId)
    const query = qs.toString()
    return fetchApi<any[]>(`/sessions${query ? '?' + query : ''}`)
  },
  createSession: (data: { title?: string; agent_id?: string; model?: string }) =>
    fetchApi<{ id: string; title: string }>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  updateSession: (id: string, data: { title?: string; model?: string; is_pinned?: boolean }) =>
    fetchApi<any>(`/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSession: (id: string) =>
    fetchApi<void>(`/sessions/${id}`, { method: 'DELETE' }),
  getSessionMessages: (id: string, params?: { limit?: number; offset?: number }) => {
    const qs = new URLSearchParams()
    if (params?.limit !== undefined) qs.set('limit', String(params.limit))
    if (params?.offset !== undefined) qs.set('offset', String(params.offset))
    const query = qs.toString()
    return fetchApi<{ total: number; offset: number; limit: number; messages: any[] }>(
      `/sessions/${id}/messages${query ? '?' + query : ''}`
    )
  },
  getMessageTraces: (sessionId: string, messageId: string) =>
    fetchApi<{ traces: any[] }>(`/sessions/${sessionId}/messages/${messageId}/traces`),

  // Automation tasks
  getAutomationTasks: () => fetchApi<any[]>('/automation/tasks'),
  getAutomationTimezone: () => fetchApi<{ timezone: string }>('/automation/timezone'),
  createAutomationTask: (data: object) =>
    fetchApi<any>('/automation/tasks', { method: 'POST', body: JSON.stringify(data) }),
  updateAutomationTask: (id: string, data: object) =>
    fetchApi<any>(`/automation/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAutomationTask: (id: string) =>
    fetchApi<void>(`/automation/tasks/${id}`, { method: 'DELETE' }),
  pauseAutomationTask: (id: string) =>
    fetchApi<any>(`/automation/tasks/${id}/pause`, { method: 'POST' }),
  resumeAutomationTask: (id: string) =>
    fetchApi<any>(`/automation/tasks/${id}/resume`, { method: 'POST' }),
  runAutomationTask: (id: string) =>
    fetchApi<any>(`/automation/tasks/${id}/run`, { method: 'POST' }),
  getAutomationTaskRuns: (id: string) =>
    fetchApi<{ items: any[]; total: number }>(`/automation/tasks/${id}/runs`),
  getAutomationRuns: () => fetchApi<{ items: any[]; total: number }>('/automation/runs'),
  rerunAutomation: (id: string) =>
    fetchApi<any>(`/automation/runs/${id}/rerun`, { method: 'POST' }),
  testAutomationNotification: (target: object) =>
    fetchApi<{ status: 'sent' | 'failed'; error: string | null }>('/automation/notifications/test', {
      method: 'POST',
      body: JSON.stringify({ target }),
    }),

  getSummarization: () => fetchApi<{ enabled: boolean; default_model: string; trigger: any; keep: any }>('/settings/summarization'),
  updateSummarization: (data: { enabled?: boolean; default_model?: string; trigger?: any; keep?: any }) =>
    fetchApi<any>('/settings/summarization', { method: 'PUT', body: JSON.stringify(data) }),

  // Prompt library
  getPrompts: () => fetchApi<any[]>('/prompts'),
  createPrompt: (data: { name: string; content: string }) =>
    fetchApi<any>('/prompts', { method: 'POST', body: JSON.stringify(data) }),
  updatePrompt: (id: string, data: { name?: string; content?: string }) =>
    fetchApi<any>(`/prompts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deletePrompt: (id: string) => fetchApi<void>(`/prompts/${id}`, { method: 'DELETE' }),

  // Agent ↔ prompt bindings
  getAgentPrompts: (agentId: string) => fetchApi<string[]>(`/agents/${agentId}/prompts`),
  setAgentPrompts: (agentId: string, promptIds: string[]) =>
    fetchApi<string[]>(`/agents/${agentId}/prompts`, { method: 'PUT', body: JSON.stringify({ prompt_ids: promptIds }) }),

  // File changes
  getFileChanges: (sessionId: string) =>
    fetchApi<{ session_id: string; git_base_hash: string | null; files: any[]; sub_sessions?: any[] }>(
      `/sessions/${sessionId}/file-changes`
    ),
  getFileDiff: (sessionId: string, filePath: string) =>
    fetchApi<{ file_path: string; final_type: string; hunks: any[]; change_count: number }>(
      `/sessions/${sessionId}/file-changes/diff?file_path=${encodeURIComponent(filePath)}`
    ),
  getGitDiff: (sessionId: string, baseline: string = 'session', commit?: string) =>
    fetchApi<{
      available: boolean
      base_hash?: string
      baseline?: string
      baseline_label?: string
      diff?: string
      reason?: string
    }>(
      `/sessions/${sessionId}/git-diff?baseline=${encodeURIComponent(baseline)}${commit ? `&commit=${encodeURIComponent(commit)}` : ''}`
    ),
  getGitCommits: (sessionId: string) =>
    fetchApi<{
      available: boolean
      commits: Array<{ hash: string; short_hash: string; subject: string }>
      reason?: string
    }>(`/sessions/${sessionId}/git-diff/commits`),
  getGitDiffFiles: (sessionId: string, baseline: string = 'session', commit?: string) =>
    fetchApi<{
      available: boolean
      base_hash?: string
      baseline?: string
      baseline_label?: string
      files?: Array<{
        file_path: string
        change_type: string
        additions: number
        deletions: number
      }>
      reason?: string
    }>(`/sessions/${sessionId}/git-diff/files?baseline=${encodeURIComponent(baseline)}${commit ? `&commit=${encodeURIComponent(commit)}` : ''}`),
  getGitFileDiff: (sessionId: string, filePath: string, baseline: string = 'session', commit?: string) =>
    fetchApi<{
      available: boolean
      file_path?: string
      baseline?: string
      baseline_label?: string
      diff?: string
      reason?: string
    }>(
      `/sessions/${sessionId}/git-diff/file?file_path=${encodeURIComponent(filePath)}&baseline=${encodeURIComponent(baseline)}${commit ? `&commit=${encodeURIComponent(commit)}` : ''}`
    ),

  // 数据清理 / 瘦身（参见 docs/adr/adr-001-data-cleanup.md）
  previewCleanup: (data: {
    keep_days: number
    skip_pinned?: boolean
    skip_active?: boolean
    active_session_ids?: string[]
  }) =>
    fetchApi<{
      would_delete_sessions: number
      would_delete_messages: number
      would_delete_threads: number
      affected_session_ids: string[]
    }>('/admin/cleanup/preview', { method: 'POST', body: JSON.stringify(data) }),
  cleanupData: (data: {
    keep_days: number
    skip_pinned?: boolean
    skip_active?: boolean
    active_session_ids?: string[]
  }) =>
    fetchApi<{
      deleted_sessions: number
      deleted_messages: number
      deleted_threads: number
      kept_sessions: number
      errors: Array<{ session_id?: string; phase: string; error: string }>
    }>('/admin/cleanup', { method: 'POST', body: JSON.stringify(data) }),
  vacuumDatabases: () =>
    fetchApi<{
      data: { success: boolean; path: string; error: string | null }
      checkpoints: { success: boolean; path: string; error: string | null }
    }>('/admin/vacuum', { method: 'POST' }),
}

export async function fetchAvailableSubagents(): Promise<Array<{
  id: string
  name: string
  display_name: string | null
  source: string
  description: string
}>> {
  return fetchApi('/agents/available-subagents')
}
