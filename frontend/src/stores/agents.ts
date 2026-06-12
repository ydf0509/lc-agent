import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

export interface AgentPreset {
  id: string
  name: string
  system_prompt: string
  default_model: string
  allowed_tool_groups: string[] | null
  allowed_mcp_servers: string[] | null
  allowed_skills: string[] | null
  dangerous_tools: string[]
  source: 'builtin' | 'code' | 'user'
  default_enabled: boolean
}

const BUILTIN_IDS = new Set(['__chat__', '__empty__', '__power__'])

export const useAgentsStore = defineStore('agents', () => {
  const agents = ref<AgentPreset[]>([])
  const currentAgentId = ref('__chat__')

  const currentAgent = computed(() =>
    agents.value.find(a => a.id === currentAgentId.value) || agents.value[0]
  )

  const isBuiltin = computed(() => BUILTIN_IDS.has(currentAgentId.value))

  const isChatAgent = computed(() => currentAgentId.value === '__chat__')

  async function init() {
    try {
      agents.value = await api.getAgents()
    } catch (e) {
      console.error('[AgentsStore] Failed to fetch:', e)
    }
  }

  async function createAgent(data: Omit<AgentPreset, 'id'>) {
    const created = await api.createAgent(data)
    agents.value.push(created)
    return created
  }

  async function updateAgent(id: string, data: Partial<AgentPreset>) {
    const updated = await api.updateAgent(id, data)
    const idx = agents.value.findIndex(a => a.id === id)
    if (idx >= 0) agents.value[idx] = updated
    return updated
  }

  async function deleteAgent(id: string) {
    if (BUILTIN_IDS.has(id)) return
    await api.deleteAgent(id)
    agents.value = agents.value.filter(a => a.id !== id)
    if (currentAgentId.value === id) currentAgentId.value = '__chat__'
  }

  function selectAgent(id: string) {
    currentAgentId.value = id
  }

  function getAgentName(agentId: string): string {
    const agent = agents.value.find(a => a.id === agentId)
    return agent?.name || agentId
  }

  function isAgentBuiltin(id: string): boolean {
    return BUILTIN_IDS.has(id)
  }

  return {
    agents,
    currentAgentId,
    currentAgent,
    isBuiltin,
    isChatAgent,
    init,
    createAgent,
    updateAgent,
    deleteAgent,
    selectAgent,
    getAgentName,
    isAgentBuiltin,
  }
})
