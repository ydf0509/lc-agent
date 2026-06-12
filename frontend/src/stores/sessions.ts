import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'

export interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  created_at: string
  updated_at: string
}

export const useSessionsStore = defineStore('sessions', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)

  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value)
  )

  async function init() {
    try {
      sessions.value = await api.getSessions()
    } catch (e) {
      console.error('[SessionsStore] Failed to fetch:', e)
    }
  }

  async function createSession(agentId: string = '__chat__', model: string = '') {
    const created = await api.createSession({ agent_id: agentId, model })
    sessions.value.unshift({
      ...created,
      agent_id: agentId,
      model,
      message_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    currentSessionId.value = created.id
    return created
  }

  async function deleteSession(id: string) {
    await api.deleteSession(id)
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = sessions.value[0]?.id || null
    }
  }

  async function updateTitle(id: string, title: string) {
    await api.updateSession(id, { title })
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
  }

  function updateTitleLocal(id: string, title: string) {
    const sess = sessions.value.find(s => s.id === id)
    if (sess) sess.title = title
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

  return { sessions, currentSessionId, currentSession, groupedByAgent, init, createSession, deleteSession, updateTitle, updateTitleLocal, selectSession }
})
