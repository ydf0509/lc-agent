import { defineStore } from 'pinia'
import { ref, computed, watch, reactive } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'
import { useSessionsStore } from '@/stores/sessions'

export interface ToolItem {
  name: string
  description: string
  input_schema?: any
}

export interface ToolGroup {
  id: string
  description: string
  tools: ToolItem[]
  enabled: boolean
}

export interface McpToolSchema {
  name: string
  description: string
  input_schema: any
}

export interface McpServer {
  name: string
  type: string
  command?: string
  url?: string
  enabled: boolean
  status: string
  tools: string[]
  tool_schemas?: McpToolSchema[]
  error?: string
}

export interface Skill {
  name: string
  description: string
  source?: string
  metadata?: Record<string, any>
  enabled: boolean
}

export interface ModelInfo {
  id: string
  provider: string
  base_url: string
  context_limit: number
}

export const useToolsStore = defineStore('tools', () => {
  const groups = ref<ToolGroup[]>([])
  const models = ref<ModelInfo[]>([])
  const mcpServers = ref<McpServer[]>([])
  const skills = ref<Skill[]>([])
  const currentModel = ref('')
  const mcpRefreshing = ref(false)

  const localOverrides = reactive<Record<string, boolean>>({})

  function _effectiveEnabled(key: string, serverEnabled: boolean): boolean {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return serverEnabled
    if (key in localOverrides) return localOverrides[key]
    return agent.default_enabled ? serverEnabled : false
  }

  const filteredGroups = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return groups.value
    const allowed = agent.allowed_tool_groups
    return groups.value.map(g => ({
      ...g,
      enabled: _effectiveEnabled(`group:${g.id}`, g.enabled) && (allowed === null || allowed.includes(g.id)),
      allowed: allowed === null || allowed.includes(g.id),
    }))
  })

  const filteredMcp = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return mcpServers.value
    const allowed = agent.allowed_mcp_servers
    return mcpServers.value.map((s: any) => ({
      ...s,
      enabled: _effectiveEnabled(`mcp:${s.name}`, s.enabled) && (allowed === null || allowed.includes(s.name)),
      allowed: allowed === null || allowed.includes(s.name),
    }))
  })

  const filteredSkills = computed(() => {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    if (!agent) return skills.value
    const allowed = agent.allowed_skills
    return skills.value.map((s: any) => ({
      ...s,
      enabled: _effectiveEnabled(`skill:${s.name}`, s.enabled !== false) && (allowed === null || allowed.includes(s.name)),
      allowed: allowed === null || allowed.includes(s.name),
    }))
  })

  function syncModelWithAgentDefault() {
    const agentsStore = useAgentsStore()
    const defaultModel = agentsStore.currentAgent?.default_model
    if (defaultModel) {
      currentModel.value = defaultModel
      return
    }
    if (models.value.length > 0 && !currentModel.value) {
      currentModel.value = models.value[0].id
    }
  }

  function _clearOverrides() {
    for (const key of Object.keys(localOverrides)) {
      delete localOverrides[key]
    }
  }

  async function refreshMcpServers() {
    mcpRefreshing.value = true
    try {
      mcpServers.value = await api.getMcpServers()
    } catch (e) {
      console.error('[ToolsStore] Failed to refresh MCP servers:', e)
    } finally {
      mcpRefreshing.value = false
    }
  }

  async function init() {
    try {
      const [groupsData, modelsData, mcpData, skillsData] = await Promise.all([
        api.getToolGroups(),
        api.getModels(),
        api.getMcpServers(),
        api.getSkills(),
      ])
      groups.value = groupsData
      models.value = modelsData
      mcpServers.value = mcpData
      skills.value = skillsData
      syncModelWithAgentDefault()

      const agentsStore = useAgentsStore()
      watch(() => agentsStore.currentAgentId, () => {
        _clearOverrides()
        syncModelWithAgentDefault()
      })
    } catch (e) {
      console.error('[ToolsStore] Failed to fetch:', e)
    }
  }

  async function toggleGroup(groupId: string) {
    const key = `group:${groupId}`
    const current = _effectiveEnabled(key, groups.value.find(g => g.id === groupId)?.enabled ?? true)
    localOverrides[key] = !current
    try {
      await api.toggleToolGroup(groupId)
      const group = groups.value.find(g => g.id === groupId)
      if (group) group.enabled = !group.enabled
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle group failed:', e)
    }
  }

  async function toggleMcp(serverName: string) {
    const key = `mcp:${serverName}`
    const server = mcpServers.value.find((s: any) => s.name === serverName)
    const current = _effectiveEnabled(key, server?.enabled ?? true)
    localOverrides[key] = !current
    try {
      const result = await api.toggleMcpServer(serverName)
      if (server) {
        server.enabled = !server.enabled
        server.status = result.enabled ? (server.status === 'disabled' ? 'disconnected' : server.status) : 'disabled'
      }
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle MCP failed:', e)
    }
  }

  async function toggleSkill(skillName: string) {
    const key = `skill:${skillName}`
    const skill = skills.value.find((s: any) => s.name === skillName)
    const current = _effectiveEnabled(key, skill?.enabled !== false)
    localOverrides[key] = !current
    try {
      await api.toggleSkill(skillName)
      if (skill) skill.enabled = !skill.enabled
    } catch (e) {
      localOverrides[key] = current
      console.error('[ToolsStore] Toggle skill failed:', e)
    }
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId) {
      sessionsStore.updateModel(sessionId, modelId).catch((e) => {
        console.error('[ToolsStore] Failed to update session model:', e)
      })
    }
  }

  return {
    groups, models, mcpServers, skills, currentModel, mcpRefreshing,
    filteredGroups, filteredMcp, filteredSkills,
    init, refreshMcpServers, toggleGroup, toggleMcp, toggleSkill, setModel, syncModelWithAgentDefault,
  }
})
