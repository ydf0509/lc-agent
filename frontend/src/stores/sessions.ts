import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'
import { createClientId } from '@/utils/client-id'

export interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  is_pinned: boolean
  pinned_at: string | null
  created_at: string
  updated_at: string
}

export const useSessionsStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const localSessionIds = ref<Set<string>>(new Set())

  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value)
  )

  function isLocalSession(id: string): boolean {
    return localSessionIds.value.has(id)
  }

  async function init() {
    try {
      sessions.value = await api.getSessions()
    } catch (e) {
      console.error('[SessionsStore] Failed to fetch:', e)
    }
  }

  function createLocalSession(agentId: string = '__chat__', model: string = ''): Session {
    const existing = sessions.value.find(
      s => s.agent_id === agentId && s.message_count === 0 && localSessionIds.value.has(s.id)
    )
    if (existing) {
      currentSessionId.value = existing.id
      return existing
    }

    const id = createClientId()
    return ensureLocalSession(id, agentId, model)
  }

  function ensureLocalSession(id: string, agentId: string = '__chat__', model: string = ''): Session {
    const existing = sessions.value.find(s => s.id === id)
    if (existing) {
      existing.agent_id = agentId
      existing.model = model || existing.model
      currentSessionId.value = existing.id
      localSessionIds.value.add(existing.id)
      return existing
    }

    const session: Session = {
      id,
      title: '新对话',
      agent_id: agentId,
      model,
      message_count: 0,
      is_pinned: false,
      pinned_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    sessions.value.unshift(session)
    localSessionIds.value.add(id)
    currentSessionId.value = id
    return session
  }

  async function persistSession(id: string, model: string = ''): Promise<string> {
    if (!localSessionIds.value.has(id)) return id
    const session = sessions.value.find(s => s.id === id)
    if (!session) return id

    const created = await api.createSession({
      agent_id: session.agent_id,
      model: model || session.model,
    })
    localSessionIds.value.delete(id)
    const newId = created.id || id
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx >= 0) {
      sessions.value[idx] = { ...sessions.value[idx], ...created, id: newId }
    }
    if (currentSessionId.value === id) {
      currentSessionId.value = newId
    }
    return newId
  }

  async function createSession(agentId: string = '__chat__', model: string = '') {
    const created = await api.createSession({ agent_id: agentId, model })
    sessions.value.unshift({
      ...created,
      agent_id: agentId,
      model,
      message_count: 0,
      is_pinned: false,
      pinned_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    currentSessionId.value = created.id
    return created
  }

  async function deleteSession(id: string) {
    if (!localSessionIds.value.has(id)) {
      await api.deleteSession(id)
    } else {
      localSessionIds.value.delete(id)
    }
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0]?.id || null
    }
  }

  async function updateTitle(id: string, title: string) {
    if (!localSessionIds.value.has(id)) {
      await api.updateSession(id, { title })
    }
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  function updateTitleLocal(id: string, title: string) {
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  async function updateModel(id: string, model: string) {
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.model = model
    if (!localSessionIds.value.has(id)) {
      await api.updateSession(id, { model })
    }
  }

  function updateModelLocal(id: string, model: string) {
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.model = model
  }

  async function setPinned(id: string, isPinned: boolean) {
    if (!localSessionIds.value.has(id)) {
      const updated = await api.updateSession(id, { is_pinned: isPinned })
      const idx = sessions.value.findIndex(s => s.id === id)
      if (idx >= 0) {
        sessions.value[idx] = { ...sessions.value[idx], ...updated }
      }
      return
    }

    const sess = sessions.value.find(s => s.id === id)
    if (sess) {
      sess.is_pinned = isPinned
      sess.pinned_at = isPinned ? new Date().toISOString() : null
    }
  }

  const groupedByAgent = computed(() => {
    const agentsStore = useAgentsStore()
    const groups: Record<string, { agentName: string; agentSource: string; sessions: Session[] }> = {}
    for (const s of sessions.value) {
      const key = s.agent_id || '__chat__'
      if (!groups[key]) {
        const agent = agentsStore.agents.find(a => a.id === key)
        groups[key] = {
          agentName: agentsStore.getAgentName(key),
          agentSource: agent?.source || 'user',
          sessions: [],
        }
      }
      groups[key].sessions.push(s)
    }
    return Object.entries(groups).map(([agentId, data]) => ({
      agentId,
      agentName: data.agentName,
      agentSource: data.agentSource,
      sessions: data.sessions,
    }))
  })

  function selectSession(id: string) {
    currentSessionId.value = id
  }

  return { sessions, currentSessionId, currentSession, groupedByAgent, init, createSession, createLocalSession, ensureLocalSession, persistSession, isLocalSession, deleteSession, updateTitle, updateTitleLocal, updateModel, updateModelLocal, setPinned, selectSession }
})
