<template>
  <aside class="left-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <transition name="fade">
        <span v-if="!collapsed" class="sidebar-brand">Chats</span>
      </transition>
      <div v-if="!collapsed" class="header-actions">
        <button class="action-btn" @click="toggleAllGroups" :title="allCollapsed ? '全部展开' : '全部折叠'">
          <span v-if="allCollapsed">⊞</span>
          <span v-else>⊟</span>
        </button>
        <button class="toggle-btn" @click="emit('toggleCollapse')" :title="collapsed ? '展开侧边栏' : '收起侧边栏'">
          <span class="toggle-icon" :class="{ flipped: collapsed }">«</span>
        </button>
      </div>
      <button v-else class="toggle-btn" @click="emit('toggleCollapse')" title="展开侧边栏">
        <span class="toggle-icon flipped">«</span>
      </button>
    </div>

    <div v-if="!collapsed" class="session-list">
      <Conversations
        v-model:active="currentSessionId"
        :items="conversationItems"
        :show-tooltip="true"
        :show-built-in-menu="true"
        :groupable="true"
        ungrouped-title="未分组"
        row-key="id"
        @change="handleSessionChange"
        @menu-command="handleMenuCommand"
      >
        <template #groupTitle="{ group }">
          <div class="agent-card-shell">
            <div
              class="agent-group-header"
              :data-group="group.title"
              :class="{ 'is-collapsed': collapsedGroups.has(group.title), 'is-active-agent': group.title === activeAgentName }"
              @click.stop="toggleGroup(group.title)"
            >
              <span class="agent-group-arrow" :class="{ collapsed: collapsedGroups.has(group.title) }">▶</span>
              <span class="agent-group-name">{{ group.title }}</span>
              <span class="agent-card-count">{{ group.children?.length || 0 }}</span>
            </div>
          </div>
        </template>
      </Conversations>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect, nextTick } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Conversations } from 'vue-element-plus-x'
import type { ConversationItem, ConversationMenuCommand } from 'vue-element-plus-x/types/Conversations'
import { useSessionsStore } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'

defineProps<{ collapsed: boolean }>()

const sessionsStore = useSessionsStore()
const agentsStore = useAgentsStore()
const emit = defineEmits<{ newChat: []; switchSession: [id: string]; toggleCollapse: [] }>()

const SIDEBAR_COLLAPSED_GROUPS_KEY = 'lc-agent:sidebar:collapsed-agent-groups'

function loadCollapsedGroups() {
  try {
    const raw = localStorage.getItem(SIDEBAR_COLLAPSED_GROUPS_KEY)
    const names = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(names) ? names.filter((name): name is string => typeof name === 'string') : [])
  } catch {
    return new Set<string>()
  }
}

function persistCollapsedGroups() {
  localStorage.setItem(SIDEBAR_COLLAPSED_GROUPS_KEY, JSON.stringify([...collapsedGroups.value]))
}

const collapsedGroups = ref<Set<string>>(loadCollapsedGroups())

const allCollapsed = computed(() => {
  const groupNames = new Set(conversationItems.value.map(i => i.group).filter(Boolean))
  return groupNames.size > 0 && groupNames.size === collapsedGroups.value.size
})

function toggleGroup(title: string) {
  const next = new Set(collapsedGroups.value)
  if (collapsedGroups.value.has(title)) {
    next.delete(title)
  } else {
    next.add(title)
  }
  collapsedGroups.value = next
  persistCollapsedGroups()
  nextTick(syncCollapsedDOM)
}

function syncCollapsedDOM() {
  const headers = document.querySelectorAll('.agent-group-header[data-group]')
  headers.forEach(header => {
    const groupName = header.getAttribute('data-group') || ''
    const groupItems = header.closest('.elx-conversations__group')?.querySelector('.elx-conversations__group-items') as HTMLElement | null
    if (groupItems) {
      if (collapsedGroups.value.has(groupName)) {
        groupItems.style.display = 'none'
      } else {
        groupItems.style.display = ''
      }
    }
  })
}

function toggleAllGroups() {
  if (allCollapsed.value) {
    collapsedGroups.value = new Set()
  } else {
    const groupNames = conversationItems.value
      .map(i => i.group)
      .filter((name): name is string => typeof name === 'string')
    collapsedGroups.value = new Set(groupNames)
  }
  persistCollapsedGroups()
  nextTick(syncCollapsedDOM)
}

const conversationItems = computed<ConversationItem[]>(() =>
  sessionsStore.sessions.map(s => ({
    id: s.id,
    label: s.title || 'New Chat',
    group: agentsStore.getAgentName(s.agent_id || '__chat__'),
  }))
)

const currentSessionId = computed({
  get: () => sessionsStore.currentSessionId ?? undefined,
  set: (_val: string | number | undefined) => { /* handled by @change */ },
})

const activeAgentName = computed(() => {
  const session = sessionsStore.sessions.find(s => s.id === sessionsStore.currentSessionId)
  return agentsStore.getAgentName(session?.agent_id || '__chat__')
})

watchEffect(() => {
  const groupNames = new Set(conversationItems.value.map(i => i.group).filter((name): name is string => typeof name === 'string'))
  const pruned = new Set([...collapsedGroups.value].filter(name => groupNames.has(name)))
  if (pruned.size !== collapsedGroups.value.size) {
    collapsedGroups.value = pruned
    persistCollapsedGroups()
  }
  nextTick(syncCollapsedDOM)
})

function handleSessionChange(item: ConversationItem) {
  emit('switchSession', String(item.id))
}

async function handleMenuCommand(command: ConversationMenuCommand, item: ConversationItem) {
  const id = String(item.id)
  const cmd = typeof command === 'string' ? command : String(command)

  if (cmd === 'rename') {
    try {
      const { value } = await ElMessageBox.prompt('输入新标题', '重命名', {
        inputValue: item.label || '',
        inputValidator: (v) => !!v?.trim() || '标题不能为空',
      })
      if (value?.trim()) {
        await sessionsStore.updateTitle(id, value.trim())
      }
    } catch {
      // cancelled
    }
    return
  }

  if (cmd === 'delete') {
    const wasCurrent = id === sessionsStore.currentSessionId
    await sessionsStore.deleteSession(id)
    if (wasCurrent) {
      if (sessionsStore.sessions.length > 0) {
        emit('switchSession', sessionsStore.sessions[0].id)
      } else {
        emit('newChat')
      }
    }
  }
}
</script>

<style scoped>
.left-sidebar {
  width: 312px;
  --sidebar-agent-card-bg: color-mix(in srgb, var(--el-bg-color-overlay) 78%, var(--el-fill-color-light));
  --sidebar-agent-card-border: var(--el-border-color-lighter);
  --sidebar-agent-card-active-border: color-mix(in srgb, var(--el-color-primary) 62%, var(--el-border-color));
  --sidebar-agent-card-active-bg: color-mix(in srgb, var(--el-color-primary-light-9) 82%, var(--el-bg-color));
  --sidebar-agent-card-active-ring: color-mix(in srgb, var(--el-color-primary) 18%, transparent);
  --sidebar-agent-card-count-bg: var(--el-fill-color-light);
  --sidebar-agent-card-count-color: var(--el-text-color-secondary);
  --sidebar-session-hover-bg: color-mix(in srgb, var(--el-color-success) 16%, var(--el-bg-color-overlay));
  --sidebar-session-hover-color: var(--el-text-color-primary);
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

:global(html.dark) .left-sidebar {
  --sidebar-agent-card-bg: color-mix(in srgb, var(--el-bg-color-overlay) 82%, white 4%);
  --sidebar-agent-card-border: color-mix(in srgb, var(--el-border-color) 76%, white 8%);
  --sidebar-agent-card-active-border: color-mix(in srgb, var(--el-color-primary) 72%, white 8%);
  --sidebar-agent-card-active-bg: color-mix(in srgb, var(--el-color-primary) 14%, var(--el-bg-color-overlay));
  --sidebar-agent-card-active-ring: color-mix(in srgb, var(--el-color-primary) 24%, transparent);
  --sidebar-agent-card-count-bg: color-mix(in srgb, var(--el-fill-color) 84%, white 8%);
  --sidebar-agent-card-count-color: var(--el-text-color-regular);
  --sidebar-session-hover-bg: color-mix(in srgb, var(--el-color-success) 30%, #10261d);
  --sidebar-session-hover-color: #f8fafc;
}

.left-sidebar.collapsed {
  width: 68px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid var(--el-border-color);
}

.sidebar-brand {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.3px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.toggle-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.toggle-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-icon.flipped {
  transform: rotate(180deg);
}

.session-list {
  flex: 1;
  overflow: hidden;
}

.session-list :deep(.elx-conversations) {
  height: 100%;
  width: 100%;
  --elx-conversations-list-auto-bg-color: transparent !important;
}

.session-list :deep(.elx-conversations__list) {
  width: 100% !important;
  height: 100% !important;
  padding: 4px 4px !important;
  background: transparent !important;
  background-color: transparent !important;
  border-radius: 0 !important;
}

.session-list :deep(.elx-conversations__group) {
  margin: 8px 6px 10px;
  border: 1px solid var(--sidebar-agent-card-border);
  border-radius: 8px;
  background: var(--sidebar-agent-card-bg);
  overflow: hidden;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.session-list :deep(.elx-conversations__group:has(.agent-group-header.is-active-agent)) {
  border-color: var(--sidebar-agent-card-active-border);
  box-shadow: 0 0 0 1px var(--sidebar-agent-card-active-ring);
}

.session-list :deep(.elx-conversations__group-items) {
  padding: 2px 6px 7px;
}

.session-list :deep(.elx-conversations-item) {
  margin: 0;
  padding: 8px 9px;
  border-radius: 6px;
  color: var(--el-text-color-regular);
}

.session-list :deep(.elx-conversations-item__label) {
  max-width: 100% !important;
  color: var(--el-text-color-regular) !important;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-list :deep(.elx-conversations-item:hover) {
  background: var(--sidebar-session-hover-bg) !important;
  color: var(--sidebar-session-hover-color) !important;
}

.session-list :deep(.elx-conversations-item:hover .elx-conversations-item__label) {
  color: var(--sidebar-session-hover-color) !important;
}

.session-list :deep(.elx-conversations-item:hover .elx-conversations-item__menu) {
  color: var(--sidebar-session-hover-color) !important;
}

.session-list :deep(.elx-conversations-item--active) {
  background: var(--sidebar-agent-card-active-bg) !important;
}

.session-list :deep(.elx-conversations-item--active .elx-conversations-item__label) {
  color: var(--el-color-primary) !important;
  font-weight: 600;
}

.agent-card-shell {
  width: 100%;
}

.agent-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s, color 0.15s;
}

.agent-group-header:hover {
  background: var(--el-fill-color-lighter);
}

.agent-group-header.is-active-agent {
  background: var(--sidebar-agent-card-active-bg);
}

.agent-group-arrow {
  font-size: 9px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s ease;
  transform: rotate(90deg);
  flex-shrink: 0;
}

.agent-group-arrow.collapsed {
  transform: rotate(0deg);
}

.agent-group-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-card-count {
  font-size: 10px;
  font-weight: 600;
  color: var(--sidebar-agent-card-count-color);
  background: var(--sidebar-agent-card-count-bg);
  padding: 1px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}

/* Hide group items when collapsed */
.session-list :deep(.elx-conversations__group-items) {
  transition: max-height 0.25s ease, opacity 0.2s ease;
  overflow: hidden;
}

/* Reset EPX default group title styling (we use custom slot content) */
.session-list :deep(.elx-conversations__group-title) {
  all: unset !important;
  display: block !important;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .left-sidebar,
  .left-sidebar.collapsed {
    width: min(86vw, 340px);
    max-width: 86vw;
    height: 100%;
  }

  .sidebar-header {
    padding: 10px 12px;
  }

  .session-list {
    overflow-y: auto;
  }

  .session-list :deep(.elx-conversations__group) {
    margin: 7px 4px 9px;
  }

  .agent-group-header {
    padding: 9px 10px;
  }
}
</style>
