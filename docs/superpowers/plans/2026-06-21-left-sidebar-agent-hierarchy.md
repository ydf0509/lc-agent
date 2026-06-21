# Left Sidebar Agent Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将左侧栏改为自定义的 agent -> chat title 两级列表，支持后端持久化置顶、全量标题搜索且保留 agent 分组、每组默认 5 条并按需每次追加 20 条。

**Architecture:** 后端继续复用现有 sessions REST 接口，只给 session 元数据增加 `is_pinned` 和 `pinned_at` 字段，并在更新接口中处理置顶/取消置顶。前端保留 `sessionsStore` 作为数据源，但 `LeftSidebar.vue` 不再依赖 `Conversations` 作为主列表，而是自行计算搜索、分组、排序和“显示更多”后的渲染结果。测试沿用当前项目风格：后端用 `pytest` 路由测试，前端用 source-contract 脚本 + `vue-tsc`/`vite build` 做回归。

**Tech Stack:** FastAPI, SQLModel, SQLAlchemy AsyncSession, Vue 3, TypeScript, Pinia, Element Plus, Vite

---

## File Structure

### Backend files
- Modify: `lc_agent/db/models.py`
  - 给 `SessionMeta` 增加 `is_pinned`、`pinned_at`
- Modify: `lc_agent/db/repository.py`
  - 在 `SessionRepository.update()` 内处理置顶时间戳
- Modify: `lc_agent/server/routes/sessions.py`
  - 扩展 session 序列化字段和更新请求体
- Modify: `tests/test_routes_sessions.py`
  - 增加默认未置顶、置顶、取消置顶的路由测试

### Frontend files
- Modify: `frontend/src/api/http.ts`
  - `updateSession()` 支持 `is_pinned`
- Modify: `frontend/src/stores/sessions.ts`
  - `Session` 类型补齐 pinned 字段，新增置顶更新方法
- Modify: `frontend/src/components/layout/LeftSidebar.vue`
  - 彻底改为自定义 sidebar 渲染：搜索框、agent 分组、二级标题、操作菜单、“显示更多”
- Modify: `frontend/scripts/check-sidebar-agent-cards.mjs`
  - 将旧的 `Conversations`/agent card 契约替换为新层级 sidebar 契约
- Create: `frontend/scripts/check-session-pinning-contract.mjs`
  - 校验前端 API/store 已接入 `is_pinned` / `pinned_at`
- Modify: `frontend/package.json`
  - 增加 `test:session-pinning` 脚本

---

### Task 1: Lock backend pinning behavior with failing tests

**Files:**
- Modify: `tests/test_routes_sessions.py`
- Test: `tests/test_routes_sessions.py`

- [ ] **Step 1: Write the failing backend route test for default pin fields**

Add this test near the existing session route tests:

```python
@pytest.mark.asyncio
async def test_list_sessions_includes_default_pin_fields(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Pinned Check"})
        session_id = create_resp.json()["id"]

        list_resp = await client.get("/api/sessions")

    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 1
    assert data[0]["id"] == session_id
    assert data[0]["is_pinned"] is False
    assert data[0]["pinned_at"] is None
```

- [ ] **Step 2: Write the failing backend route test for pin and unpin**

Add this second test in the same file:

```python
@pytest.mark.asyncio
async def test_update_session_pin_status(app):
    transport = ASGITransport(app=app.fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/sessions", json={"title": "Pin Me"})
        session_id = create_resp.json()["id"]

        pin_resp = await client.put(
            f"/api/sessions/{session_id}",
            json={"is_pinned": True},
        )
        assert pin_resp.status_code == 200
        assert pin_resp.json()["is_pinned"] is True
        assert pin_resp.json()["pinned_at"] is not None

        list_after_pin = await client.get("/api/sessions")
        pinned_item = list_after_pin.json()[0]
        assert pinned_item["is_pinned"] is True
        assert pinned_item["pinned_at"] is not None

        unpin_resp = await client.put(
            f"/api/sessions/{session_id}",
            json={"is_pinned": False},
        )
        assert unpin_resp.status_code == 200
        assert unpin_resp.json()["is_pinned"] is False
        assert unpin_resp.json()["pinned_at"] is None

        list_after_unpin = await client.get("/api/sessions")
        unpinned_item = list_after_unpin.json()[0]
        assert unpinned_item["is_pinned"] is False
        assert unpinned_item["pinned_at"] is None
```

- [ ] **Step 3: Run the backend tests to verify they fail**

Run:

```bash
"D:/ProgramData/Miniconda3/envs/py312/python.exe" -m pytest tests/test_routes_sessions.py -v
```

Expected:

```text
FAILED tests/test_routes_sessions.py::test_list_sessions_includes_default_pin_fields
FAILED tests/test_routes_sessions.py::test_update_session_pin_status
```

The likely failure is missing `is_pinned` / `pinned_at` fields in the JSON response or request model rejecting `is_pinned`.

- [ ] **Step 4: Commit the failing test baseline**

```bash
git add tests/test_routes_sessions.py
git commit -m "test: cover session pinning routes"
```

---

### Task 2: Implement backend session pinning fields and route behavior

**Files:**
- Modify: `lc_agent/db/models.py`
- Modify: `lc_agent/db/repository.py`
- Modify: `lc_agent/server/routes/sessions.py`
- Test: `tests/test_routes_sessions.py`

- [ ] **Step 1: Extend the session SQLModel with pin fields**

Update `SessionMeta` in `lc_agent/db/models.py` to:

```python
class SessionMeta(SQLModel, table=True):
    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = "新对话"
    agent_id: str = "__chat__"
    model: str = ""
    message_count: int = 0
    is_pinned: bool = False
    pinned_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 2: Teach the repository to maintain `pinned_at`**

Replace `SessionRepository.update()` in `lc_agent/db/repository.py` with:

```python
async def update(self, session_id: str, **kwargs) -> SessionMeta | None:
    sess = await self.get_by_id(session_id)
    if sess is None:
        return None

    if "is_pinned" in kwargs:
        is_pinned = bool(kwargs.pop("is_pinned"))
        sess.is_pinned = is_pinned
        sess.pinned_at = datetime.now(timezone.utc) if is_pinned else None

    for key, value in kwargs.items():
        if hasattr(sess, key):
            setattr(sess, key, value)

    sess.updated_at = datetime.now(timezone.utc)
    await self.session.commit()
    await self.session.refresh(sess)
    return sess
```

- [ ] **Step 3: Extend the sessions route request/response fields**

Update `lc_agent/server/routes/sessions.py` as follows.

First, extend the request model:

```python
class SessionUpdateRequest(BaseModel):
    title: str | None = None
    model: str | None = None
    is_pinned: bool | None = None
```

Then add a serializer helper near the top of the file:

```python
def serialize_session(s):
    return {
        "id": s.id,
        "title": s.title,
        "agent_id": s.agent_id,
        "model": s.model,
        "message_count": s.message_count,
        "is_pinned": s.is_pinned,
        "pinned_at": s.pinned_at.isoformat() if s.pinned_at else None,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }
```

Then use it in both handlers:

```python
@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    sessions = await repo.list_all()
    return [serialize_session(s) for s in sessions]


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, body: SessionUpdateRequest, db: AsyncSession = Depends(get_db_session)):
    repo = SessionRepository(db)
    update_data = body.model_dump(exclude_unset=True)
    result = await repo.update(session_id, **update_data)
    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return serialize_session(result)
```

- [ ] **Step 4: Run the backend tests to verify they pass**

Run:

```bash
"D:/ProgramData/Miniconda3/envs/py312/python.exe" -m pytest tests/test_routes_sessions.py -v
```

Expected:

```text
PASSED tests/test_routes_sessions.py::test_list_sessions_includes_default_pin_fields
PASSED tests/test_routes_sessions.py::test_update_session_pin_status
```

- [ ] **Step 5: Commit the backend implementation**

```bash
git add lc_agent/db/models.py lc_agent/db/repository.py lc_agent/server/routes/sessions.py tests/test_routes_sessions.py
git commit -m "feat: persist session pinning"
```

---

### Task 3: Lock frontend API/store pinning contracts with failing checks

**Files:**
- Create: `frontend/scripts/check-session-pinning-contract.mjs`
- Modify: `frontend/package.json`
- Test: `frontend/scripts/check-session-pinning-contract.mjs`

- [ ] **Step 1: Create the failing frontend pinning contract script**

Create `frontend/scripts/check-session-pinning-contract.mjs` with this content:

```javascript
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const apiFile = readFileSync(join(root, 'src/api/http.ts'), 'utf8')
const sessionsStore = readFileSync(join(root, 'src/stores/sessions.ts'), 'utf8')

const failures = []

function expectIncludes(label, text, expected) {
  if (!text.includes(expected)) {
    failures.push(`${label} 缺少: ${expected}`)
  }
}

expectIncludes('http.ts', apiFile, 'is_pinned?: boolean')
expectIncludes('sessions.ts', sessionsStore, 'is_pinned: boolean')
expectIncludes('sessions.ts', sessionsStore, 'pinned_at: string | null')
expectIncludes('sessions.ts', sessionsStore, 'async function setPinned(id: string, isPinned: boolean)')
expectIncludes('sessions.ts', sessionsStore, "await api.updateSession(id, { is_pinned: isPinned })")

if (failures.length > 0) {
  console.error('Session pinning 前端契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Session pinning 前端契约测试通过')
```

- [ ] **Step 2: Register the new script in `frontend/package.json`**

Add this script entry next to the existing `test:*` scripts:

```json
"test:session-pinning": "node scripts/check-session-pinning-contract.mjs"
```

- [ ] **Step 3: Run the frontend pinning contract to verify it fails**

Run:

```bash
cd frontend && npm run test:session-pinning
```

Expected:

```text
Session pinning 前端契约测试失败:
- http.ts 缺少: is_pinned?: boolean
- sessions.ts 缺少: is_pinned: boolean
- sessions.ts 缺少: pinned_at: string | null
```

- [ ] **Step 4: Commit the failing frontend contract baseline**

```bash
git add frontend/package.json frontend/scripts/check-session-pinning-contract.mjs
git commit -m "test: add session pinning frontend contract"
```

---

### Task 4: Replace the sidebar contract with hierarchy/search/load-more expectations

**Files:**
- Modify: `frontend/scripts/check-sidebar-agent-cards.mjs`
- Test: `frontend/scripts/check-sidebar-agent-cards.mjs`

- [ ] **Step 1: Replace the old contract checks with new custom-sidebar assertions**

Replace the current `frontend/scripts/check-sidebar-agent-cards.mjs` content with:

```javascript
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

expectIncludes('searchQuery')
expectIncludes('visibleCountByAgent')
expectIncludes('sidebar-search-input')
expectIncludes('agent-section')
expectIncludes('agent-section-header')
expectIncludes('session-children')
expectIncludes('session-item')
expectIncludes('show-more-btn')
expectIncludes('每次显示更多 20 条')
expectIncludes('setPinned(')
expectIncludes('is_pinned')
expectMatch(/const DEFAULT_VISIBLE_COUNT = 5/, '缺少每组默认显示 5 条的常量')
expectMatch(/const LOAD_MORE_COUNT = 20/, '缺少每次追加 20 条的常量')
expectMatch(/searchQuery\.value\.trim\(\)/, '搜索逻辑缺少 trim 处理')
expectMatch(/\.session-children[\s\S]*padding-left:/, '聊天标题缺少明显缩进')
expectMatch(/\.agent-section-header[\s\S]*font-weight:\s*700/, 'agent 标题缺少更明显层级字重')
expectMatch(/v-if="group\.hiddenCount > 0"/, '显示更多按钮缺少隐藏数量判断')

if (failures.length > 0) {
  console.error('Agent 层级侧栏契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('Agent 层级侧栏契约测试通过')
```

- [ ] **Step 2: Run the sidebar contract to verify it fails against the old component**

Run:

```bash
cd frontend && npm run test:sidebar
```

Expected:

```text
Agent 层级侧栏契约测试失败:
- LeftSidebar.vue 缺少: sidebar-search-input
- LeftSidebar.vue 缺少: visibleCountByAgent
- LeftSidebar.vue 缺少: show-more-btn
```

- [ ] **Step 3: Commit the updated failing sidebar contract**

```bash
git add frontend/scripts/check-sidebar-agent-cards.mjs
git commit -m "test: define sidebar hierarchy contract"
```

---

### Task 5: Implement frontend API/store pinning support

**Files:**
- Modify: `frontend/src/api/http.ts`
- Modify: `frontend/src/stores/sessions.ts`
- Test: `frontend/scripts/check-session-pinning-contract.mjs`

- [ ] **Step 1: Extend `updateSession()` API typing**

Update `frontend/src/api/http.ts` so `updateSession()` accepts pinning:

```ts
updateSession: (id: string, data: { title?: string; model?: string; is_pinned?: boolean }) =>
  fetchApi<any>(`/sessions/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
```

- [ ] **Step 2: Extend the `Session` interface and store method**

Update the top of `frontend/src/stores/sessions.ts` to:

```ts
export interface Session {
  id: string
  title: string
  agent_id: string
  model: string
  message_count: number
  is_pinned: boolean
  pinned_at: string | null
  created_at: string
  updated_at: string
}
```

Then add this store method near `updateTitle` / `updateModel`:

```ts
async function setPinned(id: string, isPinned: boolean) {
  if (!localSessionIds.value.has(id)) {
    const updated = await api.updateSession(id, { is_pinned: isPinned })
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx >= 0) {
      sessions.value[idx] = { ...sessions.value[idx], ...updated }
    }
    return
  }

  const sess = sessions.value.find(s => s.id === id)
  if (sess) {
    sess.is_pinned = isPinned
    sess.pinned_at = isPinned ? new Date().toISOString() : null
  }
}
```

Finally, export it from the returned object:

```ts
return {
  sessions,
  currentSessionId,
  currentSession,
  groupedByAgent,
  init,
  createSession,
  createLocalSession,
  ensureLocalSession,
  persistSession,
  isLocalSession,
  deleteSession,
  updateTitle,
  updateTitleLocal,
  updateModel,
  updateModelLocal,
  setPinned,
  selectSession,
}
```

- [ ] **Step 3: Ensure new local sessions have default pin fields**

Update both local session creation paths in `frontend/src/stores/sessions.ts` so created local sessions include:

```ts
is_pinned: false,
pinned_at: null,
```

Specifically, the object literal in `ensureLocalSession()` should become:

```ts
const session: Session = {
  id,
  title: '新对话',
  agent_id: agentId,
  model,
  message_count: 0,
  is_pinned: false,
  pinned_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
}
```

- [ ] **Step 4: Run the frontend pinning contract to verify it passes**

Run:

```bash
cd frontend && npm run test:session-pinning
```

Expected:

```text
Session pinning 前端契约测试通过
```

- [ ] **Step 5: Commit the frontend API/store implementation**

```bash
git add frontend/src/api/http.ts frontend/src/stores/sessions.ts frontend/package.json frontend/scripts/check-session-pinning-contract.mjs
git commit -m "feat: expose session pinning in frontend store"
```

---

### Task 6: Rebuild `LeftSidebar.vue` as a custom hierarchical sidebar

**Files:**
- Modify: `frontend/src/components/layout/LeftSidebar.vue`
- Test: `frontend/scripts/check-sidebar-agent-cards.mjs`
- Test: `frontend/scripts/check-session-pinning-contract.mjs`

- [ ] **Step 1: Replace `Conversations`-based template with custom hierarchy markup**

Replace the current session-list portion of the template with this structure:

```vue
<div v-if="!collapsed" class="session-list">
  <div class="sidebar-search">
    <input
      v-model="searchQuery"
      class="sidebar-search-input"
      type="text"
      placeholder="搜索聊天标题"
    >
  </div>

  <div class="session-tree">
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
          <span v-if="session.is_pinned" class="session-pin-indicator">📌</span>
          <span class="session-item-title">{{ session.title }}</span>
          <div class="session-item-meta">
            <button
              type="button"
              class="session-action-btn"
              @click.stop="toggleSessionMenu(session.id)"
            >
              ⋯
            </button>
            <div v-if="openMenuSessionId === session.id" class="session-menu">
              <button type="button" @click.stop="handleRename(session.id, session.title)">重命名</button>
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
          显示更多
          <span class="show-more-hint">每次显示更多 20 条</span>
        </button>
      </div>
    </section>
  </div>
</div>
```

- [ ] **Step 2: Replace the script setup with explicit search/group/sort/load-more state**

Update the `<script setup lang="ts">` block to include these new state primitives and computed helpers:

```ts
import { computed, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useSessionsStore, type Session } from '@/stores/sessions'
import { useAgentsStore } from '@/stores/agents'

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

const normalizedQuery = computed(() => searchQuery.value.trim().toLowerCase())

const filteredSessions = computed(() => {
  const query = normalizedQuery.value
  if (!query) return sessionsStore.sessions.slice()
  return sessionsStore.sessions.filter(session =>
    (session.title || '新对话').toLowerCase().includes(query),
  )
})

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
      return {
        agentId,
        agentName,
        badgeText: String(sorted.length),
        visibleSessions: sorted.slice(0, visibleCount),
        hiddenCount: Math.max(sorted.length - visibleCount, 0),
      }
    })
    .sort((a, b) => a.agentName.localeCompare(b.agentName, 'zh-CN'))
})

watch(normalizedQuery, () => {
  visibleCountByAgent.value = {}
})

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
```

Keep the existing collapsed-group persistence helpers, `activeAgentName` computed, and `emit('toggleCollapse')` flow. Remove the `Conversations` import and any `ConversationItem` types because the template no longer uses them.

- [ ] **Step 3: Rework rename/delete helpers to operate on raw session ids**

Replace the old `handleSessionChange()` / `handleMenuCommand()` pattern with these direct handlers:

```ts
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
```

- [ ] **Step 4: Rework styles for hierarchy, indentation, active state, and show-more**

In the `<style scoped>` block, add or replace the list styles with:

```css
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

.session-tree {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.agent-section {
  border: 1px solid var(--sidebar-agent-card-border);
  border-radius: 10px;
  background: var(--sidebar-agent-card-bg);
  overflow: hidden;
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
}

.session-children {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 2px 8px 10px 22px;
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
}

.session-item.is-active {
  background: var(--sidebar-agent-card-active-bg);
}

.session-item-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-menu {
  position: absolute;
  top: calc(100% - 4px);
  right: 8px;
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

.show-more-hint {
  font-size: 11px;
  opacity: 0.72;
}
```

Do not delete the existing CSS variables at the top of `.left-sidebar`; reuse them so the new sidebar still follows the current dark-theme palette.

- [ ] **Step 5: Run the two frontend contract checks and the type/build check**

Run:

```bash
cd frontend && npm run test:session-pinning && npm run test:sidebar && npm run build
```

Expected:

```text
Session pinning 前端契约测试通过
Agent 层级侧栏契约测试通过
vite v...
✓ built in ...
```

- [ ] **Step 6: Commit the sidebar rewrite**

```bash
git add frontend/src/components/layout/LeftSidebar.vue frontend/scripts/check-sidebar-agent-cards.mjs frontend/src/api/http.ts frontend/src/stores/sessions.ts frontend/package.json frontend/scripts/check-session-pinning-contract.mjs
git commit -m "feat: rebuild session sidebar hierarchy"
```

---

### Task 7: Final verification and developer notes

**Files:**
- No code changes required unless verification fails
- Test: `tests/test_routes_sessions.py`
- Test: `frontend/scripts/check-session-pinning-contract.mjs`
- Test: `frontend/scripts/check-sidebar-agent-cards.mjs`

- [ ] **Step 1: Run backend regression for sessions**

Run:

```bash
"D:/ProgramData/Miniconda3/envs/py312/python.exe" -m pytest tests/test_routes_sessions.py -v
```

Expected:

```text
all session route tests pass
```

- [ ] **Step 2: Run frontend contract/build regression**

Run:

```bash
cd frontend && npm run test:session-pinning && npm run test:sidebar && npm run build
```

Expected:

```text
all frontend checks pass and build succeeds
```

- [ ] **Step 3: Smoke-test the exact user scenarios manually**

Verify in the browser:

```text
1. 每个 agent 默认只显示 5 条聊天标题
2. 点击“显示更多”后同一 agent 额外增加 20 条
3. 搜索一个原本不在前 5 条里的标题，能搜出来且仍保留 agent 分组
4. 对一个标题置顶后，它仍在原 agent 下，但移动到组内最前面
5. 刷新页面后置顶状态仍保留，显示更多状态恢复默认
6. 折叠/展开 agent、重命名、删除、切换当前会话仍正常工作
```

- [ ] **Step 4: Commit any follow-up fixes from verification**

```bash
git add -A
git commit -m "fix: polish sidebar hierarchy verification issues"
```

---

## Self-Review

### Spec coverage
- agent -> chat title 明显层级：Task 4 + Task 6
- 每组默认 5 条，显示更多每次 +20：Task 4 + Task 6
- 搜索所有聊天标题且保留 agent 分组：Task 6
- 置顶保留在原 agent 下且排到最前：Task 2 + Task 5 + Task 6
- 置顶持久化到后端：Task 1 + Task 2
- 刷新后显示更多状态不持久化：Task 6 + Task 7 手工验证

### Placeholder scan
- 没有 `TODO` / `TBD`
- 每个代码步骤都给了具体代码片段
- 每个测试步骤都给了精确命令和预期

### Type consistency
- 后端统一使用 `is_pinned` / `pinned_at`
- 前端 `Session` 接口、API 请求体、sidebar 逻辑统一使用相同字段名
- `setPinned(id, isPinned)` 与 sidebar `handleTogglePinned(session)` 对应一致
