import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

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

  async function createSession(agentId: string = '__default__', model: string = '') {
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

  function selectSession(id: string) {
    currentSessionId.value = id
  }

  return { sessions, currentSessionId, currentSession, init, createSession, deleteSession, updateTitle, selectSession }
})
