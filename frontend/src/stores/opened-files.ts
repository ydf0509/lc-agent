import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { api } from '@/api/http'
import { useAgentsStore } from '@/stores/agents'
import { useProjectTreeStore } from '@/stores/project-tree'
import { useUiStore } from '@/stores/ui'

export interface OpenedFile {
  // 读取内容用的路径：文件树传项目内相对路径，聊天区文件链接传绝对路径
  path: string
  name: string
  // 绝对路径，供「复制行号」使用
  sourcePath: string
  language: string
  asMarkdown: boolean
  // 固定标签：关闭其他/关闭全部时保留，排序时置前
  pinned: boolean
}

// Markdown 标签的查看模式：预览（渲染后排版）或编辑（源码）
export type MarkdownViewMode = 'preview' | 'edit'

interface FileContent {
  code: string
  truncated: boolean
  loading: boolean
  error: string
  loaded: boolean
  // 二进制文件（.db 等）：不渲染内容，展示提示
  binary: boolean
  // 图片文件：渲染 imageDataUrl
  image: boolean
  imageDataUrl: string
  imageTooLarge: boolean
  // 文档文件（pdf/docx/xlsx/pptx）：渲染 documentDataUrl，只读
  document: boolean
  documentDataUrl: string
  // 文档格式：pdf/docx/xlsx/pptx，决定前端用哪个预览组件
  documentKind: string
  documentTooLarge: boolean
  // ---- 编辑支持 ----
  // 相对未保存修改
  dirty: boolean
  // 保存中锁：防止重复提交
  saving: boolean
  // 读取时的 mtime，保存时做乐观锁
  mtime: number
  // 原文件换行符与 BOM，写回时原样保留
  newline: 'lf' | 'crlf'
  hasBom: boolean
  // 后端判定是否允许编辑（UTF-8 无损且未截断）；不可编辑时给出原因
  editable: boolean
  readonlyReason: string
  // 保存失败的错误（与加载错误 error 分开，不互相覆盖）
  saveError: string
  // 最近一次保存/加载时的内容基线，与 code 比较判断脏状态
  savedCode: string
  // 磁盘上的内容已被外部改过（Agent 工具、脚本、VSCode、WPS 等）：编辑器里是旧内容，提示用户重新加载
  externalChanged: boolean
  // 触发 externalChanged 的那个磁盘版本 mtime：用来判断是否又变了，以及配合 dismissedMtime 去重
  externalMtime: number
  // 用户点过「保留我的内容」时已确认的磁盘 mtime：同一版本不再重复提示
  dismissedMtime: number
}

type FileStatInfo = {
  path: string
  exists: boolean
  size?: number
  mtime?: number
  error?: string
}

const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg', 'ico', 'avif']
// 只读文档预览：与后端 _DOCUMENT_MIME_TYPES 保持一致
const DOCUMENT_EXTENSIONS = ['pdf', 'docx', 'xlsx', 'pptx']

const EXT_LANG_MAP: Record<string, string> = {
  py: 'python', ts: 'typescript', tsx: 'typescript', js: 'javascript', jsx: 'javascript',
  vue: 'xml', yml: 'yaml', md: 'markdown', sh: 'bash', zsh: 'bash', ps1: 'powershell',
  rs: 'rust', rb: 'ruby', kt: 'kotlin', cs: 'csharp', h: 'c', hpp: 'cpp', cc: 'cpp',
}

function extOf(path: string): string {
  return path.split('.').pop()?.toLowerCase() || ''
}

function langOf(path: string): string {
  const ext = extOf(path)
  return EXT_LANG_MAP[ext] || ext || 'text'
}

function nameOf(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).pop() || path
}

function isImagePath(path: string): boolean {
  return IMAGE_EXTENSIONS.includes(extOf(path))
}

function isDocumentPath(path: string): boolean {
  return DOCUMENT_EXTENSIONS.includes(extOf(path))
}

// 项目根 + 相对路径 → 绝对路径（分隔符跟随项目根风格）
function toAbsolute(relative: string): string {
  const treeStore = useProjectTreeStore()
  if (/^[a-zA-Z]:[\\/]/.test(relative) || relative.startsWith('/')) return relative
  const root = treeStore.projectRoot || useAgentsStore().currentAgent?.project_root?.trim() || ''
  if (!root) return relative
  const sep = root.includes('\\') ? '\\' : '/'
  return `${root.replace(/[\\/]+$/, '')}${sep}${relative.replace(/\//g, sep)}`
}

// 文件标签按 agent 持久化到 localStorage，刷新后恢复；与会话标签同一套模式
const OPENED_FILES_KEY_PREFIX = 'lc-agent:opened-files:'

interface PersistedFilesState {
  files: OpenedFile[]
  activePath: string
}

function loadPersistedState(agentId: string): PersistedFilesState | null {
  try {
    const raw = localStorage.getItem(OPENED_FILES_KEY_PREFIX + agentId)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedFilesState
    if (!Array.isArray(parsed.files)) return null
    return parsed
  } catch {
    return null
  }
}

function savePersistedState(agentId: string, state: PersistedFilesState): void {
  try {
    localStorage.setItem(OPENED_FILES_KEY_PREFIX + agentId, JSON.stringify(state))
  } catch {
    /* ignore */
  }
}

export const useOpenedFilesStore = defineStore('openedFiles', () => {
  const agentsStore = useAgentsStore()
  const files = ref<OpenedFile[]>([])
  const activePath = ref('')
  const contents = ref<Record<string, FileContent>>({})
  // 待跳转的行号：内容加载完成后由 FileEditorPane 消费并清空
  const jumpLine = ref(0)
  // 已关闭标签栈，供「恢复已关闭的标签」使用（仅当前 agent 会话内有效）
  const closedStack = ref<OpenedFile[]>([])

  // Markdown 标签的查看模式：只记在内存，刷新后回到默认预览
  const mdModes = ref<Record<string, MarkdownViewMode>>({})

  const activeFile = computed(() => files.value.find(f => f.path === activePath.value) ?? null)
  const activeContent = computed(() => contents.value[activePath.value] ?? null)

  function contentOf(path: string): FileContent | null {
    return contents.value[path] ?? null
  }

  // 固定标签永远排在未固定标签之前，保持各自相对顺序
  function normalizeOrder(list: OpenedFile[]): OpenedFile[] {
    const pinned = list.filter(f => f.pinned)
    const rest = list.filter(f => !f.pinned)
    return [...pinned, ...rest]
  }

  /** markdown 标签当前是预览还是源码编辑；没记过一律预览 */
  function markdownModeOf(path: string): MarkdownViewMode {
    return mdModes.value[path] === 'edit' ? 'edit' : 'preview'
  }

  function setMarkdownMode(path: string, mode: MarkdownViewMode) {
    if (!path) return
    if (mode === 'edit') {
      mdModes.value = { ...mdModes.value, [path]: 'edit' }
      return
    }
    const next = { ...mdModes.value }
    delete next[path]
    mdModes.value = next
  }

  function emptyContent(overrides: Partial<FileContent> = {}): FileContent {
    return {
      code: '', truncated: false, loading: false, error: '', loaded: false,
      binary: false, image: false, imageDataUrl: '', imageTooLarge: false,
      document: false, documentDataUrl: '', documentKind: '', documentTooLarge: false,
      dirty: false, saving: false, mtime: 0, newline: 'lf', hasBom: false,
      editable: false, readonlyReason: '', saveError: '', savedCode: '',
      externalChanged: false, externalMtime: 0, dismissedMtime: 0,
      ...overrides,
    }
  }

  // 刷新后启动恢复：从 localStorage 读回当前 agent 的文件标签（在 agentsStore 完成初始化后由 App 触发）
  function restoreForCurrentAgent() {
    const agentId = agentsStore.currentAgentId
    if (!agentId || files.value.length > 0) return
    const persisted = loadPersistedState(agentId)
    if (persisted && persisted.files.length > 0) {
      // 兼容早期存档：pinned 字段可能缺失
      files.value = normalizeOrder(persisted.files.map(f => ({ ...f, pinned: !!f.pinned })))
      activePath.value = persisted.activePath
      const file = files.value.find(f => f.path === activePath.value)
      if (file) void loadContent(file)
    }
  }

  async function loadContent(file: OpenedFile) {
    const current = contents.value[file.path]
    if (current?.loading || current?.loaded) return
    contents.value[file.path] = emptyContent({ loading: true })
    const agentsStore = useAgentsStore()
    try {
      // 相对路径需要 agent_id 才能定位项目根；绝对路径后端直接读
      const isRelative = !isAbsolutePath(file.path)
      // 请求大行数，配合 CodeMirror 虚拟滚动可打开大文件
      const data = await api.readFile(file.path, 200000, isRelative ? agentsStore.currentAgentId : undefined)
      if (data.error) {
        contents.value[file.path] = emptyContent({ error: data.error, loaded: true })
        return
      }
      if (data.image) {
        contents.value[file.path] = emptyContent({
          loaded: true,
          image: true,
          imageDataUrl: data.data_url || '',
          imageTooLarge: !!data.image_too_large,
          mtime: data.mtime ?? 0,
        })
        return
      }
      if (data.binary) {
        contents.value[file.path] = emptyContent({ loaded: true, binary: true, mtime: data.mtime ?? 0 })
        return
      }
      if (data.document) {
        contents.value[file.path] = emptyContent({
          loaded: true,
          document: true,
          documentDataUrl: data.data_url || '',
          documentKind: data.document_kind || extOf(file.path),
          documentTooLarge: !!data.document_too_large,
          mtime: data.mtime ?? 0,
        })
        return
      }
      contents.value[file.path] = emptyContent({
        code: (data.lines || []).join('\n'),
        truncated: !!data.truncated,
        loaded: true,
        mtime: data.mtime ?? 0,
        newline: data.newline === 'crlf' ? 'crlf' : 'lf',
        hasBom: !!data.has_bom,
        editable: !!data.editable,
        readonlyReason: data.readonly_reason || '',
        savedCode: (data.lines || []).join('\n'),
      })
    } catch (e: any) {
      contents.value[file.path] = emptyContent({ error: e.message || '读取文件失败', loaded: true })
    }
  }

  function open(path: string, options?: { name?: string; sourcePath?: string; line?: number }) {
    if (!path) return
    const existing = files.value.find(f => f.path === path)
    if (!existing) {
      files.value = normalizeOrder([...files.value, {
        path,
        name: options?.name || nameOf(path),
        sourcePath: options?.sourcePath || toAbsolute(path),
        language: langOf(path),
        asMarkdown: path.toLowerCase().endsWith('.md'),
        pinned: false,
      }])
    }
    activePath.value = path
    jumpLine.value = options?.line ?? 0
    const file = files.value.find(f => f.path === path)!
    void loadContent(file)
    useUiStore().requestTab('editor')
  }

  function activate(path: string) {
    if (!files.value.some(f => f.path === path)) return
    activePath.value = path
    jumpLine.value = 0
    const file = files.value.find(f => f.path === path)!
    void loadContent(file)
  }

  /** 请求滚动到指定行；内容已加载时 FileEditorPane 会立刻消费 */
  function requestJumpToLine(line: number) {
    jumpLine.value = line
  }

  function consumeJumpLine() {
    jumpLine.value = 0
  }

  function close(path: string) {
    const idx = files.value.findIndex(f => f.path === path)
    if (idx === -1) return
    const closing = files.value[idx]
    if (!closing.pinned) {
      closedStack.value = [...closedStack.value, closing].slice(-20)
    }
    const next = [...files.value]
    next.splice(idx, 1)
    files.value = next
    delete contents.value[path]
    delete mdModes.value[path]
    if (activePath.value === path) {
      const fallback = next[idx] || next[idx - 1] || null
      activePath.value = fallback ? fallback.path : ''
      if (fallback) void loadContent(fallback)
    }
  }

  /** 关闭除指定标签外的全部（固定标签保留） */
  function closeOthers(keepPath: string) {
    const kept = files.value.filter(f => f.pinned || f.path === keepPath)
    const removed = files.value.filter(f => !f.pinned && f.path !== keepPath)
    if (removed.length === 0) return
    closedStack.value = [...closedStack.value, ...removed].slice(-20)
    files.value = normalizeOrder(kept)
    for (const f of removed) delete contents.value[f.path]
    if (!kept.some(f => f.path === activePath.value)) {
      activePath.value = kept.length > 0 ? kept[kept.length - 1].path : ''
    }
  }

  /** 关闭指定标签右侧的全部（固定标签保留） */
  function closeToRight(path: string) {
    const idx = files.value.findIndex(f => f.path === path)
    if (idx === -1) return
    const left = files.value.slice(0, idx + 1)
    const right = files.value.slice(idx + 1)
    const removed = right.filter(f => !f.pinned)
    const kept = normalizeOrder([...left, ...right.filter(f => f.pinned)])
    if (removed.length === 0) return
    closedStack.value = [...closedStack.value, ...removed].slice(-20)
    files.value = kept
    for (const f of removed) delete contents.value[f.path]
    if (!kept.some(f => f.path === activePath.value)) {
      activePath.value = path
    }
  }

  /** 固定/取消固定标签；固定后自动置前 */
  function togglePin(path: string) {
    const file = files.value.find(f => f.path === path)
    if (!file) return
    files.value = normalizeOrder(
      files.value.map(f => (f.path === path ? { ...f, pinned: !f.pinned } : f)),
    )
  }

  /** 恢复最近关闭的标签 */
  function reopenClosed() {
    const stack = [...closedStack.value]
    const last = stack.pop()
    if (!last) return
    closedStack.value = stack
    if (!files.value.some(f => f.path === last.path)) {
      files.value = normalizeOrder([...files.value, last])
    }
    activePath.value = last.path
    void loadContent(last)
    useUiStore().requestTab('editor')
  }

  function closeAll() {
    // 固定标签在「关闭全部」时保留
    const pinned = files.value.filter(f => f.pinned)
    const removed = files.value.filter(f => !f.pinned)
    closedStack.value = [...closedStack.value, ...removed].slice(-20)
    for (const f of removed) delete contents.value[f.path]
    files.value = pinned
    activePath.value = pinned.length > 0 ? pinned[0].path : ''
  }

  /** 重命名/删除后同步标签路径（含激活项、固定状态、内容缓存） */
  function renamePath(oldPath: string, newPath: string, newName: string) {
    const file = files.value.find(f => f.path === oldPath)
    if (!file) return
    files.value = files.value.map(f =>
      f.path === oldPath
        ? { ...f, path: newPath, name: newName, sourcePath: toAbsolute(newPath), language: langOf(newPath), asMarkdown: newPath.toLowerCase().endsWith('.md') }
        : f,
    )
    if (contents.value[oldPath]) {
      contents.value[newPath] = contents.value[oldPath]
      delete contents.value[oldPath]
    }
    if (activePath.value === oldPath) activePath.value = newPath
  }

  /** 删除文件/目录后关闭受影响的标签（目录下所有文件一并关闭） */
  function closeUnderPath(targetPath: string) {
    const prefix = targetPath.replace(/[\\/]+$/, '')
    const affected = files.value.filter(
      f => f.path === targetPath || f.path.startsWith(prefix + '/') || f.path.startsWith(prefix + '\\'),
    )
    for (const f of affected) close(f.path)
  }

  /** 文件树/重命名后局部失效：清掉该目录缓存并重新拉取 */
  function invalidateTree(path: string) {
    const treeStore = useProjectTreeStore()
    delete treeStore.children[path]
  }

  // 切换 agent 时：把旧 agent 的标签集存档，载入新 agent 的标签集；
  // 新 agent 没有存档则清空。各 agent 的文件标签互不串扰。
  function switchAgent(previousId: string, nextId: string) {
    if (previousId) {
      savePersistedState(previousId, { files: files.value, activePath: activePath.value })
    }
    files.value = []
    contents.value = {}
    activePath.value = ''
    closedStack.value = []
    const persisted = nextId ? loadPersistedState(nextId) : null
    if (persisted && persisted.files.length > 0) {
      files.value = normalizeOrder(persisted.files.map(f => ({ ...f, pinned: !!f.pinned })))
      activePath.value = persisted.activePath
      const file = files.value.find(f => f.path === activePath.value)
      if (file) void loadContent(file)
    }
  }

  watch(() => agentsStore.currentAgentId, (nextId, previousId) => {
    switchAgent(previousId ?? '', nextId)
  })

  // 标签集或激活项变化时持久化到当前 agent 名下
  watch([files, activePath], () => {
    if (agentsStore.currentAgentId) {
      savePersistedState(agentsStore.currentAgentId, { files: files.value, activePath: activePath.value })
    }
  }, { deep: true })

  function refresh(path: string) {
    const file = files.value.find(f => f.path === path)
    if (!file) return
    delete contents.value[path]
    void loadContent(file)
  }

  /** 编辑器内容变化时调用：与保存基线比较维护脏状态 */
  function markDirty(path: string, nextCode: string) {
    const c = contents.value[path]
    if (!c || !c.loaded) return
    c.code = nextCode
    c.dirty = nextCode !== c.savedCode
  }

  /** 归一化成可比较的绝对路径形态（统一分隔符、去盘符大小写差异） */
  function normalizePath(p: string): string {
    const unified = (p || '').replace(/\\/g, '/').replace(/\/+$/, '')
    return /^[a-zA-Z]:/.test(unified) ? unified.toLowerCase() : unified
  }

  /** 绝对路径（Windows 盘符或 POSIX 根）不传 agent_id，走后端系统工具白名单 */
  function isAbsolutePath(path: string): boolean {
    return /^[a-zA-Z]:[\\/]/.test(path) || path.startsWith('/')
  }

  /**
   * Agent 写盘后调用：把磁盘上已变的文件标记为「外部改动」。
   * 事件里的路径是绝对路径，标签里存的可能是项目相对路径，两种形态都比。
   * 置位前先查磁盘 mtime：标签内容如果已经是最新版本（写入后才打开/重载），不要误报。
   */
  async function markExternalChanged(absolutePath: string) {
    if (!absolutePath) return
    const target = normalizePath(absolutePath)
    const matched = files.value.filter((file) => {
      const candidates = [
        normalizePath(file.sourcePath),
        normalizePath(toAbsolute(file.path)),
        normalizePath(file.path),
      ]
      return candidates.includes(target)
    })
    if (matched.length === 0) return

    const mtimeByPath = new Map<string, number>()
    try {
      const infos = await fetchStats(matched.map(file => file.path))
      for (const info of infos) {
        if (info.exists && !info.error && (info.mtime ?? 0) > 0) {
          mtimeByPath.set(info.path, info.mtime as number)
        }
      }
    } catch {
      // 查询失败时退回保守策略：照常标记
    }

    for (const file of matched) {
      const c = contents.value[file.path]
      // 内容还没加载或已卸载，无从比较，等下次加载自然拿到新内容
      if (!c?.loaded) continue
      const diskMtime = mtimeByPath.get(file.path) ?? 0
      if (diskMtime > 0 && sameMtime(diskMtime, c.mtime)) continue
      c.externalChanged = true
      if (diskMtime > 0) c.externalMtime = diskMtime
    }
  }

  /** 用户选择保留本地编辑：清标记并把当前磁盘版本记为「已确认」，同一版本不再重复提示 */
  function dismissExternalChanged(path: string) {
    const c = contents.value[path]
    if (!c) return
    c.externalChanged = false
    // -1 表示事件埋点先于轮询触发、此刻还不知道磁盘版本，由下次轮询吸收
    c.dismissedMtime = c.externalMtime > 0 ? c.externalMtime : -1
  }

  // ---- 外部改动轮询 ----
  // 事件埋点只能覆盖 Agent 走写入工具的情况（脚本生成、VSCode/WPS 编辑都不发事件），
  // 轮询 mtime 与来源无关，因此叠加这层兜底。空转时指数退避，发现改动后回到高频。
  const POLL_MIN_MS = 1000
  const POLL_MAX_MS = 30000
  // mtime 容差：文件系统精度差异会造成无意义的判定
  const MTIME_EPSILON = 0.001

  let pollTimer: ReturnType<typeof setTimeout> | null = null
  let pollDelay = POLL_MIN_MS
  let polling = false
  // 上一轮参与轮询的文件集合：集合变化说明用户又打开了文件，应当立刻回到高频
  let lastTargetsKey = ''

  function sameMtime(a: number, b: number): boolean {
    return Math.abs(a - b) < MTIME_EPSILON
  }

  /** 只有真正展示了内容的文件才值得轮询：二进制占位、超限提示都没有可过期的旧内容 */
  function hasPollableContent(c: FileContent | undefined): boolean {
    if (!c || !c.loaded || c.error) return false
    if (c.binary || c.imageTooLarge || c.documentTooLarge) return false
    if (c.image) return !!c.imageDataUrl
    if (c.document) return !!c.documentDataUrl
    return true
  }

  /**
   * 按路径类型分组查询 stat：项目内相对路径带 agent_id，绝对路径不带。
   * 绝对路径可能跨项目，后端只有不传 agent_id 时才走系统工具白名单；
   * 否则会被项目根校验拒绝，误报成「文件已删除」。
   */
  async function fetchStats(paths: string[]): Promise<FileStatInfo[]> {
    if (paths.length === 0) return []
    const agentId = agentsStore.currentAgentId
    if (!agentId) return []
    const relative: string[] = []
    const absolute: string[] = []
    for (const path of paths) {
      if (isAbsolutePath(path)) absolute.push(path)
      else relative.push(path)
    }
    const requests: Array<Promise<{ files?: FileStatInfo[]; error?: string }>> = []
    if (relative.length > 0) requests.push(api.statFiles(agentId, relative))
    if (absolute.length > 0) requests.push(api.statFiles(undefined, absolute))
    const responses = await Promise.all(requests)
    const infos: FileStatInfo[] = []
    for (const res of responses) {
      if (res.error) continue
      infos.push(...(res.files ?? []))
    }
    return infos
  }

  function stopPolling() {
    polling = false
    if (pollTimer !== null) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
  }

  function schedulePoll() {
    if (!polling) return
    if (pollTimer !== null) clearTimeout(pollTimer)
    pollTimer = setTimeout(() => { void pollOnce() }, pollDelay)
  }

  async function pollOnce() {
    pollTimer = null
    if (!polling) return
    // 页面不可见时停摆，由 visibilitychange 唤醒，避免后台标签白白发请求
    if (document.hidden) return

    const agentId = agentsStore.currentAgentId
    if (!agentId) { schedulePoll(); return }

    // 一次轮询所有已打开且展示了内容的文件，而不是只查 active 那一个
    const targets = files.value.filter(f => {
      const c = contents.value[f.path]
      return hasPollableContent(c) && c!.mtime > 0
    })
    if (targets.length === 0) {
      // 没有可比对的目标：不消耗退避额度，等有内容后再开始计时
      lastTargetsKey = ''
      schedulePoll()
      return
    }

    // 文件集合变了（新开了标签）：立刻回到高频，别让新文件等满一个退避周期
    const targetsKey = targets.map(f => f.path).join('\n')
    if (targetsKey !== lastTargetsKey) {
      lastTargetsKey = targetsKey
      pollDelay = POLL_MIN_MS
    }

    let newlyFlagged = false
    try {
      const infos = await fetchStats(targets.map(f => f.path))
      for (const info of infos) {
        const c = contents.value[info.path]
        if (!c?.loaded) continue

        // 权限/解析失败（例如跨项目绝对路径）：无法判断文件是否变化，保持原状态。
        // 不能当成「文件被删除」，否则每轮轮询都会重新置位，点多少次重载都会复发。
        if (info.error) continue

        // 文件被删除或移走：磁盘上没有可比对的版本，内容必然已过期
        if (!info.exists) {
          if (!c.externalChanged) {
            c.externalChanged = true
            c.externalMtime = 0
            newlyFlagged = true
          }
          continue
        }

        const diskMtime = info.mtime ?? 0
        if (diskMtime <= 0) continue
        if (sameMtime(diskMtime, c.mtime)) continue
        // 用户刚点过「保留我的内容」但当时还不知道磁盘版本：把这一版吸收为已确认
        if (c.dismissedMtime === -1) { c.dismissedMtime = diskMtime; continue }
        if (c.dismissedMtime > 0 && sameMtime(diskMtime, c.dismissedMtime)) continue
        if (c.externalMtime > 0 && sameMtime(diskMtime, c.externalMtime)) continue

        if (!c.externalChanged) newlyFlagged = true
        c.externalChanged = true
        c.externalMtime = diskMtime
      }
      // 发现改动后回到高频，便于捕捉 Agent 的连续写入；否则逐步退避
      pollDelay = newlyFlagged ? POLL_MIN_MS : Math.min(pollDelay * 2, POLL_MAX_MS)
    } catch {
      // 网络或权限异常不打断轮询，按退避继续，避免错误下的请求风暴
      pollDelay = Math.min(pollDelay * 2, POLL_MAX_MS)
    }
    schedulePoll()
  }

  function startPolling() {
    if (polling) return
    polling = true
    pollDelay = POLL_MIN_MS
    schedulePoll()
  }

  function handleVisibilityChange() {
    if (document.hidden) {
      stopPolling()
      return
    }
    if (files.value.length === 0) return
    startPolling()
    // 回到前台立刻补查一次，而不是等下一个退避周期
    void pollOnce()
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)

  // 有打开的文件才轮询；标签全部关掉就停下
  watch([files, () => agentsStore.currentAgentId], () => {
    if (files.value.length > 0 && agentsStore.currentAgentId) startPolling()
    else stopPolling()
  }, { immediate: true })

  /** 保存当前文件；成功后更新 mtime 并清除脏标记 */
  async function save(path: string): Promise<{ ok?: boolean; error?: string; conflict?: boolean }> {
    const c = contents.value[path]
    if (!c || !c.loaded || !c.editable) return { error: '文件不可编辑' }
    if (c.saving) return {}
    c.saving = true
    c.saveError = ''
    const agentsStore = useAgentsStore()
    const agentId = agentsStore.currentAgentId
    try {
      if (!agentId) return { error: '无活跃 Agent' }
      const result = await api.saveFile(agentId, path, c.code, {
        mtime: c.mtime, newline: c.newline, hasBom: c.hasBom,
      })
      if (result.error) {
        c.saveError = result.error
        if (result.conflict) {
          // 冲突后刷新 mtime，用户重载后才能再保存
          c.mtime = result.mtime ?? c.mtime
        }
        return result
      }
      c.mtime = result.mtime ?? c.mtime
      c.dirty = false
      c.savedCode = c.code
      // 写入后编辑器内容就是磁盘内容，过期提示与已确认版本都失效
      c.externalChanged = false
      c.externalMtime = 0
      c.dismissedMtime = 0
      return { ok: true }
    } catch (e: any) {
      c.saveError = e.message || '保存失败'
      return { error: c.saveError }
    } finally {
      c.saving = false
    }
  }

  return {
    files,
    activePath,
    activeFile,
    activeContent,
    jumpLine,
    contentOf,
    isImagePath,
    isDocumentPath,
    markdownModeOf,
    setMarkdownMode,
    open,
    activate,
    close,
    closeOthers,
    closeToRight,
    closeAll,
    togglePin,
    reopenClosed,
    renamePath,
    closeUnderPath,
    invalidateTree,
    restoreForCurrentAgent,
    requestJumpToLine,
    consumeJumpLine,
    refresh,
    markDirty,
    markExternalChanged,
    dismissExternalChanged,
    save,
  }
})
