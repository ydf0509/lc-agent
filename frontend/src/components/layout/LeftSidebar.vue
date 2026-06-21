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
      <div class="sidebar-search">
        <input
          v-model="searchQuery"
          class="sidebar-search-input"
          type="text"
          placeholder="搜索聊天标题"
        >
      </div>

      <div v-if="renderedGroups.length > 0" class="session-tree">
        <section
          v-for="group in renderedGroups"
          :key="group.agentId"
          class="agent-section"
          :class="{ 'is-active-agent': group.agentName === activeAgentName }"
        >
          <button
            type="button"
            class="agent-section-header"
            @click="toggleGroup(group.agentName)"
          >
            <span class="agent-group-arrow" :class="{ collapsed: collapsedGroups.has(group.agentName) }">▶</span>
            <span class="agent-group-name">{{ group.agentName }}</span>
            <span class="agent-card-count">{{ group.badgeText }}</span>
          </button>

          <div v-if="!collapsedGroups.has(group.agentName)" class="session-children">
            <div
              v-for="session in group.visibleSessions"
              :key="session.id"
              class="session-item"
              :class="{ 'is-active': session.id === sessionsStore.currentSessionId }"
              @click="handleSessionSelect(session.id)"
            >
              <span class="session-rail" aria-hidden="true"></span>
              <span v-if="session.is_pinned" class="session-pin-indicator">📌</span>
              <span class="session-item-title">{{ session.title || '新对话' }}</span>
              <div class="session-item-meta">
                <button
                  type="button"
                  class="session-action-btn"
                  title="会话操作"
                  @click.stop="toggleSessionMenu(session.id)"
                >
                  ⋯
                </button>
                <div v-if="openMenuSessionId === session.id" class="session-menu">
                  <button type="button" @click.stop="handleRename(session.id, session.title || '新对话')">重命名</button>
                  <button type="button" @click.stop="handleTogglePinned(session)">
                    {{ session.is_pinned ? '取消置顶' : '置顶' }}
                  </button>
                  <button type="button" @click.stop="handleDelete(session.id)">删除</button>
                </div>
              </div>
            </div>

            <button
              v-if="group.hiddenCount > 0"
              type="button"
              class="show-more-btn"
              @click="showMore(group.agentId)"
            >
              <span>显示更多</span>
              <span class="show-more-hint">每次显示更多 20 条</span>
            </button>
          </div>
        </section>
      </div>

      <div v-else class="empty-state">
        <span>{{ normalizedQuery ? '没有匹配的聊天标题' : '暂无聊天' }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useSessionsStore, type Session } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps<{ collapsed: boolean }>()

const sessionsStore = useSessionsStore()
const agentsStore = useAgentsStore()
const emit = defineEmits<{ newChat: []; switchSession: [id: string]; toggleCollapse: [] }>()

const DEFAULT_VISIBLE_COUNT = 5
const LOAD_MORE_COUNT = 20
const SIDEBAR_COLLAPSED_GROUPS_KEY = 'lc-agent:sidebar:collapsed-agent-groups'

const searchQuery = ref('')
const openMenuSessionId = ref<string | null>(null)
const visibleCountByAgent = ref<Record<string, number>>({})

interface SidebarGroup {
  agentId: string
  agentName: string
  badgeText: string
  visibleSessions: Session[]
  hiddenCount: number
}

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

const activeAgentName = computed(() => {
  const session = sessionsStore.sessions.find(s => s.id === sessionsStore.currentSessionId)
  return agentsStore.getAgentName(session?.agent_id || '__chat__')
})

const normalizedQuery = computed(() => searchQuery.value.trim().toLowerCase())

const filteredSessions = computed(() => {
  const query = normalizedQuery.value
  if (!query) return sessionsStore.sessions.slice()
  return sessionsStore.sessions.filter(session =>
    (session.title || '新对话').toLowerCase().includes(query),
  )
})

function getVisibleCount(agentId: string) {
  return visibleCountByAgent.value[agentId] ?? DEFAULT_VISIBLE_COUNT
}

function compareSessions(a: Session, b: Session) {
  if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1

  const pinnedA = a.pinned_at ? new Date(a.pinned_at).getTime() : 0
  const pinnedB = b.pinned_at ? new Date(b.pinned_at).getTime() : 0
  if (pinnedA !== pinnedB) return pinnedB - pinnedA

  return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
}

const renderedGroups = computed<SidebarGroup[]>(() => {
  const buckets = new Map<string, Session[]>()

  for (const session of filteredSessions.value) {
    const agentId = session.agent_id || '__chat__'
    const list = buckets.get(agentId) || []
    list.push(session)
    buckets.set(agentId, list)
  }

  return [...buckets.entries()]
    .map(([agentId, sessions]) => {
      const agentName = agentsStore.getAgentName(agentId)
      const sorted = sessions.slice().sort(compareSessions)
      const visibleCount = getVisibleCount(agentId)
      const totalCount = sessionsStore.sessions.filter(s => (s.agent_id || '__chat__') === agentId).length
      return {
        agentId,
        agentName,
        badgeText: normalizedQuery.value ? `${sorted.length}/${totalCount}` : String(sorted.length),
        visibleSessions: sorted.slice(0, visibleCount),
        hiddenCount: Math.max(sorted.length - visibleCount, 0),
      }
    })
    .sort((a, b) => a.agentName.localeCompare(b.agentName, 'zh-CN'))
})

const allCollapsed = computed(() => {
  const groupNames = renderedGroups.value.map(group => group.agentName)
  return groupNames.length > 0 && groupNames.every(name => collapsedGroups.value.has(name))
})

watch(normalizedQuery, () => {
  visibleCountByAgent.value = {}
  openMenuSessionId.value = null
})

watch(renderedGroups, groups => {
  const groupNames = new Set(groups.map(group => group.agentName))
  const pruned = new Set([...collapsedGroups.value].filter(name => groupNames.has(name)))
  if (pruned.size !== collapsedGroups.value.size) {
    collapsedGroups.value = pruned
    persistCollapsedGroups()
  }
}, { immediate: true })

function toggleGroup(title: string) {
  const next = new Set(collapsedGroups.value)
  if (next.has(title)) {
    next.delete(title)
  } else {
    next.add(title)
  }
  collapsedGroups.value = next
  persistCollapsedGroups()
}

function toggleAllGroups() {
  const groupNames = renderedGroups.value.map(group => group.agentName)
  if (groupNames.length === 0) return

  if (allCollapsed.value) {
    collapsedGroups.value = new Set([...collapsedGroups.value].filter(name => !groupNames.includes(name)))
  } else {
    collapsedGroups.value = new Set([...collapsedGroups.value, ...groupNames])
  }
  persistCollapsedGroups()
}

function showMore(agentId: string) {
  visibleCountByAgent.value = {
    ...visibleCountByAgent.value,
    [agentId]: getVisibleCount(agentId) + LOAD_MORE_COUNT,
  }
}

function handleSessionSelect(id: string) {
  openMenuSessionId.value = null
  emit('switchSession', id)
}

function toggleSessionMenu(id: string) {
  openMenuSessionId.value = openMenuSessionId.value === id ? null : id
}

async function handleTogglePinned(session: Session) {
  await sessionsStore.setPinned(session.id, !session.is_pinned)
  openMenuSessionId.value = null
}

async function handleRename(id: string, currentTitle: string) {
  try {
    const { value } = await ElMessageBox.prompt('输入新标题', '重命名', {
      inputValue: currentTitle,
      inputValidator: (v) => !!v?.trim() || '标题不能为空',
    })
    if (value?.trim()) {
      await sessionsStore.updateTitle(id, value.trim())
    }
  } catch {
    // cancelled
  } finally {
    openMenuSessionId.value = null
  }
}

async function handleDelete(id: string) {
  const wasCurrent = id === sessionsStore.currentSessionId
  await sessionsStore.deleteSession(id)
  openMenuSessionId.value = null
  if (wasCurrent) {
    if (sessionsStore.sessions.length > 0) {
      emit('switchSession', sessionsStore.sessions[0].id)
    } else {
      emit('newChat')
    }
  }
}

function handleDocumentClick() {
  openMenuSessionId.value = null
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
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

.action-btn,
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

.action-btn:hover,
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
  overflow-y: auto;
  padding: 8px 8px 12px;
}

.sidebar-search {
  padding: 6px 4px 12px;
}

.sidebar-search-input {
  width: 100%;
  height: 34px;
  border-radius: 8px;
  border: 1px solid var(--el-border-color);
  background: var(--el-bg-color-overlay);
  color: var(--el-text-color-primary);
  padding: 0 12px;
  outline: none;
}

.sidebar-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 18%, transparent);
}

.session-tree {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-section {
  border: 1px solid var(--sidebar-agent-card-border);
  border-radius: 10px;
  background: var(--sidebar-agent-card-bg);
  overflow: visible;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, background 0.16s ease;
}

.agent-section.is-active-agent {
  border-color: var(--sidebar-agent-card-active-border);
  box-shadow: 0 0 0 1px var(--sidebar-agent-card-active-ring);
}

.agent-section-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-weight: 700;
  color: var(--el-text-color-primary);
  text-align: left;
}

.agent-section-header:hover {
  background: var(--el-fill-color-lighter);
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

.session-children {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 2px;
  padding-right: 8px;
  padding-bottom: 10px;
  padding-left: 22px;
}

.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--el-text-color-regular);
}

.session-item:hover {
  background: var(--sidebar-session-hover-bg);
  color: var(--sidebar-session-hover-color);
}

.session-item.is-active {
  background: var(--sidebar-agent-card-active-bg);
  color: var(--el-color-primary);
}

.session-rail {
  width: 8px;
  height: 1px;
  background: color-mix(in srgb, var(--el-border-color) 78%, transparent);
  flex-shrink: 0;
}

.session-pin-indicator {
  flex-shrink: 0;
  font-size: 12px;
}

.session-item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-item-meta {
  position: relative;
  flex-shrink: 0;
}

.session-action-btn {
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.session-action-btn:hover {
  background: color-mix(in srgb, var(--el-fill-color-light) 88%, transparent);
}

.session-menu {
  position: absolute;
  top: calc(100% - 4px);
  right: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  min-width: 112px;
  padding: 6px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color-overlay);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.22);
}

.session-menu button {
  border: none;
  background: transparent;
  color: var(--el-text-color-primary);
  text-align: left;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
}

.session-menu button:hover {
  background: var(--el-fill-color-light);
}

.show-more-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin-top: 2px;
  padding: 8px 8px 4px;
  border: none;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
}

.show-more-btn:hover {
  color: var(--el-text-color-primary);
}

.show-more-hint {
  font-size: 11px;
  opacity: 0.72;
}

.empty-state {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
  font-size: 13px;
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
    padding: 6px 6px 12px;
  }

  .session-tree {
    gap: 8px;
  }
}
</style>
