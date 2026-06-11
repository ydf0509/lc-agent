<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 Agent' : '新建 Agent'"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form :model="form" label-width="100px" label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" placeholder="例如：Code Assistant" />
      </el-form-item>

      <el-form-item label="模型">
        <el-select v-model="form.default_model" style="width:100%" placeholder="选择默认模型">
          <el-option
            v-for="model in toolsStore.models"
            :key="model.id"
            :label="`${model.id} (${model.provider})`"
            :value="model.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="系统提示词">
        <el-input
          v-model="form.system_prompt"
          type="textarea"
          :autosize="{ minRows: 4, maxRows: 12 }"
          placeholder="定义 Agent 的行为和角色..."
        />
      </el-form-item>

      <el-form-item label="允许的工具组">
        <div class="tool-group-select">
          <el-radio-group v-model="toolGroupMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="toolGroupMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedGroups">
              <el-checkbox
                v-for="group in toolsStore.groups"
                :key="group.name"
                :value="group.name"
              >
                {{ group.name }} ({{ group.tools.length }} tools)
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="危险工具（需要审批）">
        <el-input
          v-model="dangerousToolsStr"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="每行一个工具名, 例如: filesystem__delete_file"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="danger" v-if="isEdit && editingId !== '__default__'" @click="handleDelete">
        删除
      </el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore, type AgentPreset } from '@/stores/agents'

const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()

const visible = ref(false)
const saving = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const toolGroupMode = ref<'all' | 'none' | 'custom'>('all')
const selectedGroups = ref<string[]>([])

const form = ref({
  name: '',
  system_prompt: '',
  default_model: '',
})

const dangerousToolsStr = ref('')

function open(agent?: AgentPreset) {
  if (agent) {
    isEdit.value = true
    editingId.value = agent.id
    form.value.name = agent.name
    form.value.system_prompt = agent.system_prompt
    form.value.default_model = agent.default_model
    dangerousToolsStr.value = (agent.dangerous_tools || []).join('\n')

    if (agent.allowed_tool_groups === null) {
      toolGroupMode.value = 'all'
      selectedGroups.value = []
    } else if (agent.allowed_tool_groups.length === 0) {
      toolGroupMode.value = 'none'
      selectedGroups.value = []
    } else {
      toolGroupMode.value = 'custom'
      selectedGroups.value = [...agent.allowed_tool_groups]
    }
  } else {
    isEdit.value = false
    editingId.value = ''
    form.value = { name: '', system_prompt: '', default_model: toolsStore.currentModel }
    dangerousToolsStr.value = ''
    toolGroupMode.value = 'all'
    selectedGroups.value = []
  }
  visible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    const allowed_tool_groups =
      toolGroupMode.value === 'all' ? null :
      toolGroupMode.value === 'none' ? [] :
      selectedGroups.value

    const data = {
      name: form.value.name,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      allowed_tool_groups,
      dangerous_tools: dangerousToolsStr.value.split('\n').map(s => s.trim()).filter(Boolean),
    }

    if (isEdit.value) {
      await agentsStore.updateAgent(editingId.value, data)
    } else {
      await agentsStore.createAgent(data as any)
    }
    visible.value = false
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  await agentsStore.deleteAgent(editingId.value)
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.tool-group-select {
  width: 100%;
}

.custom-groups {
  margin-top: 8px;
  padding: 8px;
  background: var(--lc-bg-tertiary);
  border-radius: 6px;
}
</style>
