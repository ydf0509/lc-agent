# Agent Session Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the confirmed A-style left sidebar where each Agent reads as a lightweight card with a clear session list inside it.

**Architecture:** Keep `vue-element-plus-x` `Conversations` as the interaction layer, and use its group title slot plus scoped CSS to restyle Agent groups as cards. Persist collapsed Agent group names in `localStorage` from `LeftSidebar.vue`, and add a source-level contract test so future changes do not flatten the hierarchy again.

**Tech Stack:** Vue 3, Element Plus, Vue Element Plus X, Node.js source contract scripts, Vite build.

---

### Task 1: Add Sidebar Contract Test

**Files:**
- Create: `frontend/scripts/check-sidebar-agent-cards.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Write the failing test**

Create `frontend/scripts/check-sidebar-agent-cards.mjs`:

```js
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const leftSidebar = readFileSync(join(root, 'src/components/layout/LeftSidebar.vue'), 'utf8')

const failures = []

function expectIncludes(expected) {
  if (!leftSidebar.includes(expected)) {
    failures.push(`LeftSidebar.vue 缺少: ${expected}`)
  }
}

function expectMatch(pattern, message) {
  if (!pattern.test(leftSidebar)) {
    failures.push(`LeftSidebar.vue ${message}`)
  }
}

expectIncludes('SIDEBAR_COLLAPSED_GROUPS_KEY')
expectIncludes('lc-agent:sidebar:collapsed-agent-groups')
expectIncludes('loadCollapsedGroups')
expectIncludes('persistCollapsedGroups')
expectIncludes("class=\"agent-group-header\"")
expectIncludes("class=\"agent-card-shell\"")
expectIncludes("class=\"agent-card-count\"")
expectIncludes("'is-active-agent': group.title === activeAgentName")
expectMatch(/\.session-list\s+:deep\(\.elx-conversations__group\)[\s\S]*border:\s*1px solid var\(--sidebar-agent-card-border\)/, 'Agent 分组缺少卡片边框')
expectMatch(/\.session-list\s+:deep\(\.elx-conversations__group:has\(\.agent-group-header\.is-active-agent\)\)[\s\S]*border-color:\s*var\(--sidebar-agent-card-active-border\)/, '当前 Agent 卡片缺少高亮边框')
expectMatch(/\.left-sidebar[\s\S]*--sidebar-agent-card-bg:/, '缺少侧栏卡片主题变量')
expectMatch(/html\.dark[\s\S]*--sidebar-agent-card-bg:/, '缺少黑色主题侧栏卡片变量')
expectMatch(/@media\s*\(max-width:\s*900px\)[\s\S]*\.session-list\s+:deep\(\.elx-conversations__group\)[\s\S]*margin:/, '移动端 Agent 卡片没有收紧间距')
expectMatch(/\.session-list\s+:deep\(\.elx-conversations-item__label\)[\s\S]*text-overflow:\s*ellipsis/, '会话标题缺少省略策略')

if (failures.length > 0) {
  console.error('Agent 会话侧栏契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Agent 会话侧栏契约测试通过')
```

Add the npm script:

```json
"test:sidebar": "node scripts/check-sidebar-agent-cards.mjs"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run test:sidebar
```

Expected: FAIL, because `LeftSidebar.vue` does not yet define `SIDEBAR_COLLAPSED_GROUPS_KEY`, `agent-card-shell`, or active Agent card styling.

### Task 2: Implement Agent Card Sidebar

**Files:**
- Modify: `frontend/src/components/layout/LeftSidebar.vue`

- [ ] **Step 1: Implement collapsed group persistence**

Add a fixed key, loading, saving, and pruning:

```ts
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
```

After every toggle and `toggleAllGroups`, call `persistCollapsedGroups()`. In `watchEffect`, prune names that are no longer present in `conversationItems`.

- [ ] **Step 2: Implement active Agent name**

Add:

```ts
const activeAgentName = computed(() => {
  const session = sessionsStore.sessions.find(s => s.id === sessionsStore.currentSessionId)
  return agentsStore.getAgentName(session?.agent_id || '__chat__')
})
```

Use it in the group title class:

```vue
:class="{ 'is-collapsed': collapsedGroups.has(group.title), 'is-active-agent': group.title === activeAgentName }"
```

- [ ] **Step 3: Convert group title slot to Agent card header**

Replace the existing group title markup with:

```vue
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
```

Add `class="agent-card-shell"` in a wrapper if the slot needs a stable marker for the contract test.

- [ ] **Step 4: Restyle groups as lightweight cards**

Add theme variables to `.left-sidebar`, override `html.dark`, and style:

```css
.session-list :deep(.elx-conversations__group) {
  margin: 8px 6px 10px;
  border: 1px solid var(--sidebar-agent-card-border);
  border-radius: 8px;
  background: var(--sidebar-agent-card-bg);
  overflow: hidden;
}

.session-list :deep(.elx-conversations__group:has(.agent-group-header.is-active-agent)) {
  border-color: var(--sidebar-agent-card-active-border);
  box-shadow: 0 0 0 1px var(--sidebar-agent-card-active-ring);
}
```

Keep mobile spacing tighter under `@media (max-width: 900px)`.

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run test:sidebar
```

Expected: PASS with `Agent 会话侧栏契约测试通过`.

### Task 3: Regression Verification

**Files:**
- Read: `frontend/src/components/layout/LeftSidebar.vue`
- Read: `frontend/scripts/check-responsive-layout.mjs`

- [ ] **Step 1: Run related frontend contract tests**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run test:sidebar
npm run test:responsive
```

Expected: both scripts exit 0.

- [ ] **Step 2: Run frontend build**

Run:

```powershell
cd D:\codes\lc-agent\frontend
npm run build
```

Expected: `vue-tsc --noEmit` and `vite build` both exit 0.

- [ ] **Step 3: Inspect final diff**

Run:

```powershell
git diff -- frontend/src/components/layout/LeftSidebar.vue frontend/scripts/check-sidebar-agent-cards.mjs frontend/package.json docs/superpowers/specs/2026-06-18-agent-session-sidebar-design.md docs/superpowers/plans/2026-06-18-agent-session-sidebar.md
```

Expected: diff only contains the sidebar UI hierarchy, its contract test, npm script, and docs.
