<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 Agent' : '新建 Agent'"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-alert v-if="isCodeAgent" type="warning" :closable="false" style="margin-bottom: 12px">
      此智能体由代码注册（CompiledGraph），仅可修改运行时配置（工具/MCP/Skills）。
    </el-alert>

    <el-form :model="form" label-width="100px" label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" :disabled="isCodeAgent" placeholder="例如：Code Assistant" />
      </el-form-item>

      <el-form-item label="模型">
        <el-select v-model="form.default_model" :disabled="isCodeAgent" style="width:100%" placeholder="选择默认模型">
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
          :disabled="isCodeAgent"
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
                :key="group.id"
                :value="group.id"
              >
                {{ group.description || group.id }} ({{ group.tools.length }} tools)
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="允许的 MCP 服务器">
        <div class="tool-group-select">
          <el-radio-group v-model="mcpMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="mcpMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedMcpServers">
              <el-checkbox
                v-for="server in toolsStore.mcpServers"
                :key="server.name"
                :value="server.name"
              >
                {{ server.name }}
                <el-tag size="small" :type="server.status === 'connected' ? 'success' : 'info'" style="margin-left:4px">
                  {{ server.tools?.length || 0 }} tools
                </el-tag>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>

      <el-form-item label="允许的 Skills">
        <div class="tool-group-select">
          <el-radio-group v-model="skillsMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="skillsMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedSkills">
              <el-checkbox
                v-for="skill in toolsStore.skills"
                :key="skill.name"
                :value="skill.name"
              >
                {{ skill.name }}
                <span class="skill-hint">{{ skill.description }}</span>
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
      <el-button type="danger" v-if="isEdit && !agentsStore.isAgentBuiltin(editingId!) && !isCodeAgent" @click="handleDelete">
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
const editingSource = ref<'builtin' | 'code' | 'user'>('user')
const toolGroupMode = ref<'all' | 'none' | 'custom'>('all')
const selectedGroups = ref<string[]>([])
const mcpMode = ref<'all' | 'none' | 'custom'>('all')
const selectedMcpServers = ref<string[]>([])
const skillsMode = ref<'all' | 'none' | 'custom'>('all')
const selectedSkills = ref<string[]>([])

const isCodeAgent = ref(false)

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
    editingSource.value = agent.source || 'user'
    isCodeAgent.value = agent.source === 'code'
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

    if (agent.allowed_mcp_servers === null) {
      mcpMode.value = 'all'
      selectedMcpServers.value = []
    } else if (agent.allowed_mcp_servers.length === 0) {
      mcpMode.value = 'none'
      selectedMcpServers.value = []
    } else {
      mcpMode.value = 'custom'
      selectedMcpServers.value = [...agent.allowed_mcp_servers]
    }

    if (agent.allowed_skills === null) {
      skillsMode.value = 'all'
      selectedSkills.value = []
    } else if (agent.allowed_skills.length === 0) {
      skillsMode.value = 'none'
      selectedSkills.value = []
    } else {
      skillsMode.value = 'custom'
      selectedSkills.value = [...agent.allowed_skills]
    }
  } else {
    isEdit.value = false
    editingId.value = ''
    editingSource.value = 'user'
    isCodeAgent.value = false
    form.value = { name: '', system_prompt: '', default_model: toolsStore.currentModel }
    dangerousToolsStr.value = ''
    toolGroupMode.value = 'all'
    selectedGroups.value = []
    mcpMode.value = 'all'
    selectedMcpServers.value = []
    skillsMode.value = 'all'
    selectedSkills.value = []
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

    const allowed_mcp_servers =
      mcpMode.value === 'all' ? null :
      mcpMode.value === 'none' ? [] :
      selectedMcpServers.value

    const allowed_skills =
      skillsMode.value === 'all' ? null :
      skillsMode.value === 'none' ? [] :
      selectedSkills.value

    const data = {
      name: form.value.name,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      allowed_tool_groups,
      allowed_mcp_servers,
      allowed_skills,
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
  padding: 10px;
  background: var(--lc-glass-bg-hover);
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-md);
  max-height: 200px;
  overflow-y: auto;
}

.custom-groups .el-checkbox {
  display: flex;
  align-items: center;
  margin-bottom: 4px;
}

.skill-hint {
  font-size: 11px;
  color: var(--lc-text-secondary);
  margin-left: 4px;
  opacity: 0.7;
}
</style>
