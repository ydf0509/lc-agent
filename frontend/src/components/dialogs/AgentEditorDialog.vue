<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 Agent' : '新建 Agent'"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-alert v-if="isCodeAgent" type="warning" :closable="false" style="margin-bottom: 12px">
      此智能体由代码注册（CompiledGraph），工具、MCP、Skills、提示词和模型由代码中的 graph 决定。此处仅展示说明，不能修改框架级配置。
    </el-alert>

    <el-form v-if="!isCodeAgent" :model="form" label-width="100px" label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" :disabled="isCodeAgent" placeholder="例如：Code Assistant" />
      </el-form-item>

      <el-form-item label="模型">
        <el-select v-model="form.default_model" :disabled="isCodeAgent" filterable style="width:100%" placeholder="选择默认模型">
          <el-option
            v-for="model in toolsStore.models"
            :key="model.id"
            :label="`${model.id} (${model.provider})`"
            :value="model.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="Temperature">
        <div class="llm-param-item">
          <el-checkbox
            :model-value="form.llm_params?.temperature !== undefined"
            :disabled="isCodeAgent"
            @update:model-value="toggleTemperature"
          >为此预设固定温度值</el-checkbox>
          <div v-if="form.llm_params?.temperature !== undefined" class="temperature-preset-control">
            <el-slider
              :model-value="form.llm_params.temperature"
              :min="0"
              :max="2"
              :step="0.05"
              :disabled="isCodeAgent"
              class="temp-slider"
              @update:model-value="setTemperature"
            />
            <el-input-number
              :model-value="form.llm_params.temperature"
              :min="0"
              :max="2"
              :step="0.05"
              :precision="2"
              size="small"
              controls-position="right"
              :disabled="isCodeAgent"
              style="width: 80px"
              @update:model-value="setTemperature"
            />
          </div>
          <span v-else class="param-hint">留空时运行时默认 0.7</span>
        </div>
      </el-form-item>

      <el-form-item label="思考级别（reasoning_effort）">
        <div class="llm-param-item">
          <el-checkbox
            :model-value="form.llm_params?.reasoning_effort !== undefined"
            :disabled="isCodeAgent"
            @update:model-value="toggleReasoningEffort"
          >为此预设固定思考级别</el-checkbox>
          <el-select
            v-if="form.llm_params?.reasoning_effort !== undefined"
            :model-value="form.llm_params.reasoning_effort"
            size="small"
            :disabled="isCodeAgent"
            style="width: 140px; margin-top: 6px"
            @update:model-value="setReasoningEffort"
          >
            <el-option
              v-for="effort in REASONING_EFFORTS"
              :key="effort"
              :label="effort"
              :value="effort"
            />
          </el-select>
          <span v-else class="param-hint">留空时由模型决定</span>
        </div>
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

      <el-form-item label="允许的子Agent">
        <div class="tool-group-select">
          <el-radio-group v-model="subAgentMode" size="small">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="none">无</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
          <div v-if="subAgentMode === 'custom'" class="custom-groups">
            <el-checkbox-group v-model="selectedSubAgents">
              <el-checkbox
                v-for="agent in agentsStore.agents.filter(a => a.id !== editingId)"
                :key="agent.id"
                :value="agent.id"
              >
                {{ agent.name }}
                <el-tag size="small" style="margin-left:4px">{{ agent.source }}</el-tag>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </div>
      </el-form-item>
    </el-form>

    <div v-else class="code-agent-readonly">
      <div class="readonly-row">
        <span class="readonly-label">名称</span>
        <span class="readonly-value">{{ form.name }}</span>
      </div>
      <div class="readonly-row">
        <span class="readonly-label">说明</span>
        <span class="readonly-value">{{ form.system_prompt }}</span>
      </div>
      <div class="readonly-row">
        <span class="readonly-label">运行模型</span>
        <span class="readonly-value">由代码 graph 决定</span>
      </div>
      <div class="readonly-row">
        <span class="readonly-label">工具能力</span>
        <span class="readonly-value">由代码 graph 决定</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="danger" v-if="isEdit && !agentsStore.isAgentBuiltin(editingId!) && !isCodeAgent" @click="handleDelete">
        删除
      </el-button>
      <el-button v-if="!isCodeAgent" type="primary" :loading="saving" @click="handleSave">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore, type AgentPreset } from '@/stores/agents'

const REASONING_EFFORTS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh']

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
const subAgentMode = ref<'all' | 'none' | 'custom'>('none')
const selectedSubAgents = ref<string[]>([])

const isCodeAgent = ref(false)

const form = ref({
  name: '',
  system_prompt: '',
  default_model: '',
  llm_params: null as Record<string, any> | null,
})

function open(agent?: AgentPreset) {
  if (agent) {
    isEdit.value = true
    editingId.value = agent.id
    editingSource.value = agent.source || 'user'
    isCodeAgent.value = agent.source === 'code'
    form.value.name = agent.name
    form.value.system_prompt = agent.system_prompt
    form.value.default_model = agent.default_model
    form.value.llm_params = agent.llm_params ?? null

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

    if (agent.allowed_sub_agents === null) {
      subAgentMode.value = 'all'
      selectedSubAgents.value = []
    } else if (agent.allowed_sub_agents.length === 0) {
      subAgentMode.value = 'none'
      selectedSubAgents.value = []
    } else {
      subAgentMode.value = 'custom'
      selectedSubAgents.value = [...agent.allowed_sub_agents]
    }
  } else {
    isEdit.value = false
    editingId.value = ''
    editingSource.value = 'user'
    isCodeAgent.value = false
    form.value = { name: '', system_prompt: '', default_model: toolsStore.currentModel, llm_params: null }
    toolGroupMode.value = 'all'
    selectedGroups.value = []
    mcpMode.value = 'all'
    selectedMcpServers.value = []
    skillsMode.value = 'all'
    selectedSkills.value = []
    subAgentMode.value = 'none'
    selectedSubAgents.value = []
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

    const allowed_sub_agents =
      subAgentMode.value === 'all' ? null :
      subAgentMode.value === 'none' ? [] :
      selectedSubAgents.value

    const data = {
      name: form.value.name,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      allowed_tool_groups,
      allowed_mcp_servers,
      allowed_skills,
      allowed_sub_agents,
      llm_params: form.value.llm_params || null,
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

function _ensureLlmParams() {
  if (!form.value.llm_params) form.value.llm_params = {}
}

function _cleanLlmParams() {
  if (form.value.llm_params && !Object.keys(form.value.llm_params).length) {
    form.value.llm_params = null
  }
}

function toggleTemperature(v: boolean) {
  if (v) {
    _ensureLlmParams()
    form.value.llm_params!.temperature = 0.7
  } else {
    if (form.value.llm_params) {
      delete form.value.llm_params.temperature
      _cleanLlmParams()
    }
  }
}

function setTemperature(v: number | undefined) {
  if (v === undefined) return
  _ensureLlmParams()
  form.value.llm_params!.temperature = v
}

function toggleReasoningEffort(v: boolean) {
  if (v) {
    _ensureLlmParams()
    form.value.llm_params!.reasoning_effort = 'medium'
  } else {
    if (form.value.llm_params) {
      delete form.value.llm_params.reasoning_effort
      _cleanLlmParams()
    }
  }
}

function setReasoningEffort(v: string) {
  _ensureLlmParams()
  form.value.llm_params!.reasoning_effort = v
}

defineExpose({ open })
</script>

<style scoped>
.llm-param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.temperature-preset-control {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.temp-slider {
  flex: 1;
}

.param-hint {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  margin-left: 2px;
}

.tool-group-select {
  width: 100%;
}

.custom-groups {
  margin-top: 8px;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
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
  color: var(--el-text-color-secondary);
  margin-left: 4px;
  opacity: 0.7;
}
.code-agent-readonly {
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-light);
}

.readonly-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.readonly-row:last-child {
  border-bottom: none;
}

.readonly-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 600;
}

.readonly-value {
  color: var(--el-text-color-primary);
  font-size: 13px;
  text-align: right;
}

</style>
