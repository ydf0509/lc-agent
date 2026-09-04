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
  scope?: 'global' | 'project' | 'extra'
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
  const llmParams = ref<Record<string, any> | null>(null)
  const mcpRefreshing = ref(false)
  const refreshingMcpServerNames = ref<string[]>([])

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
    if (agentsStore.currentAgent?.source === 'code') {
      currentModel.value = ''
      return
    }
    const defaultModel = agentsStore.currentAgent?.default_model
    if (defaultModel && defaultModel !== 'custom') {
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

  function setLlmParam(key: string, value: any) {
    if (value === null || value === undefined || value === '') {
      if (llmParams.value) {
        delete llmParams.value[key]
        if (Object.keys(llmParams.value).length === 0) llmParams.value = null
      }
    } else {
      if (!llmParams.value) llmParams.value = {}
      llmParams.value[key] = value
    }
  }

  function resetLlmParams() {
    llmParams.value = null
  }

  async function refreshMcpServers() {
    mcpRefreshing.value = true
    try {
      mcpServers.value = await api.refreshMcpServers()
    } catch (e) {
      console.error('[ToolsStore] Failed to refresh MCP servers:', e)
    } finally {
      mcpRefreshing.value = false
    }
  }

  function isMcpRefreshing(serverName: string): boolean {
    return mcpRefreshing.value || refreshingMcpServerNames.value.includes(serverName)
  }

  async function refreshMcpServer(serverName: string) {
    if (isMcpRefreshing(serverName)) return
    refreshingMcpServerNames.value = [...refreshingMcpServerNames.value, serverName]
    try {
      const refreshed = await api.refreshMcpServer(serverName)
      const index = mcpServers.value.findIndex(server => server.name === serverName)
      if (index >= 0) mcpServers.value[index] = refreshed
    } catch (e) {
      console.error(`[ToolsStore] Failed to refresh MCP server '${serverName}':`, e)
    } finally {
      refreshingMcpServerNames.value = refreshingMcpServerNames.value.filter(name => name !== serverName)
    }
  }

  async function getSkillsForCurrentAgent() {
    const agentsStore = useAgentsStore()
    const agent = agentsStore.currentAgent
    const projectRoot = agent?.project_mode ? agent.project_root || undefined : undefined
    const extraDirs = agent?.extra_skill_dirs || []
    return api.getSkills(projectRoot, extraDirs)
  }

  async function refreshRuntimeToggles() {
    try {
      const [groupsData, mcpData, skillsData] = await Promise.all([
        api.getToolGroups(),
        api.getMcpServers(),
        getSkillsForCurrentAgent(),
      ])
      groups.value = groupsData
      mcpServers.value = mcpData
      skills.value = skillsData
    } catch (e) {
      console.error('[ToolsStore] Failed to refresh runtime toggles:', e)
    }
  }

  async function init() {
    try {
      const [groupsData, modelsData, mcpData, skillsData] = await Promise.all([
        api.getToolGroups(),
        api.getModels(),
        api.getMcpServers(),
        getSkillsForCurrentAgent(),
      ])
      groups.value = groupsData
      models.value = modelsData
      mcpServers.value = mcpData
      skills.value = skillsData
      syncModelWithAgentDefault()

      const agentsStore = useAgentsStore()
      watch(
        () => [
          agentsStore.currentAgentId,
          agentsStore.currentAgent?.project_mode,
          agentsStore.currentAgent?.project_root,
          agentsStore.currentAgent?.extra_skill_dirs,
        ] as const,
        () => {
          _clearOverrides()
          syncModelWithAgentDefault()
          resetLlmParams()
          refreshRuntimeToggles()
        },
      )
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

  function applyModel(modelId: string) {
    currentModel.value = modelId
  }

  function setModel(modelId: string) {
    applyModel(modelId)
    const sessionsStore = useSessionsStore()
    const sessionId = sessionsStore.currentSessionId
    if (sessionId) {
      sessionsStore.updateModel(sessionId, modelId).catch((e) => {
        console.error('[ToolsStore] Failed to update session model:', e)
      })
    }
  }

  return {
    groups, models, mcpServers, skills, currentModel, llmParams, mcpRefreshing,
    filteredGroups, filteredMcp, filteredSkills,
    init, refreshMcpServers, refreshMcpServer, isMcpRefreshing, refreshRuntimeToggles, toggleGroup, toggleMcp, toggleSkill,
    applyModel, setModel, setLlmParam, resetLlmParams, syncModelWithAgentDefault,
  }
})
