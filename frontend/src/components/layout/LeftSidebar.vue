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
          <div
            class="group-header"
            :data-group="group.title"
            :class="{ 'is-collapsed': collapsedGroups.has(group.title) }"
            @click.stop="toggleGroup(group.title)"
          >
            <span class="group-arrow" :class="{ collapsed: collapsedGroups.has(group.title) }">▶</span>
            <span class="group-name">{{ group.title }}</span>
            <span class="group-count">{{ group.children?.length || 0 }}</span>
          </div>
        </template>
      </Conversations>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect, nextTick, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Conversations } from 'vue-element-plus-x'
import type { ConversationItem, ConversationMenuCommand } from 'vue-element-plus-x/types/Conversations'
import { useSessionsStore } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'

defineProps<{ collapsed: boolean }>()

const sessionsStore = useSessionsStore()
const agentsStore = useAgentsStore()
const emit = defineEmits<{ newChat: []; switchSession: [id: string]; toggleCollapse: [] }>()

const collapsedGroups = ref<Set<string>>(new Set())

const allCollapsed = computed(() => {
  const groupNames = new Set(conversationItems.value.map(i => i.group).filter(Boolean))
  return groupNames.size > 0 && groupNames.size === collapsedGroups.value.size
})

function toggleGroup(title: string) {
  if (collapsedGroups.value.has(title)) {
    collapsedGroups.value.delete(title)
  } else {
    collapsedGroups.value.add(title)
  }
  nextTick(syncCollapsedDOM)
}

function syncCollapsedDOM() {
  const headers = document.querySelectorAll('.group-header[data-group]')
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
    collapsedGroups.value.clear()
  } else {
    const groupNames = new Set(conversationItems.value.map(i => i.group).filter(Boolean))
    collapsedGroups.value = groupNames as Set<string>
  }
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
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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

.session-list :deep(.elx-conversations-item) {
  margin: 0;
  padding: 8px 8px;
  border-radius: 6px;
  color: var(--el-text-color-regular);
}

.session-list :deep(.elx-conversations-item__label) {
  max-width: none !important;
  color: var(--el-text-color-regular) !important;
}

.session-list :deep(.elx-conversations-item--active) {
  background: var(--el-color-primary-light-9) !important;
}

.session-list :deep(.elx-conversations-item--active .elx-conversations-item__label) {
  color: var(--el-color-primary) !important;
  font-weight: 600;
}

/* Group header custom styling */
.group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 8px 4px 8px;
  margin-top: 4px;
  cursor: pointer;
  border-top: 1px solid var(--el-border-color-lighter);
  user-select: none;
  transition: background 0.15s;
  border-radius: 4px;
}

.group-header:hover {
  background: var(--el-fill-color-lighter);
}

.session-list :deep(.elx-conversations__group:first-child .group-header) {
  border-top: none;
  margin-top: 0;
}

.group-arrow {
  font-size: 9px;
  color: var(--el-text-color-secondary);
  transition: transform 0.2s ease;
  transform: rotate(90deg);
  flex-shrink: 0;
}

.group-arrow.collapsed {
  transform: rotate(0deg);
}

.group-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.3px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-count {
  font-size: 10px;
  color: var(--el-text-color-placeholder);
  background: var(--el-fill-color);
  padding: 1px 5px;
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
</style>
