<template>
  <aside class="left-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <transition name="fade">
        <span v-if="!collapsed" class="sidebar-brand">Chats</span>
      </transition>
      <button class="toggle-btn" @click="emit('toggleCollapse')" :title="collapsed ? '展开侧边栏' : '收起侧边栏'">
        <span class="toggle-icon" :class="{ flipped: collapsed }">«</span>
      </button>
    </div>

    <div v-if="!collapsed" class="session-scroll">
      <div v-for="group in sessionsStore.groupedByAgent" :key="group.agentId" class="agent-group">
        <div class="agent-group-header" @click="toggleGroup(group.agentId)">
          <span class="chevron" :class="{ expanded: !collapsedGroups[group.agentId] }">›</span>
          <span class="agent-dot" :class="`dot-${group.agentSource}`" />
          <span class="agent-name">{{ group.agentName }}</span>
          <span class="source-tag" :class="`tag-${group.agentSource}`">
            {{ group.agentSource === 'builtin' ? '内置' : group.agentSource === 'code' ? '代码' : '自建' }}
          </span>
          <span class="session-count">{{ group.sessions.length }}</span>
        </div>
        <transition name="slide">
          <div v-show="!collapsedGroups[group.agentId]" class="agent-group-body">
            <div
              v-for="session in group.sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: session.id === sessionsStore.currentSessionId }"
              @click="emit('switchSession', session.id)"
              @contextmenu.prevent="openMenu($event, session)"
            >
              <template v-if="renaming === session.id">
                <input
                  class="rename-input"
                  v-model="renameInput"
                  @keyup.enter="confirmRename(session.id)"
                  @keyup.escape="cancelRename"
                  @blur="confirmRename(session.id)"
                />
              </template>
              <template v-else>
                <span class="session-title">{{ session.title }}</span>
                <span class="session-time">{{ formatTime(session.updated_at) }}</span>
              </template>
            </div>
          </div>
        </transition>
      </div>

      <div v-if="!sessionsStore.sessions.length" class="empty-state">
        <span class="empty-icon">💬</span>
        <span class="empty-text">暂无会话</span>
      </div>
    </div>

    <teleport to="body">
      <div v-if="menuVisible" class="menu-backdrop" @click="closeMenu" />
      <div
        v-if="menuVisible"
        class="context-menu"
        :style="{ left: menuPosition.x + 'px', top: menuPosition.y + 'px' }"
      >
        <div class="menu-item" @click="startRename">
          <span class="menu-icon">✏️</span> 重命名
        </div>
        <div class="menu-divider" />
        <div class="menu-item menu-item-danger" @click="deleteTarget">
          <span class="menu-icon">🗑️</span> 删除
        </div>
      </div>
    </teleport>
  </aside>
</template>

<script setup lang="ts">
import { ref, reactive, nextTick } from 'vue'
import { useSessionsStore, type Session } from '@/stores/sessions'

defineProps<{ collapsed: boolean }>()

const sessionsStore = useSessionsStore()
const emit = defineEmits<{ newChat: []; switchSession: [id: string]; toggleCollapse: [] }>()

const collapsedGroups = reactive<Record<string, boolean>>({})
const menuVisible = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const menuTarget = ref<Session | null>(null)
const renaming = ref<string | null>(null)
const renameInput = ref('')

function toggleGroup(agentId: string) {
  collapsedGroups[agentId] = !collapsedGroups[agentId]
}

function openMenu(event: MouseEvent, session: Session) {
  menuTarget.value = session
  menuPosition.value = { x: event.clientX, y: event.clientY }
  menuVisible.value = true
}

function closeMenu() {
  menuVisible.value = false
  menuTarget.value = null
}

function startRename() {
  if (!menuTarget.value) return
  renaming.value = menuTarget.value.id
  renameInput.value = menuTarget.value.title
  closeMenu()
  nextTick(() => {
    const input = document.querySelector('.rename-input') as HTMLInputElement
    input?.focus()
    input?.select()
  })
}

async function confirmRename(sessionId: string) {
  if (renameInput.value.trim()) {
    await sessionsStore.updateTitle(sessionId, renameInput.value.trim())
  }
  renaming.value = null
}

function cancelRename() {
  renaming.value = null
}

async function deleteTarget() {
  if (!menuTarget.value) return
  const id = menuTarget.value.id
  const wasCurrent = id === sessionsStore.currentSessionId
  closeMenu()
  await sessionsStore.deleteSession(id)
  if (wasCurrent) {
    if (sessionsStore.sessions.length > 0) {
      emit('switchSession', sessionsStore.sessions[0].id)
    } else {
      emit('newChat')
    }
  }
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}天前`
  return new Date(iso).toLocaleDateString()
}
</script>

<style scoped>
.left-sidebar {
  width: 270px;
  background: #0d1117;
  border-right: 1px solid #21262d;
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.left-sidebar.collapsed {
  width: 56px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  flex-shrink: 0;
  border-bottom: 1px solid #21262d;
}

.sidebar-brand {
  font-size: 14px;
  font-weight: 700;
  color: #c9d1d9;
  letter-spacing: 0.3px;
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
  color: #8b949e;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.toggle-btn:hover {
  background: #21262d;
  color: #c9d1d9;
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-icon.flipped {
  transform: rotate(180deg);
}


.session-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.session-scroll::-webkit-scrollbar {
  width: 4px;
}
.session-scroll::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 4px;
}

.agent-group {
  margin-bottom: 0;
}

.agent-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 14px;
  margin: 0 8px 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
  background: linear-gradient(135deg, #1a3052 0%, #162544 100%);
  border: 1px solid #234876;
  border-radius: 8px;
  position: sticky;
  top: 4px;
  z-index: 1;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  margin-top: 8px;
}

.agent-group-header:hover {
  background: linear-gradient(135deg, #1f3a62 0%, #1a2d50 100%);
  border-color: #2d5a9e;
}

.chevron {
  font-size: 11px;
  color: #8b949e;
  transition: transform 0.2s ease;
  width: 12px;
  text-align: center;
}

.chevron.expanded {
  transform: rotate(90deg);
}

.agent-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-builtin {
  background: #58a6ff;
}

.dot-code {
  background: #d29922;
}

.dot-user {
  background: #3fb950;
}

.source-tag {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
  flex-shrink: 0;
}

.tag-builtin {
  background: #1c3a5e;
  color: #58a6ff;
}

.tag-code {
  background: #3d2e00;
  color: #d29922;
}

.tag-user {
  background: #0f2d16;
  color: #3fb950;
}

.agent-name {
  font-size: 13px;
  font-weight: 700;
  color: #79b8ff;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-count {
  font-size: 10px;
  color: #8b949e;
  background: #21262d;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 500;
  min-width: 18px;
  text-align: center;
}

.agent-group-body {
  padding: 4px 8px;
  background: #0d1117;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 7px 12px;
  margin: 1px 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  color: #7d8590;
  transition: all 0.15s ease;
  position: relative;
  background: transparent;
}

.session-item:hover {
  background: #21262d;
  color: #c9d1d9;
}

.session-item.active {
  background: #161b22;
  color: #c9d1d9;
  border-left: 2px solid #58a6ff;
  padding-left: 10px;
}

.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
  line-height: 1.4;
}

.session-time {
  font-size: 10px;
  color: #484f58;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.session-item:hover .session-time {
  opacity: 1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 16px;
  color: #484f58;
}

.empty-icon {
  font-size: 24px;
}

.empty-text {
  font-size: 12px;
}

.rename-input {
  width: 100%;
  padding: 4px 8px;
  font-size: 13px;
  border: 1px solid #58a6ff;
  border-radius: 4px;
  background: #0d1117;
  color: #e6edf3;
  outline: none;
}

.rename-input:focus {
  box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.3);
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.slide-enter-from, .slide-leave-to {
  max-height: 0;
  opacity: 0;
}
.slide-enter-to, .slide-leave-from {
  max-height: 500px;
  opacity: 1;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>

<style>
.context-menu {
  position: fixed;
  z-index: 9999;
  background: #1c2128;
  border: 1px solid #30363d;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  padding: 4px;
  min-width: 140px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 12px;
  font-size: 13px;
  border-radius: 5px;
  cursor: pointer;
  color: #c9d1d9;
  transition: background 0.12s ease;
}

.menu-item:hover {
  background: #30363d;
}

.menu-item-danger {
  color: #f87171;
}

.menu-item-danger:hover {
  background: #3d1f1f;
}

.menu-icon {
  font-size: 14px;
}

.menu-divider {
  height: 1px;
  background: #30363d;
  margin: 3px 8px;
}

.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9998;
}
</style>
