import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/http'

export interface AgentSubagentConfig {
  agent_id: string
  delegation_description: string
}

export interface AgentPreset {
  id: string
  name: string
  display_name: string | null
  system_prompt: string
  default_model: string
  allowed_tool_groups: string[] | null
  allowed_mcp_servers: string[] | null
  allowed_skills: string[] | null
  llm_params: Record<string, any> | null
  subagents: AgentSubagentConfig[] | null
  enable_general_purpose_subagent: boolean
  source: 'builtin' | 'code' | 'user'
  default_enabled: boolean
  project_mode?: boolean
  project_root?: string | null
  project_extra_dirs?: string[] | null
  extra_skill_dirs?: string[] | null
}

const BUILTIN_IDS = new Set(['chat', 'empty', 'power'])

export const useAgentsStore = defineStore('agents', () => {
  const agents = ref<AgentPreset[]>([])
  const currentAgentId = ref('chat')

  const currentAgent = computed(() =>
    agents.value.find(a => a.id === currentAgentId.value) || agents.value[0]
  )

  const isBuiltin = computed(() => BUILTIN_IDS.has(currentAgentId.value))

  const isChatAgent = computed(() => currentAgentId.value === 'chat')

  const isCodeAgent = computed(() => currentAgent.value?.source === 'code')

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
    if (currentAgentId.value === id) currentAgentId.value = 'chat'
  }

  async function selectAgent(id: string) {
    currentAgentId.value = id
  }

  function getAgentName(agentId: string): string {
    const agent = agents.value.find(a => a.id === agentId)
    return agent?.display_name || agent?.name || agentId
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
    isCodeAgent,
    init,
    createAgent,
    updateAgent,
    deleteAgent,
    selectAgent,
    getAgentName,
    isAgentBuiltin,
  }
})
