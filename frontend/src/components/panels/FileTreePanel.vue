<template>
  <div class="file-tree-panel">
    <div class="panel-section tree-toolbar">
      <div class="tree-toolbar-row">
        <div class="tree-project" :title="store.projectRoot || '项目'">
          <el-icon class="tree-project-icon"><FolderOpened /></el-icon>
          <span class="tree-project-name">{{ rootLabel }}</span>
        </div>

        <span v-if="store.gitBranch" class="tree-branch" :title="`当前 git 分支：${store.gitBranch}`">
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path
              d="M5 3.5v6.2M5 12.5a2 2 0 1 0 0-.01M11 5.5a2 2 0 1 0 0-.01M11 5.5v1c0 1.4-1.1 2.5-2.5 2.5H5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.4"
              stroke-linecap="round"
            />
            <circle cx="5" cy="12.4" r="2" fill="none" stroke="currentColor" stroke-width="1.4" />
            <circle cx="11" cy="3.6" r="2" fill="none" stroke="currentColor" stroke-width="1.4" />
          </svg>
          <span class="tree-branch-name">{{ store.gitBranch }}</span>
        </span>

        <button class="tree-icon-btn" type="button" title="刷新目录" :disabled="loading" @click="reload">
          <svg viewBox="0 0 16 16" :class="{ spinning: loading }" aria-hidden="true">
            <path
              d="M13 8a5 5 0 1 1-1.5-3.6M13 2v3h-3"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </button>
      </div>

      <div class="tree-search">
        <el-icon class="tree-search-icon"><Search /></el-icon>
        <input
          v-model="keyword"
          class="tree-search-input"
          type="text"
          :placeholder="searchMode === 'content' ? '搜索项目内文件内容' : '搜索项目内文件或目录'"
          @keydown.esc="keyword = ''"
        />
        <button
          v-if="keyword"
          class="tree-search-clear"
          type="button"
          title="清空"
          @click="keyword = ''"
        >
          <svg viewBox="0 0 12 12" aria-hidden="true">
            <path
              d="M3.5 3.5l5 5m0-5l-5 5"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </button>
      </div>

      <!-- 搜索模式切换：文件名 / 内容（grep）。两枚胶囊都有彩色底，激活态用文件区统一的翠绿渐变 -->
      <div class="tree-search-modes" role="tablist" aria-label="搜索模式">
        <button
          type="button"
          role="tab"
          class="tree-mode-btn"
          :class="{ 'is-on': searchMode === 'name' }"
          :aria-selected="searchMode === 'name'"
          @click="switchMode('name')"
        >
          文件名
        </button>
        <button
          type="button"
          role="tab"
          class="tree-mode-btn"
          :class="{ 'is-on': searchMode === 'content' }"
          :aria-selected="searchMode === 'content'"
          @click="switchMode('content')"
        >
          内容
        </button>
      </div>
    </div>

    <div v-if="error" class="tree-error">{{ error }}</div>

    <template v-else-if="searching || keyword">
      <div class="tree-scroll">
        <div v-if="searching" class="tree-status">
          <el-icon class="is-loading"><Loading /></el-icon>
          搜索中
        </div>
        <div v-else-if="searchError" class="tree-error tree-error-inline">{{ searchError }}</div>

        <!-- 内容模式：按文件分组，组下列出匹配行 -->
        <template v-else-if="searchMode === 'content'">
          <template v-if="grepGroups.length > 0">
            <div class="tree-status tree-status-count">
              <span>{{ grepMatchCount }} 处匹配 · {{ grepGroups.length }} 个文件</span>
              <span v-if="searchTruncated" class="tree-truncated">已截断</span>
            </div>
            <div v-for="group in grepGroups" :key="group.path" class="grep-group">
              <div class="grep-file" :title="group.path">
                <FileTypeIcon :name="group.name" :compact="true" />
                <span class="grep-file-name">{{ group.name }}</span>
                <span class="grep-file-count">{{ group.items.length }}</span>
              </div>
              <div
                v-for="match in group.items"
                :key="`${match.path}:${match.line}`"
                class="grep-line"
                :class="{ 'is-active': activeFile === match.path }"
                role="button"
                tabindex="0"
                :title="match.text"
                @click="openMatch(match)"
                @keydown.enter="openMatch(match)"
                @keydown.space.prevent="openMatch(match)"
              >
                <span class="grep-ln">{{ match.line }}</span>
                <span class="grep-text">{{ match.text }}</span>
              </div>
            </div>
          </template>
          <div v-else class="tree-status">没有匹配「{{ keyword }}」的文件内容</div>
        </template>

        <template v-else-if="results.length > 0">
          <div class="tree-status tree-status-count">
            <span>{{ results.length }} 个匹配</span>
            <span v-if="searchTruncated" class="tree-truncated">已截断</span>
          </div>
          <div
            v-for="item in results"
            :key="item.path"
            class="result-item"
            :class="{ 'is-active': isActiveFile(item) }"
            role="button"
            tabindex="0"
            :title="item.path"
            @click="openResult(item)"
            @keydown.enter="openResult(item)"
            @keydown.space.prevent="openResult(item)"
          >
            <FileTypeIcon
              :name="item.type === 'dir' ? '' : item.name"
              :is-directory="item.type === 'dir'"
              :compact="true"
            />
            <span class="result-name">{{ item.name }}</span>
            <span class="result-path">{{ parentDir(item.path) }}</span>
          </div>
        </template>
        <div v-else class="tree-status">
          没有匹配「{{ keyword }}」的文件或目录
        </div>
      </div>
    </template>

    <template v-else>
      <div v-if="loading && rootEntries.length === 0" class="tree-status">
        <el-icon class="is-loading"><Loading /></el-icon>
        加载目录
      </div>

      <div v-else-if="rootEntries.length === 0 && !rootDraftVisible" class="tree-status">目录为空</div>

      <div v-else class="tree-scroll">
        <!-- 根目录下的新建草稿行：与树节点同构，就地输入 -->
        <div v-if="rootDraftVisible" class="tree-row tree-row--draft" :style="{ paddingLeft: '6px' }">
          <span class="tree-caret" />
          <FileTypeIcon
            :name="edit.type === 'dir' ? '' : 'txt'"
            :is-directory="edit.type === 'dir'"
            :compact="true"
          />
          <input
            ref="rootDraftInput"
            v-model="edit.value"
            class="tree-inline-input"
            type="text"
            spellcheck="false"
            :placeholder="edit.type === 'dir' ? '新建文件夹' : '新建文件'"
            @keydown="onEditKeydown"
            @blur="submitEdit"
            @click.stop
          />
        </div>
        <FileTreeNode
          v-for="entry in rootEntries"
          :key="entry.path"
          :entry="entry"
          :depth="0"
        />
      </div>
    </template>

    <!-- 右键菜单统一由面板渲染（teleport 到 body），递归节点只上报请求：
         若每个节点各自渲染菜单，会多出 N 个浮层与 N 套外部点击监听 -->
    <teleport to="body">
      <div
        v-if="menuVisible && menuEntry"
        ref="menuEl"
        class="tree-ctx-menu"
        :style="menuStyle"
        role="menu"
        @contextmenu.prevent
      >
        <button class="tree-ctx-item" role="menuitem" @click="menuCreate('file')">新建文件</button>
        <button class="tree-ctx-item" role="menuitem" @click="menuCreate('dir')">新建文件夹</button>
        <div class="tree-ctx-sep" />
        <button class="tree-ctx-item" role="menuitem" @click="menuRename">重命名</button>
        <button class="tree-ctx-item is-danger" role="menuitem" @click="menuDelete">删除</button>
        <div class="tree-ctx-sep" />
        <button class="tree-ctx-item" role="menuitem" @click="menuCopy(true)">复制路径</button>
        <button class="tree-ctx-item" role="menuitem" @click="menuCopy(false)">复制相对路径</button>
        <template v-if="menuEntry.type === 'file'">
          <div class="tree-ctx-sep" />
          <button class="tree-ctx-item" role="menuitem" @click="menuOpenInEditor">在文件区打开</button>
        </template>
      </div>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'
import { Document as _Document, Folder as _Folder, Loading, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'
import { useProjectTreeStore, type ProjectTreeEntry } from '@/stores/project-tree'
import { useOpenedFilesStore } from '@/stores/opened-files'
import FileTreeNode from '@/components/panels/FileTreeNode.vue'

type EntryKind = 'file' | 'dir'
type SearchMode = 'name' | 'content'

// 行内编辑状态：由面板统一持有并 provide 给递归节点，
// 保证同一时刻只有一个输入框（新建与重命名互斥），节点只负责渲染与取值
interface TreeEditState {
  mode: '' | 'create' | 'rename'
  /** 新建时为新条目所在目录；重命名时为被重命名条目的父目录 */
  parentPath: string
  /** 重命名时的原路径 */
  targetPath: string
  type: EntryKind
  value: string
}

interface GrepMatch {
  path: string
  name: string
  line: number
  text: string
}

const store = useProjectTreeStore()
const agentsStore = useAgentsStore()
const openedFilesStore = useOpenedFilesStore()

const error = ref('')

const rootEntries = computed(() => store.entriesOf(''))
const loading = computed(() => store.isLoading(''))

const rootLabel = computed(() => {
  const root = store.projectRoot
  if (!root) return '项目'
  return root.split(/[\\/]/).filter(Boolean).pop() || root
})

async function loadRoot() {
  const agentId = agentsStore.currentAgentId
  if (!agentId) return
  error.value = ''
  const result = await store.load(agentId, '')
  error.value = result.error || ''
}

function reload() {
  store.clear()
  keyword.value = ''
  void loadRoot()
}

// ---- 全项目搜索（文件名 / 内容）----
const keyword = ref('')
const searchMode = ref<SearchMode>('name')
const results = ref<ProjectTreeEntry[]>([])
const grepResults = ref<GrepMatch[]>([])
const searching = ref(false)
const searchError = ref('')
const searchTruncated = ref(false)
let searchToken = 0
let searchTimer: ReturnType<typeof setTimeout> | null = null

// grep 结果按文件分组：一个文件一个分组头，下面是它的匹配行
const grepGroups = computed(() => {
  const map = new Map<string, { path: string; name: string; items: GrepMatch[] }>()
  for (const match of grepResults.value) {
    let group = map.get(match.path)
    if (!group) {
      group = { path: match.path, name: match.name, items: [] }
      map.set(match.path, group)
    }
    group.items.push(match)
  }
  return Array.from(map.values())
})

const grepMatchCount = computed(() => grepResults.value.length)

function isActiveFile(item: ProjectTreeEntry): boolean {
  return item.type !== 'dir' && activeFile.value === item.path
}

function parentDir(path: string): string {
  const idx = path.lastIndexOf('/')
  return idx === -1 ? '' : path.slice(0, idx)
}

function clearSearchState() {
  searchToken += 1
  results.value = []
  grepResults.value = []
  searchError.value = ''
  searchTruncated.value = false
  searching.value = false
}

async function runSearch() {
  const agentId = agentsStore.currentAgentId
  const q = keyword.value.trim()
  if (!agentId || !q) {
    clearSearchState()
    return
  }

  const mode = searchMode.value
  const token = ++searchToken
  searching.value = true
  searchError.value = ''
  try {
    if (mode === 'content') {
      const data = await api.grepProjectFiles(agentId, q)
      if (token !== searchToken) return
      if (data.error) {
        searchError.value = data.error
        grepResults.value = []
        return
      }
      store.projectRoot = data.project_root || store.projectRoot
      grepResults.value = data.matches || []
      searchTruncated.value = !!data.truncated
    } else {
      const data = await api.searchProjectFiles(agentId, q)
      if (token !== searchToken) return
      if (data.error) {
        searchError.value = data.error
        results.value = []
        return
      }
      store.projectRoot = data.project_root || store.projectRoot
      if (data.git_branch !== undefined) store.gitBranch = data.git_branch ?? null
      results.value = data.results || []
      searchTruncated.value = !!data.truncated
    }
  } catch (e: any) {
    if (token !== searchToken) return
    searchError.value = e.message || '搜索失败'
    results.value = []
    grepResults.value = []
  } finally {
    if (token === searchToken) searching.value = false
  }
}

function scheduleSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!keyword.value.trim()) {
    clearSearchState()
    return
  }
  searching.value = true
  // grep 需要遍历全项目文件内容，比文件名搜索慢，防抖时间相应加长
  const delay = searchMode.value === 'content' ? 400 : 260
  searchTimer = setTimeout(() => { void runSearch() }, delay)
}

function switchMode(next: SearchMode) {
  if (searchMode.value === next) return
  searchMode.value = next
  // 两种模式的结果结构不同，切换时先清空再按新模式重搜
  results.value = []
  grepResults.value = []
  searchError.value = ''
  searchTruncated.value = false
  scheduleSearch()
}

watch(keyword, scheduleSearch)

async function openResult(item: ProjectTreeEntry) {
  if (item.type === 'dir') {
    // 点击搜索结果中的文件夹：退出搜索态，并走 reveal 定位链在树中逐级展开到该目录。
    // 不能只 store.load(item.path)：那只是把子项拉进缓存，isOpen 是每个节点的本地
    // 状态、全为 false，树视图仍停在原处，用户看不到任何变化。
    keyword.value = ''
    store.reveal(item.path)
    return
  }
  await openFile(item.path)
}

// 点击匹配行：打开文件并跳到该行（FileEditorPane 会消费 jumpLine）
function openMatch(match: GrepMatch) {
  openedFilesStore.open(match.path, { line: match.line })
}

watch(
  () => agentsStore.currentAgentId,
  (agentId) => {
    if (!agentId) return
    if (store.agentId !== agentId) {
      store.clear()
      keyword.value = ''
    }
    void loadRoot()
  },
  { immediate: true },
)

// 当前在文件查看区打开的文件路径，供列表/树节点高亮
const activeFile = computed(() => openedFilesStore.activePath)

provide('activeFile', activeFile)
// FileTreeNode 通过 inject('openFile') 打开文件标签
provide('openFile', (path: string) => { openFile(path) })

function openFile(path: string) {
  openedFilesStore.open(path)
}

// ---- 右键菜单（由面板统一渲染）----
const menuVisible = ref(false)
const menuX = ref(0)
const menuY = ref(0)
const menuEntry = ref<ProjectTreeEntry | null>(null)
const menuEl = ref<HTMLElement | null>(null)
const menuStyle = computed(() => ({ left: `${menuX.value}px`, top: `${menuY.value}px` }))

// 节点通过 inject('treeContextMenu') 上报右键事件
provide('treeContextMenu', (e: MouseEvent, entry: ProjectTreeEntry) => openMenu(e, entry))

function openMenu(e: MouseEvent, entry: ProjectTreeEntry) {
  cancelEdit()
  // 估算菜单尺寸用于贴边收拢，避免窄侧栏里溢出视口
  const MENU_W = 178
  const ITEM_H = 30
  const SEP_H = 7
  const separators = entry.type === 'file' ? 3 : 2
  const items = entry.type === 'file' ? 7 : 6
  const MENU_H = items * ITEM_H + separators * SEP_H + 8
  menuEntry.value = entry
  menuX.value = Math.max(8, Math.min(e.clientX, window.innerWidth - MENU_W - 8))
  menuY.value = Math.max(8, Math.min(e.clientY, window.innerHeight - MENU_H - 8))
  menuVisible.value = true
}

function closeMenu() {
  menuVisible.value = false
}

function onDocPointerDown(e: MouseEvent) {
  const menu = menuEl.value
  if (menu && e.target instanceof Node && menu.contains(e.target)) return
  closeMenu()
}

function onDocKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') closeMenu()
}

onMounted(() => {
  document.addEventListener('pointerdown', onDocPointerDown)
  document.addEventListener('keydown', onDocKeydown)
  window.addEventListener('resize', closeMenu)
  // 侧栏此前停在会话列表时本组件未挂载，消费 revealPath 的 watch 不会触发，定位请求被留在 store 里。
  // 挂载时补消费一次，这样「定位」直接切过来也能滚到目标文件
  if (store.revealPath) void handleReveal(store.revealPath)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocPointerDown)
  document.removeEventListener('keydown', onDocKeydown)
  window.removeEventListener('resize', closeMenu)
  if (searchTimer) clearTimeout(searchTimer)
})

// ---- 行内新建 / 重命名 ----
const edit = reactive<TreeEditState>({
  mode: '',
  parentPath: '',
  targetPath: '',
  type: 'file',
  value: '',
})

const rootDraftVisible = computed(() => edit.mode === 'create' && edit.parentPath === '')
const rootDraftInput = ref<HTMLInputElement | null>(null)

// 节点通过 inject 复用这些动作，输入框行为因此与面板保持一致
provide('treeEdit', edit)
provide('treeBeginCreate', (parentPath: string, type: EntryKind) => beginCreate(parentPath, type))
provide('treeBeginRename', (entry: ProjectTreeEntry) => beginRename(entry))
provide('treeSubmitEdit', () => { void submitEdit() })
provide('treeCancelEdit', () => cancelEdit())

function cancelEdit() {
  edit.mode = ''
  edit.value = ''
}

function beginCreate(parentPath: string, type: EntryKind) {
  cancelEdit()
  edit.mode = 'create'
  edit.parentPath = parentPath
  edit.targetPath = ''
  edit.type = type
  edit.value = ''
  // 根目录的草稿行由面板自己渲染，需要在这里聚焦；
  // 目录内的草稿行由对应 FileTreeNode 渲染并自动聚焦
  if (parentPath === '') void nextTick(() => rootDraftInput.value?.focus())
}

function beginRename(entry: ProjectTreeEntry) {
  cancelEdit()
  edit.mode = 'rename'
  edit.targetPath = entry.path
  edit.parentPath = parentDir(entry.path)
  edit.type = entry.type
  edit.value = entry.name
}

// Enter 确认 / Esc 取消；同时 stopPropagation 避免冒泡触发节点的展开/打开
function onEditKeydown(e: KeyboardEvent) {
  e.stopPropagation()
  if (e.key === 'Enter') {
    e.preventDefault()
    void submitEdit()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancelEdit()
  }
}

async function submitEdit() {
  const mode = edit.mode
  // 已提交或已取消：输入框卸载时的 blur 不再重复提交
  if (!mode) return
  const agentId = agentsStore.currentAgentId
  const name = edit.value.trim()
  const isCreate = mode === 'create'
  const parentPath = isCreate ? edit.parentPath : parentDir(edit.targetPath)
  const targetPath = edit.targetPath
  const type = edit.type
  cancelEdit()
  if (!agentId || !name) return

  try {
    if (isCreate) {
      const data = await api.createProjectEntry(agentId, parentPath, name, type)
      if (data.error) {
        ElMessage.error(data.error)
        return
      }
    } else {
      const data = await api.renameProjectEntry(agentId, targetPath, name)
      if (data.error) {
        ElMessage.error(data.error)
        return
      }
      const newName = data.name || name
      const newPath = parentPath ? `${parentPath}/${newName}` : newName
      if (type === 'dir') {
        // 目录改名：目录下所有已打开文件都要跟着换前缀，否则标签会指向不存在的路径
        const prefix = `${targetPath}/`
        for (const file of [...openedFilesStore.files]) {
          if (!file.path.startsWith(prefix)) continue
          const suffix = file.path.slice(prefix.length)
          openedFilesStore.renamePath(file.path, `${newPath}/${suffix}`, file.name)
        }
        // 旧路径的子树缓存随之作废
        openedFilesStore.invalidateTree(targetPath)
      } else {
        // 同步已打开标签的路径与激活项
        openedFilesStore.renamePath(targetPath, newPath, newName)
      }
    }
    await refreshDir(parentPath)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败，请重试')
  }
}

// 局部刷新：只重拉受影响目录，避免整树 reload 造成闪烁
async function refreshDir(dirPath: string) {
  const agentId = agentsStore.currentAgentId
  if (!agentId) return
  openedFilesStore.invalidateTree(dirPath)
  const result = await store.load(agentId, dirPath)
  if (result.error) ElMessage.error(result.error)
}

async function deleteEntry(entry: ProjectTreeEntry) {
  const isDir = entry.type === 'dir'
  try {
    await ElMessageBox.confirm(
      isDir
        ? `将永久删除文件夹「${entry.name}」及其中的全部内容，此操作不可恢复。`
        : `将永久删除文件「${entry.name}」，此操作不可恢复。`,
      isDir ? '删除文件夹' : '删除文件',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      },
    )
  } catch {
    return
  }

  const agentId = agentsStore.currentAgentId
  if (!agentId) return
  try {
    const data = await api.deleteProjectEntry(agentId, entry.path)
    if (data.error) {
      ElMessage.error(data.error)
      return
    }
    // 目录下所有已打开文件一并关闭
    openedFilesStore.closeUnderPath(entry.path)
    await refreshDir(parentDir(entry.path))
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败，请重试')
  }
}

// 绝对路径 = 项目根 + 相对路径，分隔符跟随项目根风格
function toAbsolute(relative: string): string {
  const root = store.projectRoot || agentsStore.currentAgent?.project_root?.trim() || ''
  if (!root) return relative
  const sep = root.includes('\\') ? '\\' : '/'
  return `${root.replace(/[\\/]+$/, '')}${sep}${relative.replace(/\\/g, '/').replace(/\//g, sep)}`
}

async function writeClipboard(text: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function menuCreate(type: EntryKind) {
  const entry = menuEntry.value
  closeMenu()
  if (!entry) return
  // 文件上右键时，新建项落在它所在的父目录：与 VS Code 一致，菜单不会因目标是文件而缺项
  beginCreate(entry.type === 'dir' ? entry.path : parentDir(entry.path), type)
}

function menuRename() {
  const entry = menuEntry.value
  closeMenu()
  if (entry) beginRename(entry)
}

function menuDelete() {
  const entry = menuEntry.value
  closeMenu()
  if (entry) void deleteEntry(entry)
}

function menuCopy(absolute: boolean) {
  const entry = menuEntry.value
  closeMenu()
  if (!entry) return
  void writeClipboard(absolute ? toAbsolute(entry.path) : entry.path)
}

function menuOpenInEditor() {
  const entry = menuEntry.value
  closeMenu()
  if (entry && entry.type === 'file') openFile(entry.path)
}

// ---- 在树中定位（消费 projectTree store 的 revealPath）----
// 节点侧直接用 store.revealPath 判断自己是否在定位链上（store 已在节点内使用，无需再 provide）。
// 另外 provide 一个自增 token：每个节点对同一次定位请求只处理一次，
// 这样折叠/展开导致节点重新挂载时不会重复滚动与闪烁
const revealToken = ref(0)
provide('revealToken', revealToken)

async function handleReveal(path: string) {
  if (!path) return
  const agentId = agentsStore.currentAgentId
  if (!agentId) return
  revealToken.value += 1
  // 定位时先退出搜索态，否则树被搜索结果列表替换，目标节点不可见
  if (keyword.value) keyword.value = ''
  await nextTick()

  if (!store.isLoaded('')) {
    const root = await store.load(agentId, '')
    if (root.error) {
      ElMessage.error(root.error)
      return
    }
  }
  // 逐级加载目标的所有父目录，保证每一级节点都有数据可渲染（节点侧再自行展开）
  const segments = path.split('/').filter(Boolean)
  let prefix = ''
  for (let i = 0; i < segments.length - 1; i += 1) {
    prefix = prefix ? `${prefix}/${segments[i]}` : segments[i]
    // 节点侧可能已并发发起同一目录的加载，此处跳过避免重复请求
    if (store.isLoaded(prefix) || store.isLoading(prefix)) continue
    const result = await store.load(agentId, prefix)
    if (result.error) {
      ElMessage.error(result.error)
      return
    }
  }
}

watch(() => store.revealPath, handleReveal)
</script>

<style scoped>
.file-tree-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tree-toolbar {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tree-toolbar-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.tree-project {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
  max-width: 50%;
  min-width: 0;
  color: var(--el-text-color-primary);
  font-size: 12.5px;
  font-weight: 700;
}

.tree-project-icon {
  flex-shrink: 0;
  color: #d9a441;
  font-size: 15px;
}

.tree-project-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 分支胶囊：内容自适应，不撑满整行 */
.tree-branch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 1;
  min-width: 0;
  max-width: 46%;
  padding: 2px 8px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 32%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-color-primary) 9%, transparent);
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.5;
}

.tree-branch svg {
  flex-shrink: 0;
  width: 11px;
  height: 11px;
}

.tree-branch-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  margin-left: auto;
  padding: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: transparent;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: all 0.16s ease;
}

.tree-icon-btn svg {
  width: 13px;
  height: 13px;
}

.tree-icon-btn:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--el-color-primary) 40%, transparent);
  background: color-mix(in srgb, var(--el-color-primary) 8%, transparent);
  color: var(--el-color-primary);
}

.tree-icon-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.tree-icon-btn .spinning {
  animation: spin 0.9s linear infinite;
}

.tree-search {
  position: relative;
  display: flex;
  align-items: center;
}

.tree-search-icon {
  position: absolute;
  left: 9px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  pointer-events: none;
}

.tree-search-input {
  width: 100%;
  height: 30px;
  padding: 0 28px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  outline: none;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-primary);
  font-size: 12px;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.tree-search-input::placeholder {
  color: var(--el-text-color-placeholder);
}

.tree-search-input:focus {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--el-color-primary) 13%, transparent);
}

.tree-search-clear {
  position: absolute;
  right: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--el-fill-color-dark);
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease;
}

.tree-search-clear svg {
  width: 10px;
  height: 10px;
}

.tree-search-clear:hover {
  background: var(--el-text-color-placeholder);
  color: var(--el-bg-color);
}

/* 搜索模式胶囊：容器 14px，按钮 999px 胶囊，激活态用文件区统一的翠绿渐变 */
.tree-search-modes {
  display: flex;
  gap: 4px;
  padding: 3px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 14px;
  background: color-mix(in srgb, var(--el-fill-color) 90%, var(--el-bg-color) 10%);
}

.tree-mode-btn {
  flex: 1;
  min-width: 0;
  height: 24px;
  padding: 0 8px;
  border: 1px solid rgba(5, 150, 105, 0.28);
  border-radius: 999px;
  background: rgba(5, 150, 105, 0.12);
  color: #059669;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.tree-mode-btn:hover:not(.is-on) {
  background: rgba(5, 150, 105, 0.2);
  transform: translateY(-1px);
}

.tree-mode-btn.is-on {
  border-color: rgba(5, 150, 105, 0.55);
  background: linear-gradient(135deg, #059669, #10b981);
  color: #fff;
  box-shadow: 0 2px 10px rgba(5, 150, 105, 0.32);
}

.tree-scroll {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 2px;
}

/* 新建草稿行：与树节点同构，提示当前正在此处创建 */
.tree-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding-right: 6px;
  border-radius: 6px;
}

.tree-row--draft {
  background: rgba(5, 150, 105, 0.08);
  cursor: default;
}

.tree-inline-input {
  flex: 1;
  min-width: 0;
  height: 22px;
  padding: 0 7px;
  border: 1px solid #059669;
  border-radius: 6px;
  outline: none;
  background: var(--el-fill-color-blank);
  color: var(--el-text-color-primary);
  font-family: inherit;
  font-size: 12px;
  box-shadow: 0 0 0 2px rgba(5, 150, 105, 0.14);
}

/* 搜索结果 */
.result-item {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 26px;
  padding: 2px 7px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.14s ease;
}

.result-item:hover {
  background: var(--el-fill-color-light);
}

/* 文件区选中高亮：翠绿，与文件标签激活色一致 */
.result-item.is-active {
  background: rgba(5, 150, 105, 0.13);
  box-shadow: inset 2px 0 0 #059669;
}

.result-name {
  flex-shrink: 0;
  max-width: 58%;
  overflow: hidden;
  color: var(--el-text-color-primary);
  font-size: 12.5px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--el-text-color-placeholder);
  font-size: 11px;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
  direction: rtl;
}

/* 内容搜索结果：按文件分组 */
.grep-group {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 2px 0 6px;
}

.grep-file {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 3px 6px;
  color: var(--el-text-color-primary);
  font-size: 12px;
  font-weight: 700;
}

.grep-file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grep-file-count {
  flex-shrink: 0;
  min-width: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: rgba(5, 150, 105, 0.14);
  color: #059669;
  font-size: 10px;
  line-height: 15px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.grep-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  padding: 2px 6px 2px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.14s ease;
}

.grep-line:hover {
  background: var(--el-fill-color-light);
}

.grep-line.is-active {
  background: rgba(5, 150, 105, 0.13);
  box-shadow: inset 2px 0 0 #059669;
}

.grep-ln {
  flex-shrink: 0;
  min-width: 20px;
  color: var(--el-text-color-placeholder);
  font-family: 'Cascadia Code', 'JetBrains Mono', Consolas, monospace;
  font-size: 11px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.grep-text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-family: 'Cascadia Code', 'JetBrains Mono', Consolas, monospace;
  font-size: 11.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-status {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 20px 12px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  text-align: center;
}

.tree-status-count {
  justify-content: flex-start;
  padding: 4px 6px 8px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
}

.tree-truncated {
  padding: 1px 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--el-color-warning) 16%, transparent);
  color: var(--el-color-warning);
  font-size: 10px;
}

.tree-error {
  padding: 14px 10px;
  color: var(--el-color-danger);
  font-size: 12px;
  word-break: break-all;
}

.tree-error-inline {
  padding: 14px 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .tree-icon-btn .spinning {
    animation: none;
  }
}
</style>

<style>
/* 右键菜单 teleport 到 body，用全局样式确保浮层样式一定生效（类名带 tree-ctx 前缀，不会外泄） */
.tree-ctx-menu {
  position: fixed;
  z-index: 10001;
  min-width: 168px;
  max-width: 200px;
  padding: 4px;
  border: 1px solid var(--el-border-color);
  border-radius: 10px;
  background: var(--el-bg-color-overlay);
  box-shadow: 0 8px 24px color-mix(in srgb, var(--el-bg-color-page) 55%, transparent);
}

.tree-ctx-item {
  display: block;
  width: 100%;
  padding: 7px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--el-text-color-regular);
  font-size: 12.5px;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.14s ease, color 0.14s ease;
}

.tree-ctx-item:hover {
  background: color-mix(in srgb, var(--el-color-primary) 12%, transparent);
  color: var(--el-color-primary);
}

.tree-ctx-item.is-danger {
  color: var(--el-color-danger);
}

.tree-ctx-item.is-danger:hover {
  background: color-mix(in srgb, var(--el-color-danger) 14%, transparent);
  color: var(--el-color-danger);
}

.tree-ctx-sep {
  height: 1px;
  margin: 3px 6px;
  background: var(--el-border-color-lighter);
}
</style>
