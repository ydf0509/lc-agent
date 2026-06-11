import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/api/http'

export interface ToolGroup {
  name: string
  tools: { name: string; description: string }[]
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
  const mcpServers = ref<any[]>([])
  const skills = ref<any[]>([])
  const currentModel = ref('')

  async function init() {
    try {
      const [groupsData, modelsData, mcpData, skillsData] = await Promise.all([
        api.getToolGroups(),
        api.getModels(),
        api.getMcpServers(),
        api.getSkills(),
      ])
      groups.value = groupsData.map(g => ({ ...g, enabled: true }))
      models.value = modelsData
      mcpServers.value = mcpData
      skills.value = skillsData
      if (modelsData.length > 0 && !currentModel.value) {
        currentModel.value = modelsData[0].id
      }
    } catch (e) {
      console.error('[ToolsStore] Failed to fetch:', e)
    }
  }

  function toggleGroup(groupName: string) {
    const group = groups.value.find(g => g.name === groupName)
    if (group) group.enabled = !group.enabled
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
  }

  return { groups, models, mcpServers, skills, currentModel, init, toggleGroup, setModel }
})
