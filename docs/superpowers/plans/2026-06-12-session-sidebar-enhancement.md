# Session Sidebar Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance left sidebar with agent-grouped session display and right-click context menu for renaming/deleting sessions.

**Architecture:** Frontend-only changes. Sessions grouped by `agent_id`, with collapsible agent sections. Right-click context menu provides rename (inline editing) and delete. All backend APIs already exist (`PUT /api/sessions/{id}`, `DELETE /api/sessions/{id}`).

**Tech Stack:** Vue 3, Pinia, Element Plus (el-dropdown/el-input)

**Python Interpreter:** `D:\ProgramData\miniconda3\envs\py312\python.exe`

---

## File Structure

### Frontend (modify)
- `frontend/src/components/layout/LeftSidebar.vue` — grouped display, context menu, inline rename
- `frontend/src/stores/sessions.ts` — add `groupedByAgent` computed, delete confirmation
- `frontend/src/stores/agents.ts` — export agent name lookup helper

### Frontend (no changes needed)
- `frontend/src/api/http.ts` — `updateSession`, `deleteSession` already exist
- Backend — all APIs already in place

---

### Task 1: Sessions Store — Add Grouped Computed

**Files:**
- Modify: `frontend/src/stores/sessions.ts`
- Modify: `frontend/src/stores/agents.ts`

- [ ] **Step 1: Add `getAgentName` helper to agents store**

In `frontend/src/stores/agents.ts`, add a function that returns agent name by id:

```typescript
function getAgentName(agentId: string): string {
  if (agentId === '__default__') return '默认助手'
  const agent = agents.value.find(a => a.id === agentId)
  return agent?.name || agentId
}
```

Export it in the return statement.

- [ ] **Step 2: Add `groupedByAgent` computed to sessions store**

In `frontend/src/stores/sessions.ts`, add:

```typescript
import { useAgentsStore } from '@/stores/agents'

const groupedByAgent = computed(() => {
  const agentsStore = useAgentsStore()
  const groups: Record<string, { agentName: string; sessions: Session[] }> = {}
  for (const s of sessions.value) {
    const key = s.agent_id || '__default__'
    if (!groups[key]) {
      groups[key] = { agentName: agentsStore.getAgentName(key), sessions: [] }
    }
    groups[key].sessions.push(s)
  }
  return Object.entries(groups).map(([agentId, data]) => ({
    agentId,
    agentName: data.agentName,
    sessions: data.sessions,
  }))
})
```

Export `groupedByAgent` in the return statement.

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd D:\codes\lc-agent\frontend && npx vue-tsc --noEmit`
Expected: No errors

---

### Task 2: LeftSidebar — Grouped Display

**Files:**
- Modify: `frontend/src/components/layout/LeftSidebar.vue`

- [ ] **Step 1: Replace flat list with grouped template**

Replace the session-list section in the template:

```vue
<div class="session-list">
  <template v-if="sessionsStore.groupedByAgent.length > 1">
    <div v-for="group in sessionsStore.groupedByAgent" :key="group.agentId" class="session-group">
      <div class="group-header">
        <span class="group-name">{{ group.agentName }}</span>
        <span class="group-count">{{ group.sessions.length }}</span>
      </div>
      <div
        v-for="session in group.sessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === sessionsStore.currentSessionId }"
        @click="$emit('switchSession', session.id)"
        @contextmenu.prevent="openMenu($event, session)"
      >
        <span class="session-title">{{ session.title }}</span>
        <span class="session-time">{{ formatTime(session.updated_at) }}</span>
      </div>
    </div>
  </template>
  <template v-else>
    <div
      v-for="session in sessionsStore.sessions"
      :key="session.id"
      class="session-item"
      :class="{ active: session.id === sessionsStore.currentSessionId }"
      @click="$emit('switchSession', session.id)"
      @contextmenu.prevent="openMenu($event, session)"
    >
      <span class="session-title">{{ session.title }}</span>
      <span class="session-time">{{ formatTime(session.updated_at) }}</span>
    </div>
  </template>
  <p v-if="!sessionsStore.sessions.length" class="empty-hint">暂无会话</p>
</div>
```

- [ ] **Step 2: Add group styles**

```css
.session-group {
  margin-bottom: 8px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px;
  font-size: 11px;
  color: var(--lc-text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.group-count {
  background: var(--lc-bg-tertiary);
  border-radius: 8px;
  padding: 0 6px;
  font-size: 10px;
}
```

- [ ] **Step 3: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 3: Right-Click Context Menu (Rename + Delete)

**Files:**
- Modify: `frontend/src/components/layout/LeftSidebar.vue`

- [ ] **Step 1: Add context menu state and methods to script**

```typescript
import { ref, nextTick } from 'vue'
import type { Session } from '@/stores/sessions'

const menuVisible = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const menuTarget = ref<Session | null>(null)
const renaming = ref<string | null>(null)
const renameInput = ref('')

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
    const input = document.querySelector('.rename-input input') as HTMLInputElement
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
  closeMenu()
  await sessionsStore.deleteSession(id)
  emit('newChat')
}
```

Also update emit definition:
```typescript
const emit = defineEmits<{ newChat: []; switchSession: [id: string] }>()
```

- [ ] **Step 2: Add context menu and inline rename to template**

After the session-list div, add the context menu:

```vue
<!-- Context menu -->
<teleport to="body">
  <div
    v-if="menuVisible"
    class="context-menu"
    :style="{ left: menuPosition.x + 'px', top: menuPosition.y + 'px' }"
  >
    <div class="menu-item" @click="startRename">✏️ 重命名</div>
    <div class="menu-item menu-item-danger" @click="deleteTarget">🗑️ 删除</div>
  </div>
  <div v-if="menuVisible" class="menu-backdrop" @click="closeMenu" />
</teleport>
```

Replace the session-title span to support inline rename:

```vue
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
</template>
```

- [ ] **Step 3: Add context menu and rename styles**

```css
.context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--lc-bg-primary);
  border: 1px solid var(--lc-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 4px;
  min-width: 120px;
}

.menu-item {
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--lc-text-primary);
}

.menu-item:hover {
  background: var(--lc-bg-tertiary);
}

.menu-item-danger {
  color: #e74c3c;
}

.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 9998;
}

.rename-input {
  width: 100%;
  padding: 2px 4px;
  font-size: 13px;
  border: 1px solid var(--lc-accent);
  border-radius: 4px;
  background: var(--lc-bg-primary);
  color: var(--lc-text-primary);
  outline: none;
}
```

- [ ] **Step 4: Build and verify**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 4: Restart and Verify

- [ ] **Step 1: Rebuild frontend**

Run: `cd D:\codes\lc-agent\frontend && npm run build`

- [ ] **Step 2: Restart bfzs server**

```powershell
$pids = (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique | Where-Object { $_ -ne 0 }
if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
Start-Sleep 2
D:\ProgramData\miniconda3\envs\py312\python.exe -m bfzs.main --port 8001
```

Working directory: `D:\codes\lc-agent-bfzs`

- [ ] **Step 3: Verify in browser**

Expected behaviors:
1. Left sidebar shows sessions grouped by agent name (if sessions span multiple agents)
2. Right-click on a session shows context menu with "重命名" and "删除"
3. Clicking "重命名" turns title into editable input; Enter/blur saves
4. Clicking "删除" removes the session and switches to new chat
5. Single-agent sessions show flat list (no redundant group header)

---

## Summary

After completing all tasks:
- Sessions in left sidebar grouped by agent name (with count badge)
- Right-click context menu: rename + delete
- Inline rename with Enter to save, Escape to cancel
- Delete with immediate removal
- Graceful fallback to flat list when all sessions belong to one agent
