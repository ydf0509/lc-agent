import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ToolGroup {
  name: string
  tools: { name: string; description: string }[]
  enabled: boolean
}

export const useToolsStore = defineStore('tools', () => {
  const groups = ref<ToolGroup[]>([])
  const models = ref<{ id: string; provider: string; context_limit: number }[]>([])
  const currentModel = ref('')

  function toggleGroup(groupName: string) {
    const group = groups.value.find(g => g.name === groupName)
    if (group) group.enabled = !group.enabled
  }

  function setModel(modelId: string) {
    currentModel.value = modelId
  }

  return { groups, models, currentModel, toggleGroup, setModel }
})
