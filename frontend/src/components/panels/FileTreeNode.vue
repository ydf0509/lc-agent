<template>
  <div class="tree-node">
    <div
      ref="rowEl"
      class="tree-row"
      :class="{ 'is-dir': isDir, 'is-open': isDir && isOpen, 'is-active': isActive, 'is-revealed': isRevealed }"
      :style="{ paddingLeft: 6 + depth * 14 + 'px' }"
      role="button"
      tabindex="0"
      :title="entry.path"
      @click="handleClick"
      @keydown.enter="handleClick"
      @keydown.space.prevent="handleClick"
      @contextmenu.prevent="handleContextMenu"
    >
      <span class="tree-caret" :class="{ 'is-open': isOpen }">
        <svg v-if="isDir" viewBox="0 0 12 12" aria-hidden="true">
          <path
            d="M4.5 2.5 8 6l-3.5 3.5"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>

      <FileTypeIcon
        :name="isDir ? '' : entry.name"
        :is-directory="isDir"
        :compact="true"
      />

      <!-- 重命名：就地变成输入框，与 VS Code 一致，不弹窗 -->
      <input
        v-if="isRenaming"
        ref="editInput"
        v-model="editState.value"
        class="tree-inline-input"
        type="text"
        spellcheck="false"
        @keydown="onEditKeydown"
        @blur="submitEdit"
        @click.stop
      />
      <span v-else class="tree-name">{{ entry.name }}</span>

      <span v-if="isDir && dirCount !== null && !isRenaming" class="tree-count">{{ dirCount }}</span>
    </div>

    <template v-if="isDir && isOpen">
      <div v-if="loading" class="tree-hint" :style="{ paddingLeft: 6 + (depth + 1) * 14 + 18 + 'px' }">
        <el-icon class="is-loading"><Loading /></el-icon>
        加载中
      </div>
      <div
        v-else-if="loadError"
        class="tree-hint tree-hint-error"
        :style="{ paddingLeft: 6 + (depth + 1) * 14 + 18 + 'px' }"
      >
        {{ loadError }}
      </div>
      <template v-else>
        <!-- 新建草稿行：占在真实子节点之前，命名完成后才落盘（接口会校验重名） -->
        <div
          v-if="isDraftParent"
          class="tree-row tree-row--draft"
          :style="{ paddingLeft: 6 + (depth + 1) * 14 + 'px' }"
        >
          <span class="tree-caret" />
          <FileTypeIcon
            :name="editState.type === 'dir' ? '' : 'txt'"
            :is-directory="editState.type === 'dir'"
            :compact="true"
          />
          <input
            ref="draftInput"
            v-model="editState.value"
            class="tree-inline-input"
            type="text"
            spellcheck="false"
            :placeholder="editState.type === 'dir' ? '新建文件夹' : '新建文件'"
            @keydown="onEditKeydown"
            @blur="submitEdit"
            @click.stop
          />
        </div>
        <FileTreeNode
          v-for="child in children"
          :key="child.path"
          :entry="child"
          :depth="depth + 1"
        />
        <div
          v-if="children.length === 0 && !isDraftParent"
          class="tree-hint"
          :style="{ paddingLeft: 6 + (depth + 1) * 14 + 18 + 'px' }"
        >
          空目录
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onBeforeUnmount, ref, watch, type Ref } from 'vue'
import {
  Coin,
  Document,
  Folder,
  FolderOpened,
  Loading,
  Lock,
  Memo,
  Picture,
  Setting,
  Tickets,
} from '@element-plus/icons-vue'
import { useAgentsStore } from '@/stores/agents'
import { useProjectTreeStore } from '@/stores/project-tree'
import type { ProjectTreeEntry } from '@/stores/project-tree'

defineOptions({ name: 'FileTreeNode' })

const props = defineProps<{
  entry: ProjectTreeEntry
  depth: number
}>()

// 行内编辑状态由 FileTreePanel 统一持有（同一时刻只允许一个输入框），
// 节点只负责渲染；动作同样由面板 provide，节点不重复实现落盘逻辑
interface TreeEditState {
  mode: '' | 'create' | 'rename'
  parentPath: string
  targetPath: string
  type: 'file' | 'dir'
  value: string
}

const store = useProjectTreeStore()
const agentsStore = useAgentsStore()

// 由 FileTreePanel 提供：点击文件时打开预览弹层
const openFile = inject<(path: string) => void>('openFile', () => {})
// 由 FileTreePanel 提供：当前预览中的文件路径
const activeFile = inject<Ref<string>>('activeFile', ref(''))
// 由 FileTreePanel 提供：右键请求上抛（菜单只在面板渲染一份）
const requestContextMenu = inject<(e: MouseEvent, entry: ProjectTreeEntry) => void>(
  'treeContextMenu',
  () => {},
)
// 由 FileTreePanel 提供：行内编辑的共享状态与动作，节点只渲染、面板负责落盘
const editState = inject<TreeEditState>('treeEdit', {
  mode: '',
  parentPath: '',
  targetPath: '',
  type: 'file',
  value: '',
})
const submitEdit = inject<() => void>('treeSubmitEdit', () => {})
const cancelEdit = inject<() => void>('treeCancelEdit', () => {})
// 定位请求的代次：同一代次内每个节点只处理一次，避免节点重新挂载时重复滚动
const revealToken = inject<Ref<number>>('revealToken', ref(0))

const isDir = computed(() => props.entry.type === 'dir')
const isOpen = ref(false)
const loadError = ref('')
const isRevealed = ref(false)
const rowEl = ref<HTMLElement | null>(null)
const editInput = ref<HTMLInputElement | null>(null)
const draftInput = ref<HTMLInputElement | null>(null)
let revealTimer: ReturnType<typeof setTimeout> | null = null

const loading = computed(() => store.isLoading(props.entry.path))
const children = computed(() => (isOpen.value ? store.entriesOf(props.entry.path) : []))
// 收起时不显示数量徽标（children 为空会让计数误显示为 0）
const dirCount = computed(() =>
  isDir.value && isOpen.value && store.isLoaded(props.entry.path) ? children.value.length : null,
)
const isActive = computed(() => !isDir.value && activeFile.value === props.entry.path)

const isRenaming = computed(
  () => editState.mode === 'rename' && editState.targetPath === props.entry.path,
)
// 本次「新建」落点就是当前目录：需要自动展开并渲染草稿行
const isDraftParent = computed(
  () => editState.mode === 'create' && editState.parentPath === props.entry.path,
)

async function handleClick() {
  if (isRenaming.value) return
  if (!isDir.value) {
    openFile(props.entry.path)
    return
  }

  if (isOpen.value) {
    isOpen.value = false
    return
  }

  isOpen.value = true
  if (store.isLoaded(props.entry.path)) return

  loadError.value = ''
  const result = await store.load(agentsStore.currentAgentId, props.entry.path)
  if (result.error) loadError.value = result.error
}

// 右键只上报，菜单浮层由 FileTreePanel 渲染
function handleContextMenu(e: MouseEvent) {
  requestContextMenu(e, props.entry)
}

async function ensureChildrenLoaded() {
  // 面板定位时会逐级预加载，若该目录已加载或正在加载则直接复用，避免重复请求
  if (store.isLoaded(props.entry.path) || store.isLoading(props.entry.path)) return
  loadError.value = ''
  const result = await store.load(agentsStore.currentAgentId, props.entry.path)
  if (result.error) loadError.value = result.error
}

// 新建草稿落在本目录时自动展开，否则用户看不到输入框
watch(isDraftParent, async (visible) => {
  if (!visible || !isDir.value) return
  isOpen.value = true
  await ensureChildrenLoaded()
  await nextTick()
  draftInput.value?.focus()
})

// 重命名：输入框挂载后聚焦并全选原文件名，便于直接覆盖输入
watch(isRenaming, async (renaming) => {
  if (!renaming) return
  await nextTick()
  editInput.value?.focus()
  editInput.value?.select()
})

function onEditKeydown(e: KeyboardEvent) {
  // 阻止冒泡，避免 Enter/Esc 触发行的展开或打开文件
  e.stopPropagation()
  if (e.key === 'Enter') {
    e.preventDefault()
    submitEdit()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancelEdit()
  }
}

// ---- 在树中定位：直接用 store.revealPath 与自身路径比对 ----
// 判定本节点在定位链上的角色：自身即目标 / 目标是自己的后代 / 与自己无关
function revealRole(path: string): 'self' | 'ancestor' | '' {
  if (!path) return ''
  if (path === props.entry.path) return 'self'
  if (path.startsWith(`${props.entry.path}/`)) return 'ancestor'
  return ''
}

async function flashReveal() {
  await nextTick()
  rowEl.value?.scrollIntoView({ block: 'center' })
  isRevealed.value = true
  if (revealTimer) clearTimeout(revealTimer)
  revealTimer = setTimeout(() => { isRevealed.value = false }, 2000)
}

// 已处理的定位代次：节点因折叠/展开重新挂载时，同一次请求不再重复滚动与闪烁
const handledRevealToken = ref(-1)

watch(
  [() => store.revealPath, revealToken],
  async ([path, token]) => {
    if (!path) return
    const role = revealRole(path)
    if (!role) return
    // 目标是自己的后代：展开自己并确保子级已加载，让子节点继续往下定位
    if (role === 'ancestor' && isDir.value) {
      isOpen.value = true
      await ensureChildrenLoaded()
      return
    }
    if (role !== 'self' || handledRevealToken.value === token) return
    handledRevealToken.value = token
    // 定位目标是目录：顺手展开它，用户能直接看到内容（搜索结果点文件夹 = "进入"的预期）
    if (isDir.value) {
      isOpen.value = true
      void ensureChildrenLoaded()
    }
    void flashReveal()
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (revealTimer) clearTimeout(revealTimer)
})
</script>

<style scoped>
.tree-node {
  user-select: none;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding-right: 6px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.14s ease, box-shadow 0.16s ease;
}

.tree-row:hover {
  background: var(--el-fill-color-light);
}

/* 文件区选中高亮：翠绿，与文件标签激活色一致 */
.tree-row.is-active {
  background: rgba(5, 150, 105, 0.13);
  box-shadow: inset 2px 0 0 #059669;
}

/* 被「在树中定位」命中的节点：短暂翠绿高亮，2 秒后由脚本移除 */
.tree-row.is-revealed {
  background: rgba(5, 150, 105, 0.18);
  box-shadow: inset 2px 0 0 #10b981, 0 0 0 1px rgba(16, 185, 129, 0.45);
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

.tree-caret {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--el-text-color-placeholder);
  transition: transform 0.16s ease, color 0.16s ease;
}

.tree-caret.is-open {
  transform: rotate(90deg);
  color: var(--el-text-color-secondary);
}

.tree-caret svg {
  width: 12px;
  height: 12px;
}

.tree-row:hover .tree-caret {
  color: var(--el-text-color-secondary);
}

.tree-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: var(--el-text-color-regular);
  font-size: 12.5px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-row.is-dir .tree-name {
  color: var(--el-text-color-primary);
  font-weight: 600;
}

.tree-count {
  flex-shrink: 0;
  min-width: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  font-size: 10px;
  line-height: 15px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.tree-hint {
  display: flex;
  align-items: center;
  gap: 5px;
  padding-top: 3px;
  padding-bottom: 3px;
  color: var(--el-text-color-placeholder);
  font-size: 11px;
}

.tree-hint-error {
  color: var(--el-color-danger);
  word-break: break-all;
}
</style>
