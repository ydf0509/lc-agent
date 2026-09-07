<template>
  <el-dialog
    v-model="visible"
    :width="isMobile ? 'calc(100vw - 24px)' : 'min(94vw, 1360px)'"
    align-center
    class="agent-manager-dialog"
    :close-on-click-modal="false"
    :show-close="false"
  >
    <template #header>
      <div class="dialog-mode-header">
        <div class="dialog-mode-tabs">
          <button
            class="dialog-mode-tab"
            :class="{ 'is-active': viewMode === 'agents' }"
            @click="switchToAgentsView"
          >🤖 {{ isReadOnly ? 'Agents 查看' : 'Agents 管理' }}</button>
          <button
            v-if="!isReadOnly"
            class="dialog-mode-tab"
            :class="{ 'is-active': viewMode === 'prompts' }"
            @click="switchToPromptsView"
          >📚 提示词管理</button>
        </div>
        <button class="dialog-close-btn" @click="visible = false">×</button>
      </div>
    </template>
    <div class="manager-layout">
      <!-- ===== Left Sidebar ===== -->
      <div class="manager-sidebar">
        <!-- Agents mode sidebar -->
        <template v-if="viewMode === 'agents'">
          <!-- Desktop -->
          <template v-if="!isMobile">
            <button v-if="!isReadOnly" class="sidebar-new-btn" @click="handleNewAgent">
              <el-icon><Plus /></el-icon>
              <span>新建 Agent</span>
            </button>
            <div class="sidebar-list">
              <div
                v-if="isPendingNew"
                class="agent-list-item is-selected is-pending"
              >
                <span class="agent-item-icon">✨</span>
                <div class="agent-item-info">
                  <span class="agent-item-name">新 Agent</span>
                  <span class="pending-badge">未保存</span>
                </div>
              </div>
              <div
                v-for="agent in agentsStore.agents"
                :key="agent.id"
                class="agent-list-item"
                :class="{ 'is-selected': !isPendingNew && selectedAgentId === agent.id }"
                @click="trySelectAgent(agent.id)"
              >
                <span class="agent-item-icon">{{ getAgentIcon(agent) }}</span>
                <div class="agent-item-info">
                  <span class="agent-item-name">{{ agent.display_name || agent.name }}</span>
                </div>
                <span v-if="agent.project_mode" class="source-tag source-tag--project">项目</span>
                <span v-else :class="['source-tag', `source-tag--${agent.source || 'user'}`]">
                  {{ agent.source === 'builtin' ? '内置' : agent.source === 'code' ? '代码' : '自建' }}
                </span>
              </div>
            </div>
          </template>
          <!-- Mobile -->
          <div v-else class="mobile-sidebar-bar">
            <el-select
              v-model="mobileAgentSelectValue"
              class="mobile-agent-select"
              placeholder="选择 Agent"
              :disabled="formLoading"
            >
              <el-option
                v-for="opt in agentSelectOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <button v-if="!isReadOnly" class="sidebar-new-btn mobile-new-btn" @click="handleNewAgent">
              <el-icon><Plus /></el-icon>
            </button>
          </div>
        </template>

        <!-- Prompts mode sidebar -->
        <template v-else>
          <!-- Desktop -->
          <template v-if="!isMobile">
            <button class="sidebar-new-btn" @click="handleNewPrompt">
              <el-icon><Plus /></el-icon>
              <span>新建提示词</span>
            </button>
            <div class="sidebar-list">
              <div
                v-for="pt in promptsStore.prompts"
                :key="pt.id"
                class="agent-list-item"
                :class="{ 'is-selected': editingPromptId === pt.id }"
                @click="selectPromptForEdit(pt.id)"
              >
                <span class="agent-item-icon">📝</span>
                <div class="agent-item-info">
                  <span class="agent-item-name">{{ pt.name }}</span>
                </div>
              </div>
              <el-empty v-if="!promptsStore.prompts.length" description="暂无提示词" :image-size="48" />
            </div>
          </template>
          <!-- Mobile: prompts list as select -->
          <div v-else class="mobile-sidebar-bar">
            <el-select
              v-model="editingPromptId"
              class="mobile-agent-select"
              placeholder="选择提示词"
              clearable
              @change="onMobilePromptSelectChange"
            >
              <el-option
                v-for="pt in promptsStore.prompts"
                :key="pt.id"
                :label="pt.name"
                :value="pt.id"
              />
            </el-select>
            <button class="sidebar-new-btn mobile-new-btn" @click="handleNewPrompt">
              <el-icon><Plus /></el-icon>
            </button>
          </div>
        </template>
      </div>

      <!-- ===== Right Content ===== -->
      <div class="manager-content" v-loading="viewMode === 'agents' ? formLoading : promptsStore.loading">

        <!-- ===== Prompt Editor Panel ===== -->
        <template v-if="viewMode === 'prompts'">
          <template v-if="!!editingPromptId || isNewPrompt">
            <div class="prompts-editor-body form-scroll">
              <el-form label-position="top">
                <el-form-item label="名称" required>
                  <el-input v-model="promptForm.name" placeholder="提示词名称，例如：安全规范、代码风格" />
                </el-form-item>
                <el-form-item label="内容">
                  <div class="prompt-content-wrap">
                    <div class="prompt-content-toolbar">
                      <el-button
                        v-if="promptPreviewMode"
                        text
                        size="small"
                        @click="promptPreviewMode = false"
                      >返回编辑</el-button>
                      <el-button
                        v-else
                        text
                        size="small"
                        @click="promptPreviewMode = true"
                      >渲染预览</el-button>
                    </div>
                    <el-input
                      v-if="!promptPreviewMode"
                      v-model="promptForm.content"
                      type="textarea"
                      :autosize="{ minRows: 8, maxRows: 20 }"
                      placeholder="在此填写提示词内容，将追加注入到绑定该模板的 Agent 系统提示词末尾..."
                    />
                    <div v-else class="prompt-preview markdown-body">
                      <div v-if="!promptForm.content" class="prompt-preview-empty">暂无内容可预览</div>
                      <div v-else v-html="renderedPromptContent" />
                    </div>
                  </div>
                </el-form-item>
              </el-form>
            </div>
            <div class="prompts-editor-footer form-footer">
              <div>
                <el-button v-if="editingPromptId && !isNewPrompt" type="danger" @click="handleDeletePrompt">
                  删除
                </el-button>
              </div>
              <div class="prompts-editor-footer-right">
                <el-button type="info" @click="cancelEditPrompt">取消</el-button>
                <el-button type="primary" :loading="promptSaving" @click="handleSavePrompt">
                  {{ isNewPrompt ? '创建' : '保存' }}
                </el-button>
              </div>
            </div>
          </template>
          <div v-else class="empty-placeholder">
            <el-empty
              :description="isMobile ? '从上方选择提示词，或点击 + 新建' : '从左侧选择提示词，或点击「新建提示词」'"
              :image-size="72"
            />
          </div>
        </template>

        <!-- ===== Agent Form Panel ===== -->
        <template v-else>
        <template v-if="selectedAgentId !== null || isPendingNew">
          <!-- Code agent readonly view -->
          <div v-if="isCodeAgent" class="form-scroll">
            <el-alert type="warning" :closable="false" style="margin-bottom: 12px">
              此智能体由代码注册（CompiledGraph），工具、MCP、Skills、提示词和模型由代码中的 graph 决定。此处仅展示说明，不能修改框架级配置。
            </el-alert>
            <div class="code-agent-readonly">
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
          </div>

          <!-- Editable form -->
          <div v-else class="form-scroll">
            <el-alert
              v-if="isReadOnly"
              type="info"
              :closable="false"
              style="margin: 12px 0 0;"
            >当前账号仅有查看权限，Agent 配置不可修改。</el-alert>
            <el-form :model="form" label-width="100px" label-position="top" :disabled="isReadOnly">
              <el-tabs v-model="activeTab" :stretch="isMobile">
                <el-tab-pane label="基本设置" name="basic">

                  <el-form-item class="project-mode-field project-mode-field--toggle">
                    <div class="project-mode-toggle-row">
                      <el-checkbox v-model="form.project_mode">
                        <span class="project-mode-label">
                          <el-icon class="project-mode-label-icon"><Folder /></el-icon>
                          项目模式
                        </span>
                      </el-checkbox>
                      <el-tag v-if="form.project_mode" type="warning" size="small" style="margin-left: 8px;">项目</el-tag>
                      <el-button
                        type="info"
                        text
                        size="small"
                        class="project-help-btn"
                        style="margin-left: 4px;"
                        @click="showProjectModeHelp = true"
                      >
                        <el-icon><QuestionFilled /></el-icon>
                      </el-button>
                    </div>
                    <div class="form-hint">
                      开启后自动注入 项目根目录下的AGENTS.md、 .agents 目录下的skills和mcp.json 和git status快照等等
                    </div>
                  </el-form-item>

                  <el-form-item v-if="form.project_mode" label="项目根目录" class="project-mode-field">
                    <div class="project-root-row">
                      <el-input
                        v-model="form.project_root"
                        placeholder="如 D:\\codes\\my-project"
                        clearable
                      />
                    </div>
                    <div class="form-hint">自动加载项目 AGENTS.md、Skills 和 MCP，文件工具默认限制在此目录</div>
                  </el-form-item>

                  <el-form-item v-if="form.project_mode && form.project_root" label="额外允许目录" class="project-mode-field">
                    <div class="extra-dirs-list">
                      <div
                        v-for="(dir, idx) in (form.project_extra_dirs || [])"
                        :key="idx"
                        class="extra-dir-row"
                      >
                        <el-input
                          :model-value="dir"
                          placeholder="如 D:\\other\\path"
                          clearable
                          @update:model-value="(val: string) => updateExtraDir(idx, val)"
                          @clear="removeExtraDir(idx)"
                        />
                        <el-button
                          :icon="Delete"
                          circle
                          plain
                          type="danger"
                          size="small"
                          class="extra-dir-delete-btn"
                          @click="removeExtraDir(idx)"
                        />
                      </div>
                      <el-button
                        :icon="Plus"
                        plain
                        size="small"
                        class="extra-dirs-add-btn"
                        @click="addExtraDir"
                      >添加目录</el-button>
                    </div>
                    <div class="form-hint">项目模式下文件工具默认只能访问项目目录，此处可追加其他允许路径</div>
                  </el-form-item>

                  <el-form-item label="名称" required>
                    <el-input ref="nameInputRef" v-model="form.name" placeholder="例如：code-assistant、researcher" />
                    <div class="form-hint">只能使用英文字母、数字、连字符(-)和下划线(_)，且必须以字母开头</div>
                  </el-form-item>

                  <el-form-item label="显示名称">
                    <el-input v-model="form.display_name" placeholder="可填中文，例如：代码助手（留空则显示名称字段）" />
                  </el-form-item>

                  <el-form-item label="模型">
                    <el-select v-model="form.default_model" filterable style="width:100%" placeholder="选择默认模型">
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
                        @update:model-value="toggleTemperature"
                      >为此预设固定温度值</el-checkbox>
                      <div v-if="form.llm_params?.temperature !== undefined" class="temperature-preset-control">
                        <el-slider
                          :model-value="form.llm_params.temperature"
                          :min="0"
                          :max="2"
                          :step="0.05"
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
                        @update:model-value="toggleReasoningEffort"
                      >为此预设固定思考级别</el-checkbox>
                      <el-select
                        v-if="form.llm_params?.reasoning_effort !== undefined"
                        :model-value="form.llm_params.reasoning_effort"
                        size="small"
                        style="width: 140px; margin-top: 6px"
                        @update:model-value="setReasoningEffort"
                      >
                        <el-option v-for="effort in REASONING_EFFORTS" :key="effort" :label="effort" :value="effort" />
                      </el-select>
                      <span v-else class="param-hint">留空时由模型决定</span>
                    </div>
                  </el-form-item>

                  <el-form-item label="系统提示词">
                    <el-input
                      v-model="form.system_prompt"
                      type="textarea"
                      :autosize="{ minRows: 4, maxRows: 12 }"
                      placeholder="定义 Agent 的行为和角色..."
                    />
                  </el-form-item>

                  <el-form-item label="作为子 Agent 时候的触发描述">
                    <div class="subagent-capability-toggle">
                      <el-checkbox v-model="form.can_be_subagent">
                        可以作为子 Agent
                      </el-checkbox>
                    </div>
                    <div v-if="form.can_be_subagent" class="subagent-default-description">
                      <el-input
                        v-model="form.default_delegation_description"
                        type="textarea"
                        :autosize="{ minRows: 2, maxRows: 4 }"
                        placeholder="例如：当任务涉及数据分析、报表生成时，委托给本 Agent"
                      />
                      <div class="form-hint">
                        本 Agent 被其他 Agent 勾选为子 Agent 时，对方依据这段描述判断何时把任务委托给它
                      </div>
                    </div>
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
                            {{ group.id }}{{ group.description ? `（${group.description}）` : '' }} ({{ group.tools.length }} tools)
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

                  <el-form-item label="此agent自定义额外 Skills 目录">
                    <div class="extra-dirs-list">
                      <div
                        v-for="(dir, idx) in (form.extra_skill_dirs || [])"
                        :key="idx"
                        class="extra-dir-row"
                      >
                        <el-input
                          :model-value="dir"
                          placeholder="如 D:\\codes\\my-skills（必须是绝对路径）"
                          clearable
                          @update:model-value="(val: string) => updateExtraSkillDir(idx, val)"
                          @clear="removeExtraSkillDir(idx)"
                        />
                        <el-button
                          :icon="Delete"
                          circle
                          plain
                          type="danger"
                          size="small"
                          class="extra-dir-delete-btn"
                          @click="removeExtraSkillDir(idx)"
                        />
                      </div>
                      <el-button
                        :icon="Plus"
                        plain
                        size="small"
                        class="extra-dirs-add-btn"
                        @click="addExtraSkillDir"
                      >添加 Skills 目录</el-button>
                    </div>
                    <div class="form-hint">为该智能体额外加载指定目录下的 Skills（绝对路径）</div>
                  </el-form-item>

                  <el-form-item label="允许的全局 Skills">
                    <div class="tool-group-select">
                      <el-radio-group v-model="globalSkillsMode" size="small">
                        <el-radio-button value="all">全部</el-radio-button>
                        <el-radio-button value="none">无</el-radio-button>
                        <el-radio-button value="custom">自定义</el-radio-button>
                      </el-radio-group>
                      <div v-if="globalSkillsMode === 'custom'" v-loading="dialogSkillsLoading" class="custom-groups">
                        <el-checkbox-group v-model="selectedGlobalSkills">
                          <div
                            v-for="grp in globalSkillGroups"
                            :key="grp.key"
                            class="skill-group"
                          >
                            <div
                              class="skill-group-header"
                              :title="grp.path || ''"
                              @click="toggleSkillGroup(grp.key)"
                            >
                              <span class="skill-group-caret" :class="{ 'is-open': isSkillGroupOpen(grp.key) }">▸</span>
                              <span class="skill-group-icon">📁</span>
                              <span class="skill-group-name" :title="grp.path || grp.folder">{{ grp.folder }}</span>
                              <span class="skill-group-count">{{ grp.skills.length }}</span>
                            </div>
                            <div v-show="isSkillGroupOpen(grp.key)" class="skill-group-body">
                              <el-checkbox
                                v-for="skill in grp.skills"
                                :key="skill.name"
                                :value="skill.name"
                                class="skill-checkbox"
                              >
                                <div class="skill-item-main">
                                  <span class="skill-item-name" :title="skill.name">{{ skill.name }}</span>
                                </div>
                                <div v-if="skill.description" class="skill-item-desc" :title="skill.description">{{ skill.description }}</div>
                              </el-checkbox>
                            </div>
                          </div>
                          <div v-if="dialogGlobalSkills.length === 0" class="skill-empty-tip">暂无全局 Skills</div>
                        </el-checkbox-group>
                      </div>
                    </div>
                  </el-form-item>

                  <el-form-item v-if="dialogExtraSkills.length > 0" label="此agent自定义额外目录 Skills">
                    <div class="tool-group-select">
                      <el-radio-group v-model="extraSkillsMode" size="small">
                        <el-radio-button value="all">全部</el-radio-button>
                        <el-radio-button value="none">无</el-radio-button>
                        <el-radio-button value="custom">自定义</el-radio-button>
                      </el-radio-group>
                      <div v-if="extraSkillsMode === 'custom'" v-loading="dialogSkillsLoading" class="custom-groups">
                        <el-checkbox-group v-model="selectedExtraSkills">
                          <div
                            v-for="grp in extraSkillGroups"
                            :key="grp.key"
                            class="skill-group"
                          >
                            <div
                              class="skill-group-header"
                              :title="grp.path || ''"
                              @click="toggleSkillGroup(grp.key)"
                            >
                              <span class="skill-group-caret" :class="{ 'is-open': isSkillGroupOpen(grp.key) }">▸</span>
                              <span class="skill-group-icon">📁</span>
                              <span class="skill-group-name" :title="grp.path || grp.folder">{{ grp.folder }}</span>
                              <span class="skill-group-count">{{ grp.skills.length }}</span>
                            </div>
                            <div v-show="isSkillGroupOpen(grp.key)" class="skill-group-body">
                              <el-checkbox
                                v-for="skill in grp.skills"
                                :key="skill.name"
                                :value="skill.name"
                                class="skill-checkbox"
                              >
                                <div class="skill-item-main">
                                  <span class="skill-item-name" :title="skill.name">{{ skill.name }}</span>
                                </div>
                                <div v-if="skill.description" class="skill-item-desc" :title="skill.description">{{ skill.description }}</div>
                              </el-checkbox>
                            </div>
                          </div>
                          <div v-if="dialogExtraSkills.length === 0" class="skill-empty-tip">暂无此agent自定义额外目录 Skills</div>
                        </el-checkbox-group>
                      </div>
                    </div>
                  </el-form-item>

                  <el-form-item v-if="form.project_mode && dialogProjectSkills.length > 0" label="允许的项目 Skills">
                    <div class="form-hint" style="margin-bottom: 6px;">{{ form.project_root }}/.agents/skills/</div>
                    <div class="tool-group-select">
                      <el-radio-group v-model="projectSkillsMode" size="small">
                        <el-radio-button value="all">全部</el-radio-button>
                        <el-radio-button value="none">无</el-radio-button>
                        <el-radio-button value="custom">自定义</el-radio-button>
                      </el-radio-group>
                      <div v-if="projectSkillsMode === 'custom'" v-loading="dialogSkillsLoading" class="custom-groups">
                        <el-checkbox-group v-model="selectedProjectSkills">
                          <div
                            v-for="grp in projectSkillGroups"
                            :key="grp.key"
                            class="skill-group"
                          >
                            <div
                              class="skill-group-header"
                              :title="grp.path || ''"
                              @click="toggleSkillGroup(grp.key)"
                            >
                              <span class="skill-group-caret" :class="{ 'is-open': isSkillGroupOpen(grp.key) }">▸</span>
                              <span class="skill-group-icon">📁</span>
                              <span class="skill-group-name" :title="grp.path || grp.folder">{{ grp.folder }}</span>
                              <span class="skill-group-count">{{ grp.skills.length }}</span>
                            </div>
                            <div v-show="isSkillGroupOpen(grp.key)" class="skill-group-body">
                              <el-checkbox
                                v-for="skill in grp.skills"
                                :key="skill.name"
                                :value="skill.name"
                                class="skill-checkbox"
                              >
                                <div class="skill-item-main">
                                  <span class="skill-item-name" :title="skill.name">{{ skill.name }}</span>
                                </div>
                                <div v-if="skill.description" class="skill-item-desc" :title="skill.description">{{ skill.description }}</div>
                              </el-checkbox>
                            </div>
                          </div>
                        </el-checkbox-group>
                      </div>
                    </div>
                  </el-form-item>

                </el-tab-pane>

                <el-tab-pane label="关联子Agent" name="subagents">
                  <div class="subagent-picker">
                    <section class="general-purpose-subagent">
                      <div class="general-purpose-header">
                        <div class="general-purpose-title">
                          <span class="general-purpose-icon">◎</span>
                          <span>通用子 Agent</span>
                          <el-tag
                            size="small"
                            :type="form.enable_general_purpose_subagent ? 'success' : 'info'"
                            effect="plain"
                          >{{ form.enable_general_purpose_subagent ? '已启用' : '未启用' }}</el-tag>
                        </div>
                        <el-checkbox v-model="form.enable_general_purpose_subagent">
                          启用通用子 Agent
                        </el-checkbox>
                      </div>
                      <p class="general-purpose-description">
                        让当前 Agent 可以把复杂任务委派给一个同能力的隔离 worker。该 worker 不会继续调用 task。
                      </p>
                    </section>
                    <section class="specialized-subagent-section">
                      <div class="specialized-section-header">
                        <div>
                          <h3>专业子 Agent</h3>
                          <p>勾选后，默认使用各子 Agent 自身的委托描述，必要时可单独覆盖。</p>
                        </div>
                        <span class="specialized-section-count">{{ availableSubagents.length }} 个可用</span>
                      </div>
                      <p class="specialized-section-prerequisite-hint">
                        想让某个 Agent 出现在下方列表中，请先进入对应 Agent 的设置，勾选「可以作为子 Agent」。
                      </p>
                      <div class="subagent-list">
                      <div v-for="sa in availableSubagents" :key="sa.id" class="subagent-item">
                        <el-checkbox
                          :model-value="isSubagentSelected(sa.id)"
                          @update:model-value="toggleSubagent(sa.id, $event)"
                        >
                          <span class="sa-item-name">{{ sa.display_name || sa.name }}</span>
                          <el-tag
                            size="small"
                            :type="sa.source === 'code' ? 'info' : sa.source === 'builtin' ? 'warning' : 'primary'"
                            style="margin-left: 6px;"
                          >{{ sa.source }}</el-tag>
                          <el-tag
                            v-if="isSubagentSelected(sa.id)"
                            size="small"
                            :type="isSubagentOverridden(sa.id) ? 'warning' : 'success'"
                            class="sa-mode-tag"
                            :title="isSubagentOverridden(sa.id)
                              ? '使用此处的覆盖描述，不用该子 Agent 的默认委托描述'
                              : '使用该子 Agent 自身配置的默认委托描述，可在其「基本设置」中修改'"
                          >{{ isSubagentOverridden(sa.id) ? '使用覆盖委托描述' : '使用默认委托描述' }}</el-tag>
                        </el-checkbox>
                        <span v-if="sa.description" class="sa-item-desc">{{ sa.description }}</span>
                        <span v-else class="sa-item-desc sa-item-desc--empty">未设置默认委托描述，勾选后需填写覆盖描述</span>
                        <div v-if="isSubagentSelected(sa.id)" class="subagent-delegation-section">
                          <div class="subagent-override-row">
                            <button
                              type="button"
                              class="subagent-override-toggle"
                              @click="toggleSubagentOverrideOpen(sa.id)"
                            >
                              <span class="override-caret" :class="{ 'is-open': isSubagentOverrideOpen(sa.id) }">▸</span>
                              自定义覆盖
                            </button>
                            <el-button
                              v-if="isSubagentOverridden(sa.id)"
                              text
                              size="small"
                              type="primary"
                              @click="resetSubagentDelegation(sa.id)"
                            >恢复默认</el-button>
                          </div>
                          <template v-if="isSubagentOverrideOpen(sa.id) || isSubagentOverridden(sa.id)">
                            <p class="subagent-delegation-help">
                              覆盖该子 Agent 的触发描述：主 Agent 什么情况下应把任务委托给它。留空则使用上面的默认描述。
                            </p>
                            <el-input
                              :model-value="getSubagentDelegationDescription(sa.id)"
                              type="textarea"
                              :autosize="{ minRows: 2, maxRows: 4 }"
                              placeholder="例如：当对话涉及数据分析、报表生成时调用它"
                              class="subagent-delegation-input"
                              @update:model-value="setSubagentDelegationDescription(sa.id, $event)"
                            />
                          </template>
                        </div>
                      </div>
                    </div>
                    </section>
                    <el-empty v-if="availableSubagents.length === 0" description="暂无可用的子 Agent" :image-size="60" />
                  </div>
                </el-tab-pane>

                <el-tab-pane label="关联提示词" name="prompts_tab">
                  <div class="bound-prompts-section" v-loading="promptBindingLoading">
                    <p class="picker-hint">
                      勾选要追加注入到此 Agent 系统提示词的提示词模板。提示词在「提示词管理」中集中管理，修改后对所有绑定的 Agent 立即生效。
                    </p>
                    <template v-if="promptsStore.prompts.length">
                      <div
                        v-for="pt in promptsStore.prompts"
                        :key="pt.id"
                        class="prompt-binding-item"
                      >
                        <el-checkbox
                          :model-value="boundPromptIds.includes(pt.id)"
                          @update:model-value="toggleBoundPrompt(pt.id, $event)"
                        >
                          <span class="prompt-binding-name">{{ pt.name }}</span>
                        </el-checkbox>
                        <p v-if="pt.content" class="prompt-binding-preview">
                          {{ pt.content.length > 100 ? pt.content.slice(0, 100) + '…' : pt.content }}
                        </p>
                      </div>
                    </template>
                    <div v-else>
                      <el-empty
                        :description="isMobile ? '暂无提示词，点击顶部「📚 提示词管理」tab 创建' : '暂无提示词，请点击弹窗顶部「📚 提示词管理」tab 进行创建'"
                        :image-size="60"
                      />
                      <div style="text-align:center; margin-top: -8px;">
                        <el-button v-if="!isReadOnly" text type="primary" @click="switchToPromptsView">
                          前往提示词管理
                        </el-button>
                      </div>
                    </div>
                  </div>
                </el-tab-pane>
              </el-tabs>
            </el-form>
          </div>

          <!-- Footer actions -->
          <div class="form-footer">
            <el-button type="info" @click="visible = false">关闭</el-button>
            <div class="form-footer-right">
              <el-button v-if="!isReadOnly && canCopy" type="success" @click="handleCopy">克隆</el-button>
              <el-button v-if="!isReadOnly && canDelete" type="danger" @click="handleDelete">删除</el-button>
              <el-button v-if="!isReadOnly && !isCodeAgent" type="primary" :loading="saving" @click="handleSave">
                {{ isPendingNew ? '创建' : '保存' }}
              </el-button>
            </div>
          </div>
        </template>

        <div v-else class="empty-placeholder">
          <el-empty
            :description="isMobile ? '从上方选择 Agent 或点 + 新建' : '从左侧选择 Agent 或新建'"
            :image-size="80"
          />
        </div>
        </template><!-- end v-else (viewMode === 'agents') -->

      </div>
    </div>

    <!-- Project mode help nested dialog -->
    <el-dialog
      v-model="showProjectModeHelp"
      title="项目文件夹模式说明"
      :width="isMobile ? 'calc(100vw - 24px)' : '520px'"
      :align-center="isMobile"
      :append-to-body="true"
    >
      <div class="project-mode-help" :class="{ 'project-mode-help--mobile': isMobile }">
        <p>开启"项目模式"后，该 Agent 将以项目文件夹为中心运行，类似 Cursor / Codex 打开一个项目的体验：</p>
        <ul>
          <li><strong>项目上下文注入</strong> — 自动将 git 状态快照、当前分支、最近提交、OS 信息注入系统提示词</li>
          <li><strong>AGENTS.md 注入</strong> — 自动读取 <code>{project_root}/AGENTS.md</code> 作为系统指令的一部分</li>
          <li><strong>项目 Skills</strong> — 自动加载 <code>{project_root}/.agents/skills/</code> 下的技能定义</li>
          <li><strong>项目 MCP</strong> — 自动连接 <code>{project_root}/.agents/mcp.json</code> 中声明的 MCP 服务</li>
          <li><strong>文件工具范围</strong> — 文件读写工具默认只能访问项目目录（及"额外允许目录"）</li>
          <li><strong>命令工作目录</strong> — <code>run_command</code> 的默认 CWD 为项目根目录</li>
        </ul>
        <p style="margin-top: 8px; color: var(--el-text-color-secondary); font-size: 12px;">
          git 状态是会话开始时的快照，如需刷新可让 Agent 执行 <code>run_command</code> 更新。
        </p>
        <div style="margin-top: 12px; padding: 10px 12px; background: var(--el-fill-color-light); border-radius: 8px; border-left: 3px solid var(--el-color-primary); font-size: 13px; line-height: 1.6;">
          <strong>💡 编程项目强烈推荐</strong>：在全局配置文件config.jsonc中配置
          <a href="https://github.com/colbymchenry/codegraph" target="_blank" rel="noopener noreferrer" style="color: var(--el-color-primary);">codegraph</a>
          MCP，让 Agent 获得代码智能分析能力（AST 级符号索引、调用链追踪、影响范围分析），大幅提升编码效率。
          <br/>① 在项目根目录运行 <code>codegraph init</code> 完成索引
          <br/>② 在 <code>config.jsonc</code> 的 <code>mcpServers</code> 中添加：
          <pre style="margin: 6px 0 0; padding: 8px 10px; background: var(--el-bg-color); border-radius: 6px; font-size: 12px; line-height: 1.5; overflow-x: auto;">"codegraph": {
  "type": "stdio",
  "command": "codegraph",
  "args": ["serve", "--mcp"]
}</pre>
        </div>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { InputInstance } from 'element-plus'
import { QuestionFilled, Folder, Plus, Delete } from '@element-plus/icons-vue'
import { useMediaQuery } from '@vueuse/core'
import { fetchAvailableSubagents, api } from '@/api/http'
import { renderMarkdown } from '@/utils/markdown'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore, type AgentPreset, type AgentSubagentConfig } from '@/stores/agents'
import { usePromptsStore } from '@/stores/prompts'
import { useAuthStore } from '@/stores/auth'

const REASONING_EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max', 'ultra']

const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()
const promptsStore = usePromptsStore()
const authStore = useAuthStore()

const visible = ref(false)
const saving = ref(false)
const activeTab = ref('basic')
const showProjectModeHelp = ref(false)

// ===== View mode (agents | prompts) =====
const viewMode = ref<'agents' | 'prompts'>('agents')

// Sidebar state
const selectedAgentId = ref<string | null>(null)
const isPendingNew = ref(false)

// Dirty tracking
const isDirty = ref(false)
const formLoading = ref(false)
let _loadSeq = 0

// Ref for name input focus after copy
const nameInputRef = ref<InputInstance | null>(null)

// ===== Prompt library state =====
const editingPromptId = ref<string | null>(null)
const isNewPrompt = ref(false)
const promptSaving = ref(false)
const promptForm = ref({ name: '', content: '' })
const promptPreviewMode = ref(false)
const renderedPromptContent = computed(() => renderMarkdown(promptForm.value.content))

function switchToPromptsView() {
  if (viewMode.value === 'prompts') return  // already active, don't reset
  viewMode.value = 'prompts'
  editingPromptId.value = null
  isNewPrompt.value = false
  promptsStore.fetchPrompts()
}

function switchToAgentsView() {
  viewMode.value = 'agents'
}

function handleNewPrompt() {
  editingPromptId.value = null
  isNewPrompt.value = true
  promptForm.value = { name: '', content: '' }
}

function selectPromptForEdit(id: string) {
  const pt = promptsStore.getById(id)
  if (!pt) return
  editingPromptId.value = id
  isNewPrompt.value = false
  promptForm.value = { name: pt.name, content: pt.content }
}

function cancelEditPrompt() {
  editingPromptId.value = null
  isNewPrompt.value = false
}

function onMobilePromptSelectChange(val: string | null | undefined) {
  editingPromptId.value = val ?? null
  if (val) selectPromptForEdit(val)
  else cancelEditPrompt()
}

async function handleSavePrompt() {
  if (!promptForm.value.name.trim()) {
    ElMessage.error('提示词名称不能为空')
    return
  }
  promptSaving.value = true
  try {
    if (isNewPrompt.value) {
      const created = await promptsStore.createPrompt(promptForm.value)
      isNewPrompt.value = false
      editingPromptId.value = created.id
      ElMessage.success('提示词已创建')
    } else if (editingPromptId.value) {
      await promptsStore.updatePrompt(editingPromptId.value, promptForm.value)
      ElMessage.success('提示词已保存')
    }
  } catch {
    ElMessage.error('保存失败，请检查后端服务')
  } finally {
    promptSaving.value = false
  }
}

async function handleDeletePrompt() {
  if (!editingPromptId.value) return
  const pt = promptsStore.getById(editingPromptId.value)
  try {
    await ElMessageBox.confirm(
      `确定要删除提示词「${pt?.name}」吗？已绑定此提示词的 Agent 将无法删除，需先解绑。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    try {
      await promptsStore.deletePrompt(editingPromptId.value)
      editingPromptId.value = null
      isNewPrompt.value = false
      ElMessage.success('提示词已删除')
    } catch (e: any) {
      const detail = e?.message || ''
      if (detail.includes('409') || detail.includes('in use')) {
        ElMessage.error('该提示词已被 Agent 使用，请先在 Agent 的「关联提示词」tab 中解绑后再删除')
      } else {
        ElMessage.error('删除失败')
      }
    }
  } catch {
    // cancelled
  }
}

// ===== Agent prompt binding state =====
const boundPromptIds = ref<string[]>([])
const promptBindingLoading = ref(false)

async function _loadBoundPrompts(agentId: string, seq: number) {
  if (!agentId) return
  promptBindingLoading.value = true
  try {
    const ids = await api.getAgentPrompts(agentId)
    if (seq !== _loadSeq) return  // stale load, discard result
    boundPromptIds.value = ids
  } catch {
    if (seq !== _loadSeq) return
    boundPromptIds.value = []
  } finally {
    if (seq === _loadSeq) promptBindingLoading.value = false
  }
}

function toggleBoundPrompt(promptId: string, checked: boolean | string | number) {
  if (checked) {
    if (!boundPromptIds.value.includes(promptId)) {
      boundPromptIds.value = [...boundPromptIds.value, promptId]
    }
  } else {
    boundPromptIds.value = boundPromptIds.value.filter(id => id !== promptId)
  }
  isDirty.value = true
}

// ===== Mobile detection =====

const isMobile = useMediaQuery('(max-width: 760px)')

const _PENDING_NEW_VALUE = '__pending_new__'

const mobileAgentSelectValue = computed({
  get() {
    if (isPendingNew.value) return _PENDING_NEW_VALUE
    return selectedAgentId.value ?? ''
  },
  set(val: string) {
    if (val === _PENDING_NEW_VALUE) {
      void handleNewAgent()
      return
    }
    if (val) void trySelectAgent(val)
  },
})

const agentSelectOptions = computed(() => {
  const opts: { value: string; label: string }[] = agentsStore.agents.map(a => ({
    value: a.id,
    label: `${getAgentIcon(a)} ${a.display_name || a.name}`,
  }))
  if (isPendingNew.value) {
    opts.unshift({ value: _PENDING_NEW_VALUE, label: '✨ 新 Agent（未保存）' })
  }
  return opts
})

// ===== Computed =====

const isCodeAgent = computed(() => {
  if (isPendingNew.value || !selectedAgentId.value) return false
  return agentsStore.agents.find(a => a.id === selectedAgentId.value)?.source === 'code'
})

const isSelectedBuiltin = computed(() => {
  if (!selectedAgentId.value) return false
  return agentsStore.isAgentBuiltin(selectedAgentId.value)
})

const canCopy = computed(() =>
  !isPendingNew.value && !isCodeAgent.value && !isSelectedBuiltin.value
)

const canDelete = computed(() =>
  !isPendingNew.value && !isCodeAgent.value && !isSelectedBuiltin.value
)

const isReadOnly = computed(() => authStore.authRequired === true && !authStore.isAdmin)

// ===== Form state =====

const toolGroupMode = ref<'all' | 'none' | 'custom'>('none')
const selectedGroups = ref<string[]>([])
const mcpMode = ref<'all' | 'none' | 'custom'>('none')
const selectedMcpServers = ref<string[]>([])
const globalSkillsMode = ref<'all' | 'none' | 'custom'>('none')
const selectedGlobalSkills = ref<string[]>([])
const projectSkillsMode = ref<'all' | 'none' | 'custom'>('all')
const selectedProjectSkills = ref<string[]>([])
const extraSkillsMode = ref<'all' | 'none' | 'custom'>('all')
const selectedExtraSkills = ref<string[]>([])
const availableSubagents = ref<Array<{
  id: string
  name: string
  display_name: string | null
  source: string
  description: string
}>>([])

// Skills lists
type DialogSkill = { name: string; description: string; path: string | null; scope: 'global' | 'project' | 'extra'; enabled: boolean }
type SkillGroup = { key: string; folder: string; path: string | null; skills: DialogSkill[] }
const dialogAllSkills = ref<DialogSkill[]>([])
const dialogSkillsLoading = ref(false)
const dialogGlobalSkills = computed(() => dialogAllSkills.value.filter(s => s.scope === 'global'))
const dialogProjectSkills = computed(() => dialogAllSkills.value.filter(s => s.scope === 'project'))
const dialogExtraSkills = computed(() => dialogAllSkills.value.filter(s => s.scope === 'extra'))

// Tree grouping: group skills by their containing collection folder, derived from the
// skill path `<collection>/<skillFolder>/SKILL.md` by dropping the filename and skill folder.
function groupSkillsByFolder(skills: DialogSkill[]): SkillGroup[] {
  const groups = new Map<string, SkillGroup>()
  for (const s of skills) {
    let key: string
    let folder: string
    let path: string | null
    if (s.path) {
      const parts = s.path.split(/[\\/]+/).filter(Boolean)
      // remove filename (SKILL.md)
      parts.pop()
      // remove the skill folder name (skill lives one level under its collection)
      parts.pop()
      path = parts.join('\\')
      key = path || '__root__'
      // Full collection path instead of the last folder segment
      folder = path || '其他'
    } else {
      key = '__root__'
      path = null
      folder = '其他'
    }
    if (!groups.has(key)) {
      groups.set(key, { key, folder, path, skills: [] })
    }
    groups.get(key)!.skills.push(s)
  }
  const list = [...groups.values()]
  list.sort((a, b) => a.folder.localeCompare(b.folder, 'zh-Hans-CN'))
  list.forEach(g => g.skills.sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN')))
  return list
}

const globalSkillGroups = computed(() => groupSkillsByFolder(dialogGlobalSkills.value))
const projectSkillGroups = computed(() => groupSkillsByFolder(dialogProjectSkills.value))
const extraSkillGroups = computed(() => groupSkillsByFolder(dialogExtraSkills.value))

// Expanded state: groups default to expanded (undefined === expanded).
const expandedSkillGroups = reactive<Record<string, boolean>>({})
function toggleSkillGroup(key: string) {
  expandedSkillGroups[key] = expandedSkillGroups[key] !== false
}
function isSkillGroupOpen(key: string): boolean {
  return expandedSkillGroups[key] !== false
}

let _skillFetchSeq = 0

async function fetchDialogSkills() {
  const seq = ++_skillFetchSeq
  dialogSkillsLoading.value = true
  try {
    const projectRoot = (form.value.project_mode && form.value.project_root.trim())
      ? form.value.project_root.trim()
      : undefined
    const extraDirs = (form.value.extra_skill_dirs || []).map(d => d.trim()).filter(Boolean)
    const result = await api.getSkills(projectRoot, extraDirs)
    if (seq !== _skillFetchSeq) return
    dialogAllSkills.value = result
    const globalNames = new Set(result.filter((s: any) => s.scope === 'global').map((s: any) => s.name))
    const projectNames = new Set(result.filter((s: any) => s.scope === 'project').map((s: any) => s.name))
    const extraNames = new Set(result.filter((s: any) => s.scope === 'extra').map((s: any) => s.name))
    selectedGlobalSkills.value = selectedGlobalSkills.value.filter(n => globalNames.has(n))
    selectedProjectSkills.value = selectedProjectSkills.value.filter(n => projectNames.has(n))
    selectedExtraSkills.value = selectedExtraSkills.value.filter(n => extraNames.has(n))
  } catch (e) {
    if (seq !== _skillFetchSeq) return
    console.error('[AgentManagerDialog] Failed to fetch skills:', e)
    dialogAllSkills.value = []
    ElMessage.warning('加载 Skills 列表失败，请检查后端服务')
  } finally {
    if (seq === _skillFetchSeq) dialogSkillsLoading.value = false
  }
}

const form = ref({
  name: '',
  display_name: '',
  system_prompt: '',
  default_model: '',
  default_delegation_description: '',
  can_be_subagent: false,
  llm_params: null as Record<string, any> | null,
  subagents: [] as AgentSubagentConfig[],
  enable_general_purpose_subagent: false,
  project_mode: false,
  project_root: '',
  project_extra_dirs: null as string[] | null,
  extra_skill_dirs: null as string[] | null,
})

function addExtraSkillDir() {
  form.value.extra_skill_dirs = [...(form.value.extra_skill_dirs || []), '']
}

function updateExtraSkillDir(idx: number, value: string) {
  if (!form.value.extra_skill_dirs) return
  form.value.extra_skill_dirs[idx] = value
}

function removeExtraSkillDir(idx: number) {
  if (!form.value.extra_skill_dirs) return
  const next = form.value.extra_skill_dirs.filter((_, i) => i !== idx)
  form.value.extra_skill_dirs = next.length > 0 ? next : null
}

function addExtraDir() {
  form.value.project_extra_dirs = [...(form.value.project_extra_dirs || []), '']
}

function updateExtraDir(idx: number, value: string) {
  if (!form.value.project_extra_dirs) return
  form.value.project_extra_dirs[idx] = value
}

function removeExtraDir(idx: number) {
  if (!form.value.project_extra_dirs) return
  const next = form.value.project_extra_dirs.filter((_, i) => i !== idx)
  form.value.project_extra_dirs = next.length > 0 ? next : null
}

// Watch form changes for dirty tracking (skip during load)
watch(form, () => {
  if (formLoading.value) return
  isDirty.value = true
}, { deep: true })

watch([toolGroupMode, mcpMode, globalSkillsMode, projectSkillsMode, extraSkillsMode], () => {
  if (formLoading.value) return
  isDirty.value = true
})

watch([selectedGroups, selectedMcpServers, selectedGlobalSkills, selectedProjectSkills, selectedExtraSkills], () => {
  if (formLoading.value) return
  isDirty.value = true
}, { deep: true })

// Re-fetch skills when project config changes
let _skillFetchTimer: ReturnType<typeof setTimeout> | null = null
watch([() => form.value.project_root, () => form.value.project_mode], () => {
  if (!visible.value || formLoading.value) return
  projectSkillsMode.value = 'all'
  selectedProjectSkills.value = []
  if (_skillFetchTimer) clearTimeout(_skillFetchTimer)
  _skillFetchTimer = setTimeout(() => {
    _skillFetchTimer = null
    if (visible.value) fetchDialogSkills()
  }, 400)
})

// Re-fetch skills when extra skill dirs change
watch(() => form.value.extra_skill_dirs, () => {
  if (!visible.value || formLoading.value) return
  extraSkillsMode.value = 'all'
  selectedExtraSkills.value = []
  if (_skillFetchTimer) clearTimeout(_skillFetchTimer)
  _skillFetchTimer = setTimeout(() => {
    _skillFetchTimer = null
    if (visible.value) fetchDialogSkills()
  }, 600)
}, { deep: true })

// Clean up pending timer when dialog closes
watch(visible, (v) => {
  if (!v && _skillFetchTimer) {
    clearTimeout(_skillFetchTimer)
    _skillFetchTimer = null
  }
})

// ===== Helper functions =====

function getAgentIcon(agent: AgentPreset): string {
  if (agent.source === 'code') return '⚙️'
  if (agent.id === 'chat') return '💬'
  if (agent.id === 'empty') return '🧩'
  if (agent.source === 'builtin') return '✨'
  if (agent.project_mode) return '📁'
  return '🤖'
}

function _distributeAllowedSkills(allowedSkills: string[] | null) {
  const globalNames = new Set(dialogGlobalSkills.value.map(s => s.name))
  const projectNames = new Set(dialogProjectSkills.value.map(s => s.name))
  const extraNames = new Set(dialogExtraSkills.value.map(s => s.name))
  const hasProject = projectNames.size > 0
  const hasExtra = extraNames.size > 0

  if (allowedSkills === null) {
    globalSkillsMode.value = 'all'; selectedGlobalSkills.value = []
    projectSkillsMode.value = 'all'; selectedProjectSkills.value = []
    extraSkillsMode.value = 'all'; selectedExtraSkills.value = []
    return
  }
  if (allowedSkills.length === 0) {
    globalSkillsMode.value = 'none'; selectedGlobalSkills.value = []
    projectSkillsMode.value = 'none'; selectedProjectSkills.value = []
    extraSkillsMode.value = 'none'; selectedExtraSkills.value = []
    return
  }
  const allowedSet = new Set(allowedSkills)
  const allowedGlobal = [...globalNames].filter(n => allowedSet.has(n))
  if (allowedGlobal.length === 0) {
    globalSkillsMode.value = 'none'; selectedGlobalSkills.value = []
  } else if (allowedGlobal.length === globalNames.size) {
    globalSkillsMode.value = 'all'; selectedGlobalSkills.value = []
  } else {
    globalSkillsMode.value = 'custom'; selectedGlobalSkills.value = allowedGlobal
  }
  if (!hasProject) {
    projectSkillsMode.value = 'all'; selectedProjectSkills.value = []
  } else {
    const allowedProject = [...projectNames].filter(n => allowedSet.has(n))
    if (allowedProject.length === 0) {
      projectSkillsMode.value = 'none'; selectedProjectSkills.value = []
    } else if (allowedProject.length === projectNames.size) {
      projectSkillsMode.value = 'all'; selectedProjectSkills.value = []
    } else {
      projectSkillsMode.value = 'custom'; selectedProjectSkills.value = allowedProject
    }
  }
  if (!hasExtra) {
    extraSkillsMode.value = 'all'; selectedExtraSkills.value = []
  } else {
    const allowedExtra = [...extraNames].filter(n => allowedSet.has(n))
    if (allowedExtra.length === 0) {
      extraSkillsMode.value = 'none'; selectedExtraSkills.value = []
    } else if (allowedExtra.length === extraNames.size) {
      extraSkillsMode.value = 'all'; selectedExtraSkills.value = []
    } else {
      extraSkillsMode.value = 'custom'; selectedExtraSkills.value = allowedExtra
    }
  }
}

function _computeAllowedSkills(): string[] | null {
  const hasProject = dialogProjectSkills.value.length > 0
  const hasExtra = dialogExtraSkills.value.length > 0
  const effectiveProjectMode = hasProject ? projectSkillsMode.value : 'all'
  const effectiveExtraMode = hasExtra ? extraSkillsMode.value : 'all'
  if (globalSkillsMode.value === 'all' && effectiveProjectMode === 'all' && effectiveExtraMode === 'all') return null
  const globalAllowed =
    globalSkillsMode.value === 'all' ? dialogGlobalSkills.value.map(s => s.name) :
    globalSkillsMode.value === 'none' ? [] :
    selectedGlobalSkills.value
  const projectAllowed = !hasProject ? [] :
    projectSkillsMode.value === 'all' ? dialogProjectSkills.value.map(s => s.name) :
    projectSkillsMode.value === 'none' ? [] :
    selectedProjectSkills.value
  const extraAllowed = !hasExtra ? [] :
    extraSkillsMode.value === 'all' ? dialogExtraSkills.value.map(s => s.name) :
    extraSkillsMode.value === 'none' ? [] :
    selectedExtraSkills.value
  return [...globalAllowed, ...projectAllowed, ...extraAllowed]
}

function _applyAgentToToolsMode(agent: AgentPreset) {
  if (agent.allowed_tool_groups === null) {
    toolGroupMode.value = 'all'; selectedGroups.value = []
  } else if (agent.allowed_tool_groups.length === 0) {
    toolGroupMode.value = 'none'; selectedGroups.value = []
  } else {
    toolGroupMode.value = 'custom'; selectedGroups.value = [...agent.allowed_tool_groups]
  }
  if (agent.allowed_mcp_servers === null) {
    mcpMode.value = 'all'; selectedMcpServers.value = []
  } else if (agent.allowed_mcp_servers.length === 0) {
    mcpMode.value = 'none'; selectedMcpServers.value = []
  } else {
    mcpMode.value = 'custom'; selectedMcpServers.value = [...agent.allowed_mcp_servers]
  }
}

/**
 * Populate form fields from an agent, fetch subagents + skills in parallel,
 * and return the list of available subagents.
 * Callers must perform their own _loadSeq check after awaiting.
 */
async function _populateFormFromAgent(
  agent: AgentPreset,
  opts: { nameOverride?: string; excludeAgentId?: string } = {}
) {
  form.value.name = opts.nameOverride ?? agent.name
  form.value.display_name = agent.display_name ?? ''
  form.value.system_prompt = agent.system_prompt
  form.value.default_model = agent.default_model
  form.value.default_delegation_description = agent.default_delegation_description ?? ''
  form.value.can_be_subagent = agent.can_be_subagent ?? false
  form.value.llm_params = agent.llm_params ? { ...agent.llm_params } : null
  form.value.subagents = agent.subagents ? agent.subagents.map(item => ({ ...item })) : []
  form.value.enable_general_purpose_subagent = agent.enable_general_purpose_subagent ?? false
  form.value.project_mode = agent.project_mode ?? false
  form.value.project_root = agent.project_root ?? ''
  form.value.project_extra_dirs = agent.project_extra_dirs ? [...agent.project_extra_dirs] : null
  form.value.extra_skill_dirs = agent.extra_skill_dirs ? [...agent.extra_skill_dirs] : null
  _resetSubagentOverrideOpen()
  _applyAgentToToolsMode(agent)

  const [allSubagents] = await Promise.all([
    fetchAvailableSubagents(),
    fetchDialogSkills(),  // reads form.value.project_root set above
  ])
  const filtered = opts.excludeAgentId
    ? allSubagents.filter(sa => sa.id !== opts.excludeAgentId)
    : allSubagents
  return { subagents: filtered }
}

async function _loadAgentIntoForm(agent: AgentPreset) {
  const seq = ++_loadSeq
  formLoading.value = true
  activeTab.value = 'basic'

  try {
    const [{ subagents }] = await Promise.all([
      _populateFormFromAgent(agent, { excludeAgentId: agent.id }),
      _loadBoundPrompts(agent.id, seq),
      promptsStore.prompts.length === 0 ? promptsStore.fetchPrompts() : Promise.resolve(),
    ])
    if (seq !== _loadSeq) return  // a newer load started; discard stale result

    availableSubagents.value = subagents
    _distributeAllowedSkills(agent.allowed_skills)

    await nextTick()
    if (seq !== _loadSeq) return
    isDirty.value = false
  } catch (err: any) {
    if (seq !== _loadSeq) return
    availableSubagents.value = []
    ElMessage.error(err?.message || '加载 Agent 失败，请重试')
  } finally {
    if (seq === _loadSeq) formLoading.value = false
  }
}

async function _loadNewForm() {
  const seq = ++_loadSeq
  formLoading.value = true
  activeTab.value = 'basic'
  form.value = {
    name: '',
    display_name: '',
    system_prompt: '',
    default_model: toolsStore.currentModel,
    default_delegation_description: '',
    can_be_subagent: false,
    llm_params: null,
    subagents: [],
    enable_general_purpose_subagent: false,
    project_mode: false,
    project_root: '',
    project_extra_dirs: null,
    extra_skill_dirs: null,
  }
  _resetSubagentOverrideOpen()
  toolGroupMode.value = 'none'; selectedGroups.value = []
  mcpMode.value = 'none'; selectedMcpServers.value = []
  globalSkillsMode.value = 'none'; selectedGlobalSkills.value = []
  projectSkillsMode.value = 'none'; selectedProjectSkills.value = []
  extraSkillsMode.value = 'all'; selectedExtraSkills.value = []
  boundPromptIds.value = []

  const [allSubagents] = await Promise.all([
    fetchAvailableSubagents(),
    fetchDialogSkills(),
    promptsStore.prompts.length === 0 ? promptsStore.fetchPrompts() : Promise.resolve(),
  ])
  if (seq !== _loadSeq) return

  availableSubagents.value = allSubagents

  await nextTick()
  if (seq !== _loadSeq) return
  formLoading.value = false
  isDirty.value = false
}

async function _confirmDiscardIfDirty(): Promise<boolean> {
  if (!isDirty.value) return true
  try {
    await ElMessageBox.confirm(
      '当前有未保存的修改，切换后将丢失这些改动。',
      '放弃修改？',
      {
        confirmButtonText: '放弃修改',
        cancelButtonText: '继续编辑',
        type: 'warning',
      }
    )
    return true
  } catch {
    return false
  }
}

// ===== Public API =====

async function open(agentId?: string) {
  // Set formLoading before showing the dialog to prevent a flash of stale form data
  formLoading.value = true
  isPendingNew.value = false
  isDirty.value = false
  viewMode.value = 'agents'
  editingPromptId.value = null
  isNewPrompt.value = false
  visible.value = true

  const targetId = agentId ?? agentsStore.currentAgentId
  const agent = agentsStore.agents.find(a => a.id === targetId)
  if (agent) {
    selectedAgentId.value = targetId
    await _loadAgentIntoForm(agent)
  } else {
    // fallback: open with first agent, or empty state if no agents
    const first = agentsStore.agents[0]
    if (first) {
      selectedAgentId.value = first.id
      await _loadAgentIntoForm(first)
    } else {
      selectedAgentId.value = null
      formLoading.value = false
    }
  }
}

// ===== Actions =====

async function trySelectAgent(agentId: string) {
  if (formLoading.value) return  // prevent interrupting an ongoing load
  if (!isPendingNew.value && selectedAgentId.value === agentId) return
  if (!await _confirmDiscardIfDirty()) return
  isPendingNew.value = false
  selectedAgentId.value = agentId
  const agent = agentsStore.agents.find(a => a.id === agentId)
  if (agent) await _loadAgentIntoForm(agent)
}

async function handleNewAgent() {
  if (isReadOnly.value || formLoading.value) return
  if (!await _confirmDiscardIfDirty()) return
  selectedAgentId.value = null
  isPendingNew.value = true
  await _loadNewForm()
  nextTick(() => nameInputRef.value?.focus())
}

async function handleCopy() {
  if (isReadOnly.value || !selectedAgentId.value) return
  const agent = agentsStore.agents.find(a => a.id === selectedAgentId.value)
  if (!agent) return
  if (!await _confirmDiscardIfDirty()) return

  const seq = ++_loadSeq
  formLoading.value = true
  activeTab.value = 'basic'

  const [{ subagents }, copiedBoundIds] = await Promise.all([
    _populateFormFromAgent(agent, { nameOverride: `${agent.name}-copy` }),
    api.getAgentPrompts(agent.id).catch(() => [] as string[]),
    promptsStore.prompts.length === 0 ? promptsStore.fetchPrompts() : Promise.resolve(),
  ])
  if (seq !== _loadSeq) return

  availableSubagents.value = subagents
  _distributeAllowedSkills(agent.allowed_skills)
  boundPromptIds.value = copiedBoundIds

  selectedAgentId.value = null
  isPendingNew.value = true

  await nextTick()
  if (seq !== _loadSeq) return
  formLoading.value = false
  isDirty.value = false

  nextTick(() => {
    nameInputRef.value?.focus()
    nameInputRef.value?.select()
  })
}

async function handleDelete() {
  if (isReadOnly.value || !selectedAgentId.value) return
  try {
    await ElMessageBox.confirm(
      '确定要删除此 Agent 吗？此操作不可撤销。',
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const deletedId = selectedAgentId.value
    await agentsStore.deleteAgent(deletedId)
    selectedAgentId.value = null
    isPendingNew.value = false
    isDirty.value = false
    ElMessage.success('Agent 已删除')
  } catch {
    // user cancelled
  }
}

async function handleSave() {
  if (isReadOnly.value) return
  saving.value = true
  try {
    const namePattern = /^[a-zA-Z][a-zA-Z0-9_-]*$/
    if (!namePattern.test(form.value.name)) {
      ElMessage.error('名称只能使用英文字母、数字、连字符(-)和下划线(_)，且必须以字母开头')
      return
    }

    const allowed_tool_groups =
      toolGroupMode.value === 'all' ? null :
      toolGroupMode.value === 'none' ? [] :
      selectedGroups.value

    const allowed_mcp_servers =
      mcpMode.value === 'all' ? null :
      mcpMode.value === 'none' ? [] :
      selectedMcpServers.value

    const allowed_skills = _computeAllowedSkills()

    if (form.value.project_mode && !form.value.project_root.trim()) {
      ElMessage.error('开启项目模式时，必须填写项目根目录')
      return
    }

    if (form.value.project_mode && form.value.project_root.trim()) {
      const pathsToCheck: string[] = [form.value.project_root.trim()]
      const cleanedExtraDirs = (form.value.project_extra_dirs || []).map(d => d.trim()).filter(Boolean)
      pathsToCheck.push(...cleanedExtraDirs)
      try {
        const results = await api.checkPaths(pathsToCheck)
        const missingPaths = results.filter(r => !r.exists).map(r => r.path)
        if (missingPaths.length > 0) {
          ElMessage.error(`以下路径不存在或不是目录，请检查后重新填写：${missingPaths.join('、')}`)
          return
        }
      } catch {
        // 路径检查接口失败时不阻断保存，由后端兜底校验
      }
    }

    // Validate extra skill dirs: must be absolute paths that exist
    const cleanedSkillDirs = (form.value.extra_skill_dirs || []).map(d => d.trim()).filter(Boolean)
    if (cleanedSkillDirs.length > 0) {
      const isAbsolute = (p: string) => /^[A-Za-z]:[\\/]/.test(p) || p.startsWith('\\\\') || p.startsWith('~')
      const notAbsolute = cleanedSkillDirs.filter(d => !isAbsolute(d))
      if (notAbsolute.length > 0) {
        activeTab.value = 'basic'
        ElMessage.error(`此agent自定义额外 Skills 目录必须使用绝对路径：${notAbsolute.join('、')}`)
        return
      }
      try {
        const results = await api.checkPaths(cleanedSkillDirs)
        const missingPaths = results.filter(r => !r.exists).map(r => r.path)
        if (missingPaths.length > 0) {
          activeTab.value = 'basic'
          ElMessage.error(`以下 Skills 目录不存在或不是目录，请检查后重新填写：${missingPaths.join('、')}`)
          return
        }
      } catch {
        // 路径检查接口失败时不阻断保存，由后端兜底校验
      }
    }

    if (form.value.project_mode) {
      const FILE_TOOL_GROUPS = ['file_read', 'file_write', 'command']
      if (toolGroupMode.value === 'none') {
        activeTab.value = 'basic'
        ElMessage.error('项目模式下，工具组不能全部关闭，需要启用 file_read、file_write 和 command')
        return
      }
      if (toolGroupMode.value === 'custom') {
        const missingGroups = FILE_TOOL_GROUPS.filter(g => !selectedGroups.value.includes(g))
        if (missingGroups.length > 0) {
          activeTab.value = 'basic'
          ElMessage.error(`项目模式下必须启用以下工具组：${missingGroups.join('、')}`)
          return
        }
      }
    }

    if (form.value.can_be_subagent && !form.value.default_delegation_description.trim()) {
      activeTab.value = 'basic'
      await ElMessageBox.alert(
        '已勾选「可以作为子 Agent」，请填写「作为子 Agent 时候的触发描述」，否则其他 Agent 无法判断何时委派给它。',
        '无法保存',
        { type: 'error', confirmButtonText: '去填写' }
      )
      return
    }

    // A selected subagent needs either an override or its own default delegation
    // description, otherwise the parent agent has no signal for when to delegate.
    const subagentNoDesc = form.value.subagents
      .filter(item => !item.delegation_description.trim())
      .map(item => availableSubagents.value.find(sa => sa.id === item.agent_id))
      .filter(sa => sa && !sa.description.trim())
    if (subagentNoDesc.length > 0) {
      activeTab.value = 'subagents'
      await ElMessageBox.alert(
        `以下子 Agent 既未填写覆盖描述，也未设置默认委托描述，主 Agent 将无从判断何时委派：\n${subagentNoDesc.map(sa => `• ${sa!.display_name || sa!.name}`).join('\n')}`,
        '无法保存',
        { type: 'error', confirmButtonText: '去填写', customStyle: { whiteSpace: 'pre-line' } as any }
      )
      return
    }

    const normalizedSubagents = form.value.subagents.map(item => ({
      agent_id: item.agent_id,
      delegation_description: item.delegation_description.trim(),
    }))

    const data = {
      name: form.value.name,
      display_name: form.value.display_name || null,
      system_prompt: form.value.system_prompt,
      default_model: form.value.default_model,
      default_delegation_description: form.value.default_delegation_description.trim(),
      can_be_subagent: form.value.can_be_subagent,
      allowed_tool_groups,
      allowed_mcp_servers,
      allowed_skills,
      llm_params: form.value.llm_params || null,
      subagents: normalizedSubagents.length > 0 ? normalizedSubagents : null,
      enable_general_purpose_subagent: form.value.enable_general_purpose_subagent,
      project_mode: form.value.project_mode,
      project_root: form.value.project_mode ? (form.value.project_root?.trim() || null) : null,
      project_extra_dirs: form.value.project_mode
        ? (() => {
            const dirs = (form.value.project_extra_dirs || []).map(d => d.trim()).filter(Boolean)
            return dirs.length > 0 ? dirs : null
          })()
        : null,
      extra_skill_dirs: (() => {
        const dirs = (form.value.extra_skill_dirs || []).map(d => d.trim()).filter(Boolean)
        return dirs.length > 0 ? dirs : null
      })(),
    }

    try {
      if (isPendingNew.value) {
        const created = await agentsStore.createAgent(data as any)
        // Save prompt bindings if any were selected
        if (boundPromptIds.value.length > 0) {
          await api.setAgentPrompts(created.id, boundPromptIds.value)
        }
        isPendingNew.value = false
        selectedAgentId.value = created.id
        isDirty.value = false
        ElMessage.success('Agent 创建成功')
      } else if (selectedAgentId.value) {
        await agentsStore.updateAgent(selectedAgentId.value, data)
        await api.setAgentPrompts(selectedAgentId.value, boundPromptIds.value)
        isDirty.value = false
        ElMessage.success('Agent 已保存')
      }
    } catch (err: any) {
      ElMessage.error(err?.message || '保存失败，请重试')
    }
  } finally {
    saving.value = false
  }
}

// ===== Subagent helpers =====

// UI-only state: which subagents have their "自定义覆盖" input expanded.
const subagentOverrideOpen = reactive<Record<string, boolean>>({})

function _resetSubagentOverrideOpen() {
  Object.keys(subagentOverrideOpen).forEach(k => delete subagentOverrideOpen[k])
}

function isSubagentOverrideOpen(agentId: string) {
  return subagentOverrideOpen[agentId] === true
}

function toggleSubagentOverrideOpen(agentId: string) {
  subagentOverrideOpen[agentId] = !subagentOverrideOpen[agentId]
}

function isSubagentSelected(agentId: string) {
  return form.value.subagents.some(item => item.agent_id === agentId)
}

function isSubagentOverridden(agentId: string) {
  return !!getSubagentDelegationDescription(agentId).trim()
}

function resetSubagentDelegation(agentId: string) {
  setSubagentDelegationDescription(agentId, '')
  subagentOverrideOpen[agentId] = false
}

function getSubagentDelegationDescription(agentId: string) {
  return form.value.subagents.find(item => item.agent_id === agentId)?.delegation_description || ''
}

function toggleSubagent(agentId: string, checked: boolean | string | number) {
  if (checked) {
    if (!isSubagentSelected(agentId)) {
      form.value.subagents.push({ agent_id: agentId, delegation_description: '' })
    }
    return
  }
  form.value.subagents = form.value.subagents.filter(item => item.agent_id !== agentId)
  delete subagentOverrideOpen[agentId]
}

function setSubagentDelegationDescription(agentId: string, value: string | number) {
  const item = form.value.subagents.find(entry => entry.agent_id === agentId)
  if (!item) return
  item.delegation_description = String(value)
}

// ===== LLM param helpers =====

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
/* ===== Dialog body override ===== */
.agent-manager-dialog :deep(.el-dialog__body) {
  padding: 0;
  overflow: hidden;
  height: min(86vh, 980px);
}

.agent-manager-dialog :deep(.el-dialog__header) {
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.agent-manager-dialog :deep(.el-dialog__title) {
  font-size: 16px;
  font-weight: 700;
}

/* ===== Layout ===== */
.manager-layout {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ===== Left Sidebar ===== */
.manager-sidebar {
  width: 210px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  border-right: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-extra-light);
}

.sidebar-new-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 10px 10px 4px;
  padding: 9px 12px;
  border-radius: 8px;
  border: 1.5px dashed var(--el-color-primary);
  color: var(--el-color-primary);
  background: color-mix(in srgb, var(--el-color-primary) 5%, transparent);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s ease, transform 0.15s ease;
}

.sidebar-new-btn:hover {
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
  transform: translateY(-1px);
}

.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 8px;
  min-height: 0;
}

.agent-list-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  border: 1px solid transparent;
  transition: background 0.14s ease, border-color 0.14s ease;
}

.agent-list-item:hover {
  background: var(--el-fill-color-light);
}

.agent-list-item.is-selected {
  background: color-mix(in srgb, var(--el-color-primary) 14%, var(--el-bg-color));
  border-color: color-mix(in srgb, var(--el-color-primary) 40%, transparent);
  box-shadow: inset 3px 0 0 var(--el-color-primary);
}

.agent-list-item.is-selected .agent-item-name {
  font-weight: 700;
  color: var(--el-color-primary);
}

.agent-list-item.is-pending {
  border: 1.5px dashed var(--el-color-warning);
  background: color-mix(in srgb, var(--el-color-warning) 6%, transparent);
}

.agent-item-icon {
  font-size: 15px;
  flex-shrink: 0;
  width: 18px;
  text-align: center;
}

.agent-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.agent-item-name {
  font-size: 12px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--el-text-color-primary);
}

.pending-badge {
  font-size: 10px;
  color: var(--el-color-warning);
  font-weight: 600;
}

.source-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.source-tag--builtin {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(168, 85, 247, 0.1));
  color: #7c3aed;
  border: 1px solid rgba(124, 58, 237, 0.2);
}

.source-tag--code {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1));
  color: #059669;
  border: 1px solid rgba(5, 150, 105, 0.2);
}

.source-tag--user {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(249, 115, 22, 0.1));
  color: #d97706;
  border: 1px solid rgba(217, 119, 6, 0.2);
}

.source-tag--project {
  background: linear-gradient(135deg, rgba(14, 165, 233, 0.1), rgba(6, 182, 212, 0.1));
  color: #0284c7;
  border: 1px solid rgba(2, 132, 199, 0.2);
}

:global(html.dark) .source-tag--builtin {
  background: rgba(124, 58, 237, 0.15);
  color: #a78bfa;
  border-color: rgba(167, 139, 250, 0.25);
}

:global(html.dark) .source-tag--code {
  background: rgba(16, 185, 129, 0.15);
  color: #6ee7b7;
  border-color: rgba(110, 231, 183, 0.25);
}

:global(html.dark) .source-tag--user {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border-color: rgba(251, 191, 36, 0.25);
}

:global(html.dark) .source-tag--project {
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
  border-color: rgba(56, 189, 248, 0.25);
}

/* ===== Right content ===== */
.manager-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}

.form-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 0;
  min-height: 0;
}

.empty-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-bg-color);
}

.form-footer-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* ===== Form styles (mirrored from AgentEditorDialog) ===== */
.form-scroll :deep(.el-form-item) {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--el-fill-color-extra-light);
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.form-scroll :deep(.el-form-item:hover) {
  border-color: var(--el-border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.form-scroll :deep(.el-form-item--label-top .el-form-item__label) {
  display: inline-flex !important;
  align-items: center;
  gap: 5px;
  width: auto !important;
  height: auto !important;
  padding: 4px 10px !important;
  margin-bottom: 8px !important;
  border-radius: 999px;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color-light);
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.3 !important;
  letter-spacing: 0.4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.form-scroll :deep(.el-form-item--label-top .el-form-item__label)::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--el-color-info);
  flex-shrink: 0;
}

.form-scroll :deep(.el-form-item--label-top.is-required .el-form-item__label)::after {
  content: '*';
  color: var(--el-color-danger);
  font-size: 12px;
  margin-left: 2px;
}

.form-scroll :deep(.el-form-item--label-top .el-form-item__label .el-form-item__asterisk) {
  display: none;
}

.form-scroll :deep(.el-tabs__header) {
  position: sticky;
  top: -12px; /* 抵消 .form-scroll 的 padding-top: 12px，滚动时贴住容器顶 */
  z-index: 5;
  margin-bottom: 14px;
  background: var(--el-bg-color);
  padding-top: 12px;
  border-bottom: 2px solid var(--el-border-color-light);
}

.form-scroll :deep(.el-tabs__nav-wrap::after) {
  /* sticky 后伪元素横线会脱离 header 底部，改由 header 自身带底边 */
  display: none;
}

.form-scroll :deep(.el-tabs__content) {
  overflow: visible;
}

.form-scroll :deep(.el-tabs__item) {
  font-size: 13px;
  font-weight: 600;
}

/* Project mode fields */
.project-mode-field {
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-extra-light) 100%) !important;
  border-color: var(--el-color-primary-light-7) !important;
}

.project-mode-field:hover {
  border-color: var(--el-color-primary-light-5) !important;
}

.project-mode-field :deep(.el-form-item__label) {
  color: var(--el-color-primary) !important;
  background: var(--el-color-primary-light-9) !important;
  border-color: var(--el-color-primary-light-7) !important;
}

.project-mode-field :deep(.el-form-item__label)::before {
  background: var(--el-color-primary) !important;
}

.project-mode-field--toggle {
  border-left-width: 4px !important;
  border-left-color: var(--el-color-primary) !important;
}

.project-mode-toggle-row {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 2px 0;
}

.project-mode-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 14px;
  color: var(--el-color-primary);
}

.project-mode-label-icon {
  font-size: 15px;
}

.project-root-row {
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
}

.project-root-row .el-input {
  flex: 1;
}

.project-help-btn {
  flex-shrink: 0;
  padding: 4px 6px;
}

.extra-dirs-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.extra-dir-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.extra-dir-row .el-input {
  flex: 1;
}

.extra-dir-delete-btn {
  flex-shrink: 0;
}

.extra-dirs-add-btn {
  align-self: flex-start;
  margin-top: 2px;
}

/* Form hints */
.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 6px;
  line-height: 1.5;
}

/* Subagent capability */
.subagent-capability-toggle {
  display: block;
  width: 100%;
  margin-bottom: 8px;
}

.subagent-default-description {
  width: 100%;
}

/* LLM params */
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

/* Tool groups / MCP / Skills */
.tool-group-select {
  width: 100%;
}

.custom-groups {
  margin-top: 8px;
  padding: 10px;
  background: var(--el-fill-color-light);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
}

.custom-groups .el-checkbox {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.custom-groups .el-checkbox .el-checkbox__input {
  margin-top: 2px;
}

/* ===== Skill checkbox: 限宽 + 省略号 ===== */
/* 关键：el-checkbox-group 默认 font-size:0/line-height:0，
   加上 .el-checkbox 无宽度约束，会让描述文字无限撑宽冲出 custom-groups 边界。
   给 checkbox 与内部 label 限宽，让 overflow/ellipsis 能触发。 */
.skill-checkbox {
  width: 100% !important;
  max-width: 100% !important;
}

.skill-checkbox :deep(.el-checkbox__label) {
  width: 100% !important;
  max-width: 100% !important;
  overflow: hidden !important;
  padding-left: 8px;
}

.skill-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0; /* flex 子项：允许缩小，让 ellipsis 生效 */
}

.skill-item-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
  /* 单行省略 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  color: inherit !important;
  font-size: inherit !important;
  line-height: inherit !important;
  font-weight: 600 !important;
}

.skill-item-desc {
  font-size: 12px !important;
  line-height: 1.4 !important;
  color: var(--el-text-color-regular);
  opacity: 0.75;
  margin-top: 2px;
  margin-left: 22px; /* 与 checkbox 框后的文字左侧对齐，避开选中框宽度 */
  /* 单行省略：用户明确要求 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
}

.skill-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  /* 关键：覆盖上层 <el-checkbox-group> 默认的 font-size:0 / line-height:0，否则文字塌缩为 0 高度看不见 */
  font-size: 13px !important;
  line-height: 1.5 !important;
  font-weight: 600 !important;
  /* 轻量版：去掉整块重色长条，改为左侧一个细主题色竖条做标识，背景极淡 */
  color: var(--el-text-color-primary) !important;
  background: color-mix(in srgb, var(--el-color-primary) 5%, transparent);
  border: 1px solid transparent;
  border-left: 3px solid var(--el-color-primary);
  transition: background 0.15s ease;
}

.skill-group-header:hover {
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
}

/* 暗色：保持左侧竖条，不用深蓝长块背景 */
:global(html.dark) .skill-group-header {
  color: #e6f0ff !important;
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent) !important;
  border-color: transparent !important;
  border-left: 3px solid #7aa8ff !important;
}

:global(html.dark) .skill-group-header:hover {
  background: color-mix(in srgb, var(--el-color-primary) 20%, transparent) !important;
}

.skill-group-caret {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  font-size: 12px !important;
  line-height: 1 !important;
  color: inherit !important;
  transition: transform 0.15s ease;
}

.skill-group-caret.is-open {
  transform: rotate(90deg);
}

.skill-group-icon {
  flex-shrink: 0;
  font-size: 14px !important;
  line-height: 1 !important;
  color: inherit !important;
}

/* 暗色下数量徽标要更对比：改用白底蓝字 */
:global(html.dark) .skill-group-count {
  color: #1e3a5f;
  background: #ffffff;
}

.skill-group-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: inherit !important;
  font-size: inherit !important;
  line-height: inherit !important;
  font-weight: inherit !important;
  /* 允许 flex 放大并缩窄，让单行省略号生效，不顶走数量徽标 */
  flex: 1 1 auto;
  min-width: 0;
  max-width: 100%;
}

.skill-group-count {
  flex-shrink: 0;
  font-size: 11px !important;
  line-height: 16px !important;
  font-weight: 600 !important;
  color: var(--el-color-white);
  background: var(--el-color-primary);
  border-radius: 999px;
  padding: 0 8px;
}

.skill-group-body {
  padding: 8px 6px 6px 24px;
  border-left: 1px solid var(--el-border-color-lighter);
  margin: 0 0 4px 9px;
}

.skill-item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.skill-item-name {
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.skill-item-desc {
  font-size: 12px;
  color: var(--el-text-color-regular);
  opacity: 0.75;
  line-height: 1.4;
  margin-top: 2px;
}

.skill-empty-tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  padding: 4px 0;
}

/* Code agent readonly */
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
  flex-shrink: 0;
}

.readonly-value {
  color: var(--el-text-color-primary);
  font-size: 13px;
  text-align: right;
  word-break: break-word;
}

/* Subagents */
.subagent-picker {
  width: 100%;
}

.general-purpose-subagent {
  margin-bottom: 18px;
  padding: 14px 16px 12px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 42%, var(--el-border-color-lighter));
  border-left: 4px solid var(--el-color-primary);
  border-radius: 8px;
  background: color-mix(in srgb, var(--el-color-primary) 7%, var(--el-bg-color));
}

.general-purpose-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.general-purpose-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.general-purpose-icon {
  font-size: 20px;
  line-height: 1;
}

.general-purpose-header :deep(.el-checkbox) {
  flex-shrink: 0;
  margin-right: 0;
}

.general-purpose-description {
  margin: 9px 0 0;
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.5;
}

.picker-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin: 4px 0 10px 0;
  line-height: 1.5;
}

.subagent-prerequisite-hint {
  margin: 9px 0 0;
  padding: 7px 10px;
  border-left: 3px solid var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.5;
}

.specialized-subagent-section {
  padding-top: 2px;
}

.specialized-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin: 0 2px 10px;
}

.specialized-section-header h3 {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.specialized-section-header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.specialized-section-prerequisite-hint {
  margin: 8px 0 10px;
  padding: 7px 10px;
  border-left: 3px solid var(--el-color-warning);
  background: var(--el-color-warning-light-9);
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.5;
}

.specialized-section-count {
  flex-shrink: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.subagent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.subagent-item {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-extra-light);
}

.subagent-item :deep(.el-checkbox) {
  display: flex;
  align-items: center;
  height: auto;
  width: 100%;
}

.sa-item-name {
  font-weight: 600;
}

.sa-mode-tag {
  margin-left: 6px;
}

.sa-item-desc {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-left: 22px;
  margin-top: 2px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sa-item-desc--empty {
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.subagent-override-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.subagent-override-toggle {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  border-radius: 4px;
  transition: background 0.15s ease;
}

.subagent-override-toggle:hover {
  background: color-mix(in srgb, var(--el-color-primary) 10%, transparent);
}

.override-caret {
  display: inline-flex;
  width: 12px;
  font-size: 12px;
  transition: transform 0.15s ease;
}

.override-caret.is-open {
  transform: rotate(90deg);
}

.subagent-delegation-section {
  margin-top: 8px;
  margin-left: 22px;
}

.subagent-delegation-help {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

/* Project mode help content */
.project-mode-help {
  font-size: 14px;
  line-height: 1.8;
}

.project-mode-help ul {
  padding-left: 18px;
  margin: 8px 0;
}

.project-mode-help li {
  margin-bottom: 6px;
}

.project-mode-help code {
  background: var(--el-fill-color-light);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}

.project-mode-help--mobile {
  max-height: calc(70dvh - 60px);
  overflow-y: auto;
}

/* ===== Dialog mode header (custom #header slot) ===== */
.dialog-mode-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dialog-mode-tabs {
  display: flex;
  gap: 4px;
  background: var(--el-fill-color-light);
  padding: 3px;
  border-radius: 10px;
}

.dialog-mode-tab {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  transition: background 0.15s, color 0.15s;
  white-space: nowrap;
}

.dialog-mode-tab:hover {
  color: var(--el-text-color-primary);
}

.dialog-mode-tab.is-active {
  background: var(--el-bg-color);
  color: var(--el-text-color-primary);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}

.dialog-close-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  color: var(--el-text-color-secondary);
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.dialog-close-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

/* ===== Prompt editor (in right content area) ===== */
.prompts-editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.prompts-editor-footer {
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.prompts-editor-footer-right {
  display: flex;
  gap: 8px;
}

/* ===== Prompt content preview ===== */
.prompt-content-wrap {
  width: 100%;
}

.prompt-content-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 6px;
}

.prompt-preview {
  min-height: 120px;
  max-height: 420px;
  overflow-y: auto;
  padding: 12px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color);
  line-height: 1.6;
  word-break: break-word;
}

.prompt-preview-empty {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  text-align: center;
  padding: 40px 0;
}


/* ===== Bound prompts tab ===== */
.bound-prompts-section {
  padding: 4px 0;
}

.prompt-binding-item {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-extra-light);
  margin-bottom: 8px;
  transition: border-color 0.15s;
}

.prompt-binding-item:hover {
  border-color: var(--el-border-color);
}

.prompt-binding-name {
  font-weight: 600;
  font-size: 13px;
}

.prompt-binding-preview {
  margin: 4px 0 0 26px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ===== Mobile layout ===== */
@media (max-width: 760px) {
  /* agent-manager-dialog class 就是 .el-dialog 元素本身，不能用后代选择器 */
  .agent-manager-dialog {
    width: calc(100vw - 16px) !important;
    margin: 3vh auto 0 !important;
  }

  .manager-layout {
    flex-direction: column;
  }

  .manager-sidebar {
    width: 100%;
    height: auto;
    flex-shrink: 0;
    border-right: none;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  /* Mobile: select + new-btn row */
  .mobile-sidebar-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
  }

  .mobile-agent-select {
    flex: 1;
    min-width: 0;
  }

  .mobile-new-btn {
    flex-shrink: 0;
    padding: 6px 10px;
    font-size: 14px;
    margin: 0; /* 重置 .sidebar-new-btn 的 margin: 10px 10px 4px */
  }

  /* 缩减表单区水平内边距，给内容更多空间 */
  .form-scroll {
    padding: 10px 10px 0;
  }

  /* 缩减每个表单项的内边距 */
  .form-scroll :deep(.el-form-item) {
    padding: 10px 10px;
  }

  .form-scroll :deep(.el-tabs__header) {
    margin-bottom: 8px;
  }

  /* 减小 tab 文字和水平内边距 */
  .form-scroll :deep(.el-tabs__item) {
    font-size: 12px;
    padding: 0 10px;
  }

  .form-footer {
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 12px;
  }

  .form-footer-right {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  /* dialog header 水平内边距收窄 */
  .agent-manager-dialog :deep(.el-dialog__header) {
    padding: 14px 14px 12px;
  }

  /* 移动端对话框标题 tab 缩小间距 */
  .dialog-mode-tab {
    padding: 5px 10px;
    font-size: 12px;
  }
}
</style>

<style>
/* Global overrides for this dialog (non-scoped) */
.agent-manager-dialog {
  border: 2px solid color-mix(in srgb, var(--el-color-primary) 38%, var(--el-border-color-lighter));
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.05),
    0 12px 32px -8px color-mix(in srgb, var(--el-color-primary) 26%, transparent);
}

.agent-manager-dialog .el-dialog__body {
  padding: 0;
  overflow: hidden;
  height: min(86vh, 980px);
}

.agent-manager-dialog .el-dialog__header {
  padding: 16px 20px 14px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.agent-manager-dialog .el-form-item {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--el-fill-color-extra-light);
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.agent-manager-dialog .el-form-item:hover {
  border-color: var(--el-border-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.agent-manager-dialog .el-form-item--label-top .el-form-item__label {
  display: inline-flex !important;
  align-items: center;
  gap: 5px;
  width: auto !important;
  height: auto !important;
  padding: 4px 10px !important;
  margin-bottom: 8px !important;
  border-radius: 999px;
  background: var(--el-fill-color);
  border: 1px solid var(--el-border-color-light);
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.3 !important;
  letter-spacing: 0.4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.agent-manager-dialog .el-form-item--label-top .el-form-item__label::before {
  content: '';
  width: 6px;
  height: 6px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--el-color-info);
}

.agent-manager-dialog .el-form-item--label-top.is-required .el-form-item__label::after {
  content: '*';
  margin-left: 2px;
  color: var(--el-color-danger);
  font-size: 12px;
}

.agent-manager-dialog .el-form-item--label-top .el-form-item__label .el-form-item__asterisk {
  display: none;
}

.agent-manager-dialog .project-mode-field {
  border-color: var(--el-color-primary-light-7) !important;
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-fill-color-extra-light) 100%) !important;
}

.agent-manager-dialog .project-mode-field--toggle {
  border-left-width: 4px !important;
  border-left-color: var(--el-color-primary) !important;
}

.agent-manager-dialog .project-mode-field .el-form-item__label {
  border-color: var(--el-color-primary-light-7) !important;
  background: var(--el-color-primary-light-9) !important;
  color: var(--el-color-primary) !important;
}

.agent-manager-dialog .project-mode-field .el-form-item__label::before {
  background: var(--el-color-primary) !important;
}

@media (max-width: 760px) {
  /* agent-manager-dialog class 就是 .el-dialog 元素本身 */
  .agent-manager-dialog {
    width: calc(100vw - 16px) !important;
    margin: 3vh auto 0 !important;
  }

  .agent-manager-dialog .el-dialog__header {
    padding: 14px 14px 12px !important;
  }

  .agent-manager-dialog .el-dialog__body {
    height: calc(92dvh - 56px) !important;
  }

  /* 移动端缩减全局表单项内边距 */
  .agent-manager-dialog .el-form-item {
    padding: 10px 10px;
  }
}

/* ===== Dark mode: Skill folder header (全局硬写，避免 scoped/:global 编译后选择器错位) ===== */
html.dark .agent-manager-dialog .skill-group-header {
  color: #e6f0ff !important;
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent) !important;
  border-color: transparent !important;
  border-left: 3px solid #7aa8ff !important;
}

html.dark .agent-manager-dialog .skill-group-header:hover {
  background: color-mix(in srgb, var(--el-color-primary) 20%, transparent) !important;
}

html.dark .agent-manager-dialog .skill-group-caret,
html.dark .agent-manager-dialog .skill-group-icon,
html.dark .agent-manager-dialog .skill-group-name {
  color: #e6f0ff !important;
}

html.dark .agent-manager-dialog .skill-group-count {
  color: #1e3a5f !important;
  background: #ffffff !important;
  border-color: #ffffff !important;
}
</style>
