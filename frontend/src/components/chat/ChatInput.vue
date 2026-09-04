<template>
  <div class="chat-input-wrapper">
    <div v-if="isEditing" class="edit-banner">
      <span>正在编辑上一条消息</span>
      <button type="button" class="cancel-edit-btn" @click="handleCancelEdit">取消</button>
    </div>
    <div
      class="textarea-shell"
      :class="{
        'is-disabled': isStreamingState,
        'is-streaming': isStreamingState,
        'effect-rainbow-rod': isStreamingState && inputAnimation === 'rainbow-rod',
        'effect-transparent-arc': isStreamingState && inputAnimation === 'transparent-arc',
        'effect-marquee': isStreamingState && inputAnimation === 'marquee',
        'effect-rainbow-gradient': isStreamingState && inputAnimation === 'rainbow-gradient',
      }"
      @drop="handleDrop"
      @dragover="handleDragover"
    >
      <template v-if="isStreamingState && inputAnimation === 'marquee'">
        <span
          v-for="(color, i) in marqueeColors"
          :key="i"
          class="marquee-dot"
          :style="{ '--dot-color': color, '--dot-delay': `${(i / marqueeColors.length) * -4}s` }"
        />
      </template>
      <div v-if="attachments.length > 0" class="attachments-preview">
        <div
          v-for="att in attachments"
          :key="att.id"
          class="attachment-item"
        >
          <img
            v-if="att.type === 'image'"
            :src="att.dataUrl"
            class="attachment-image"
            :alt="att.name"
          />
          <div v-else class="attachment-file">
            <span class="file-icon">📄</span>
            <span class="file-name" :title="att.name">{{ att.name }}</span>
          </div>
          <button
            type="button"
            class="attachment-remove"
            @click="removeAttachment(att.id)"
          >×</button>
        </div>
      </div>

      <div
        v-if="skillMenuOpen && !isStreamingState"
        class="skill-picker"
        role="listbox"
        aria-label="选择 Skill"
        @mousedown.prevent
      >
        <div class="skill-picker-header">
          <span>Skills</span>
          <span class="skill-picker-query">/{{ skillQuery }}</span>
        </div>
        <button
          v-for="(skill, index) in skillSuggestions"
          :key="skill.name"
          type="button"
          class="skill-picker-item"
          :class="{ 'is-active': index === activeSkillIndex }"
          role="option"
          :aria-selected="index === activeSkillIndex"
          @mousedown.prevent="selectSkill(skill)"
        >
          <el-icon class="skill-picker-icon"><MagicStick /></el-icon>
          <span class="skill-picker-main">
            <span class="skill-picker-name">/{{ skill.name }}</span>
            <span class="skill-picker-description">{{ getSkillDescription(skill.description) }}</span>
          </span>
          <span v-if="skill.scope === 'project'" class="skill-picker-scope">项目</span>
          <span v-else-if="skill.scope === 'extra'" class="skill-picker-scope">额外</span>
        </button>
        <div v-if="skillSuggestions.length === 0" class="skill-picker-empty">没有匹配的 Skill</div>
      </div>

      <textarea
        ref="textareaRef"
        v-model="messageText"
        class="chat-textarea"
        rows="1"
        placeholder="Send a message... (可粘贴/拖拽图片或文本文件)"
        enterkeyhint="enter"
        @input="handleInput"
        @keydown="handleKeydown"
        @keyup="handleKeyup"
        @click="updateSkillMenu"
        @blur="closeSkillMenu"
        @paste="handlePaste"
      />
      <div class="input-actions">
        <button
          v-if="!isStreamingState"
          type="button"
          class="input-action-btn attach-btn"
          aria-label="附加文件"
          title="附加图片或文本文件"
          :disabled="isStreamingState"
          @click="triggerFileInput"
        >
          <span class="attach-icon">📎</span>
        </button>
        <input
          ref="fileInputRef"
          type="file"
          multiple
          class="hidden-file-input"
          accept="image/*,.txt,.md,.markdown,.json,.yaml,.yml,.csv,.log,.xml,.html,.htm,.js,.ts,.jsx,.tsx,.py,.go,.rs,.java,.c,.cpp,.h,.hpp,.sh,.sql,.css,.scss,.less,.vue,.toml,.ini,.conf"
          @change="handleFileInputChange"
        />
        <template v-if="isStreamingState">
          <button
            type="button"
            class="input-action-btn stop-btn animated-stop-btn"
            aria-label="停止生成"
            title="停止生成"
            @click="handleStop"
          >
            <span class="stop-spinner" aria-hidden="true">
              <span class="stop-square" />
            </span>
          </button>
          <span class="stop-timer" aria-live="polite">{{ formatElapsed(elapsedSeconds) }}</span>
        </template>
        <button
          v-else-if="messageText || attachments.length > 0"
          type="button"
          class="input-action-btn clear-btn"
          @click="clearInput"
        >
          清空
        </button>
        <button
          v-if="!isStreamingState"
          type="button"
          class="send-btn"
          :disabled="!canSend"
          @click="handleSubmit"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { MagicStick } from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useAgentsStore } from '@/stores/agents'
import { useToolsStore, type Skill } from '@/stores/tools'
import { useInputAnimation } from '@/composables/useInputAnimation'
import {
  type Attachment,
  type ContentBlock,
  buildContentBlocks,
  countImages,
  filesToAttachments,
  imageFilesFromClipboard,
  MAX_IMAGE_COUNT,
} from '@/utils/fileUpload'

const props = defineProps<{
  isStreaming?: boolean
  editContent?: string
  editAttachments?: Attachment[]
  isEditing?: boolean
}>()

const emit = defineEmits<{
  send: [content: ContentBlock[]]
  stop: []
  cancelEdit: []
}>()

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const toolsStore = useToolsStore()
const { isStreaming } = storeToRefs(chatStore)
const { inputAnimation } = useInputAnimation()
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const messageText = ref('')
const attachments = ref<Attachment[]>([])
const skillMenuOpen = ref(false)
const skillQuery = ref('')
const activeSkillIndex = ref(0)

type SkillSuggestion = Skill & { allowed?: boolean }

const availableSkills = computed<SkillSuggestion[]>(() => {
  if (agentsStore.isCodeAgent) return []
  return toolsStore.filteredSkills.filter((skill: SkillSuggestion) =>
    skill.enabled && skill.allowed !== false,
  )
})

const skillSuggestions = computed(() => {
  const query = skillQuery.value.trim().toLocaleLowerCase()
  if (!query) return availableSkills.value
  return availableSkills.value
    .filter((skill) => {
      const name = skill.name.toLocaleLowerCase()
      const description = skill.description.toLocaleLowerCase()
      return name.includes(query) || description.includes(query)
    })
    .sort((a, b) => {
      const aStarts = a.name.toLocaleLowerCase().startsWith(query)
      const bStarts = b.name.toLocaleLowerCase().startsWith(query)
      return Number(bStarts) - Number(aStarts)
    })
})

const isStreamingState = computed(() => props.isStreaming ?? isStreaming.value)
const elapsedSeconds = ref(0)
let elapsedTimer: number | null = null
let localStartTs = 0

function formatElapsed(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60)
    .toString()
    .padStart(2, '0')
  const s = (totalSeconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

watch(
  isStreamingState,
  (streaming) => {
    if (streaming) closeSkillMenu()
    if (streaming) {
      // 每次重新进入 streaming 都以当前时间为本地基准，确保从 0 重新计时
      localStartTs = Date.now()
      // 如果 store 中已经有本次流的开始时间（刚设置的），并且比本地基准更新，用它校正
      const storeTs = chatStore.streamStartTime
      if (storeTs && storeTs > localStartTs - 5000) {
        localStartTs = storeTs
      }
      elapsedSeconds.value = Math.floor((Date.now() - localStartTs) / 1000)
      elapsedTimer = window.setInterval(() => {
        elapsedSeconds.value = Math.floor((Date.now() - localStartTs) / 1000)
      }, 1000)
    } else {
      if (elapsedTimer !== null) {
        clearInterval(elapsedTimer)
        elapsedTimer = null
      }
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (elapsedTimer !== null) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
})
const marqueeColors = [
  '#ff2d95', '#9b5cff', '#2da8ff', '#18e6c3', '#ffe14d', '#ff7a2d',
  '#ff2d95', '#9b5cff', '#2da8ff', '#18e6c3', '#ffe14d', '#ff7a2d',
  '#ff2d95', '#9b5cff', '#2da8ff', '#18e6c3', '#ffe14d', '#ff7a2d',
]
const canSend = computed(() =>
  (Boolean(messageText.value.trim()) || attachments.value.length > 0) && !isStreamingState.value,
)

watch(() => [props.editContent, props.editAttachments] as const, async ([content, atts]) => {
  messageText.value = content || ''
  attachments.value = atts ? [...atts] : []
  await nextTick()
  resizeTextarea()
  if (messageText.value || attachments.value.length > 0) {
    focusTextarea('end')
  }
}, { immediate: true })

onMounted(async () => {
  await nextTick()
  resizeTextarea()
  if (!isStreamingState.value) {
    focusTextarea('end')
  }
})

function resizeTextarea() {
  const textarea = textareaRef.value
  if (!textarea) return
  textarea.style.height = 'auto'
  const maxHeight = Math.floor(window.innerHeight * 0.4)
  const nextHeight = Math.min(textarea.scrollHeight, maxHeight)
  textarea.style.height = `${nextHeight}px`
  textarea.style.overflowY = textarea.scrollHeight > maxHeight ? 'auto' : 'hidden'
}

function getSkillDescription(description: string): string {
  const firstLine = description.split(/\r?\n/, 1)[0].trim()
  return firstLine.length > 100 ? `${firstLine.slice(0, 100)}...` : firstLine
}

function getSkillTrigger(): { start: number; end: number; query: string } | null {
  const textarea = textareaRef.value
  if (!textarea) return null
  const cursor = textarea.selectionStart
  const beforeCursor = messageText.value.slice(0, cursor)
  const match = beforeCursor.match(/(?:^|\s)\/([^\s]*)$/)
  if (!match) return null

  const matchStart = cursor - match[0].length
  return {
    start: matchStart + (match[0].startsWith(' ') ? 1 : 0),
    end: cursor,
    query: match[1],
  }
}

function updateSkillMenu() {
  if (isStreamingState.value || agentsStore.isCodeAgent) {
    closeSkillMenu()
    return
  }
  const trigger = getSkillTrigger()
  if (!trigger) {
    closeSkillMenu()
    return
  }
  const queryChanged = skillQuery.value !== trigger.query
  skillQuery.value = trigger.query
  if (!skillMenuOpen.value || queryChanged) activeSkillIndex.value = 0
  if (activeSkillIndex.value >= skillSuggestions.value.length) activeSkillIndex.value = 0
  skillMenuOpen.value = true
}

function handleInput() {
  resizeTextarea()
  updateSkillMenu()
}

function handleKeyup(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  updateSkillMenu()
}

function closeSkillMenu() {
  skillMenuOpen.value = false
  skillQuery.value = ''
  activeSkillIndex.value = 0
}

function selectSkill(skill: SkillSuggestion) {
  const textarea = textareaRef.value
  const trigger = getSkillTrigger()
  if (!textarea || !trigger) return

  const replacement = `/${skill.name} `
  messageText.value = `${messageText.value.slice(0, trigger.start)}${replacement}${messageText.value.slice(trigger.end)}`
  closeSkillMenu()
  nextTick(() => {
    const cursor = trigger.start + replacement.length
    textarea.focus()
    textarea.setSelectionRange(cursor, cursor)
    resizeTextarea()
  })
}

function focusTextarea(position: 'start' | 'end' = 'end') {
  const textarea = textareaRef.value
  if (!textarea) return
  textarea.focus()
  const cursor = position === 'start' ? 0 : textarea.value.length
  textarea.setSelectionRange(cursor, cursor)
}

function clearInput() {
  messageText.value = ''
  attachments.value = []
  closeSkillMenu()
  nextTick(() => {
    resizeTextarea()
    focusTextarea('end')
  })
}

function handleKeydown(event: KeyboardEvent) {
  if (skillMenuOpen.value && !event.isComposing) {
    if (event.key === 'ArrowDown' && skillSuggestions.value.length > 0) {
      event.preventDefault()
      activeSkillIndex.value = (activeSkillIndex.value + 1) % skillSuggestions.value.length
      return
    }
    if (event.key === 'ArrowUp' && skillSuggestions.value.length > 0) {
      event.preventDefault()
      activeSkillIndex.value = (activeSkillIndex.value - 1 + skillSuggestions.value.length) % skillSuggestions.value.length
      return
    }
    if ((event.key === 'Enter' || event.key === 'Tab') && skillSuggestions.value.length > 0) {
      event.preventDefault()
      selectSkill(skillSuggestions.value[activeSkillIndex.value])
      return
    }
    if (event.key === 'Escape') {
      event.preventDefault()
      closeSkillMenu()
      return
    }
  }
  if (event.key !== 'Enter' || (!event.ctrlKey && !event.metaKey) || event.isComposing) return
  event.preventDefault()
  handleSubmit()
}

function handlePaste(event: ClipboardEvent) {
  if (!event.clipboardData) return
  const imageFiles = imageFilesFromClipboard(event.clipboardData.items)
  if (imageFiles.length === 0) return
  event.preventDefault()
  void addFiles(imageFiles)
}

function handleDrop(event: DragEvent) {
  event.preventDefault()
  if (!event.dataTransfer?.files?.length) return
  void addFiles(Array.from(event.dataTransfer.files))
}

function handleDragover(event: DragEvent) {
  event.preventDefault()
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleFileInputChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  void addFiles(Array.from(input.files))
  input.value = ''
}

async function addFiles(files: File[]) {
  const { attachments: newAtts, rejected } = await filesToAttachments(files)
  if (newAtts.length > 0) {
    attachments.value.push(...newAtts)
    const imgCount = countImages(attachments.value)
    if (imgCount > MAX_IMAGE_COUNT) {
      ElMessage.warning(`图片较多（${imgCount} 张），可能影响响应速度`)
    }
  }
  for (const name of rejected) {
    ElMessage.error(`不支持的文件类型: ${name}，仅支持图片和文本文件`)
  }
  if (newAtts.length === 0 && rejected.length === files.length) {
    ElMessage.error('没有可处理的文件')
  }
}

function removeAttachment(id: string) {
  attachments.value = attachments.value.filter(a => a.id !== id)
}

function handleSubmit() {
  if (isStreamingState.value) return
  const blocks = buildContentBlocks(messageText.value, attachments.value)
  if (blocks.length === 0) return
  closeSkillMenu()
  emit('send', blocks)
  clearInput()
}

function handleStop() {
  emit('stop')
}

function handleCancelEdit() {
  clearInput()
  emit('cancelEdit')
}
</script>

<style scoped>
.chat-input-wrapper {
  padding: 10px 20px 14px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  box-sizing: border-box;
  flex-shrink: 0;
  position: relative;
  z-index: 120;
  width: 100%;
}

.textarea-shell {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 8px;
  width: 100%;
  padding: 7px 8px 7px 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color-overlay);
  box-sizing: border-box;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.textarea-shell:focus-within {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--el-color-primary) 22%, transparent);
}

.textarea-shell.is-disabled {
  border-color: var(--el-border-color-lighter);
}

.textarea-shell.is-streaming::before {
  position: absolute;
  z-index: 0;
  inset: -2px;
  border-radius: 10px;
  content: '';
}

.textarea-shell.is-streaming.effect-rainbow-rod::before {
  background: conic-gradient(
    from 0deg,
    #ff2d95,
    #9b5cff,
    #2da8ff,
    #18e6c3,
    #ffe14d,
    #ff7a2d,
    #ff2d95
  );
  animation: input-conic-spin 2.4s linear infinite;
}

.textarea-shell.is-streaming.effect-transparent-arc::before {
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    #ff2d95 8deg,
    #9b5cff 22deg,
    #2da8ff 36deg,
    #18e6c3 50deg,
    #ffe14d 64deg,
    #ff7a2d 78deg,
    transparent 92deg,
    transparent 360deg
  );
  animation: input-conic-spin 2.4s linear infinite;
}

.textarea-shell.is-streaming.effect-rainbow-gradient::before {
  background: linear-gradient(
    90deg,
    #ff2d95,
    #9b5cff,
    #2da8ff,
    #18e6c3,
    #ffe14d,
    #ff7a2d,
    #ff2d95
  );
  background-size: 300% 100%;
  animation: input-rainbow-gradient 3.6s linear infinite;
}

.textarea-shell.is-streaming.effect-marquee::before {
  background: none;
}

.textarea-shell.is-streaming.effect-marquee::after {
  background: none;
}

.textarea-shell.is-streaming::after {
  position: absolute;
  z-index: 0;
  inset: 1px;
  border-radius: 7px;
  background: var(--el-bg-color-overlay);
  content: '';
}

.textarea-shell.is-streaming > * {
  position: relative;
  z-index: 1;
}

.skill-picker {
  position: absolute;
  z-index: 20;
  left: 8px;
  bottom: calc(100% + 8px);
  width: min(460px, calc(100% - 16px));
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  background: var(--el-bg-color-overlay);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
}

.skill-picker-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px 6px;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.skill-picker-query {
  overflow: hidden;
  color: var(--el-color-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-weight: 500;
  text-overflow: ellipsis;
  text-transform: none;
  white-space: nowrap;
}

.skill-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 48px;
  padding: 7px 10px;
  border: none;
  background: transparent;
  color: var(--el-text-color-primary);
  cursor: pointer;
  text-align: left;
}

.skill-picker-item:hover,
.skill-picker-item.is-active {
  background: var(--el-fill-color-light);
}

.skill-picker-icon {
  flex-shrink: 0;
  color: var(--el-color-primary);
  font-size: 16px;
}

.skill-picker-main {
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.skill-picker-name {
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-picker-description {
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 11px;
  line-height: 16px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-picker-scope {
  flex-shrink: 0;
  padding: 2px 5px;
  border: 1px solid color-mix(in srgb, var(--el-color-primary) 30%, var(--el-border-color));
  border-radius: 4px;
  color: var(--el-color-primary);
  font-size: 10px;
}

.skill-picker-empty {
  padding: 12px 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  text-align: center;
}

@keyframes input-conic-spin {
  to { transform: rotate(360deg); }
}

@keyframes input-rainbow-gradient {
  to { background-position: 300% 0; }
}

.textarea-shell .marquee-dot {
  position: absolute;
  z-index: 2;
  width: 6px;
  height: 6px;
  margin: -3px;
  border-radius: 50%;
  background: var(--dot-color);
  box-shadow: 0 0 6px var(--dot-color), 0 0 12px var(--dot-color);
  pointer-events: none;
  offset-path: inset(-3px round 10px);
  animation: dot-path 4s linear infinite;
  animation-delay: var(--dot-delay);
}

@keyframes dot-path {
  0%   { offset-distance: 0%;   }
  100% { offset-distance: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .textarea-shell.is-streaming::before {
    animation: none;
  }
  .textarea-shell .marquee-dot {
    animation: none;
  }
}

.chat-textarea {
  flex: 1;
  min-width: 0;
  min-height: 22px;
  max-height: 40vh;
  resize: none;
  border: none;
  outline: none;
  padding: 1px 0;
  background: transparent;
  color: var(--el-text-color-primary);
  font: inherit;
  font-size: 14px;
  line-height: 22px;
  overflow-y: hidden;
  scrollbar-width: thin;
}

.chat-textarea::placeholder {
  color: var(--el-text-color-placeholder);
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  min-height: 24px;
}

.input-action-btn,
.send-btn {
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  line-height: 18px;
  padding: 4px 8px;
  transition: background 0.18s ease, color 0.18s ease, opacity 0.18s ease;
}

.input-action-btn {
  background: transparent;
  color: var(--el-text-color-secondary);
}

.input-action-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.stop-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--el-color-danger) 10%, transparent);
  color: var(--el-color-danger);
}

.stop-btn:hover {
  background: color-mix(in srgb, var(--el-color-danger) 16%, transparent);
  color: var(--el-color-danger);
}

.stop-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid color-mix(in srgb, var(--el-color-danger) 28%, transparent);
  border-top-color: var(--el-color-danger);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  animation: stop-spin 0.9s linear infinite;
  box-sizing: border-box;
}

.stop-square {
  width: 6px;
  height: 6px;
  border-radius: 1px;
  background: var(--el-color-danger);
  display: block;
}

.stop-timer {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-danger);
  line-height: 1;
  user-select: none;
  min-width: 36px;
  text-align: center;
}

@keyframes stop-spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

.clear-btn {
  color: var(--el-text-color-secondary);
}

.send-btn {
  background: var(--el-color-primary);
  color: #fff;
  font-weight: 600;
}

.send-btn:hover:not(:disabled) {
  background: var(--el-color-primary-light-3);
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.edit-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  padding: 7px 10px;
  border: 1px solid color-mix(in srgb, var(--el-color-success) 38%, var(--el-border-color));
  border-radius: 8px;
  background: color-mix(in srgb, var(--el-color-success) 12%, var(--el-bg-color-overlay));
  color: var(--el-text-color-primary);
  font-size: 12px;
}

.cancel-edit-btn {
  border: none;
  background: transparent;
  color: var(--el-color-success);
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 4px;
}

.cancel-edit-btn:hover {
  color: var(--el-color-success-light-3);
}

@media (max-width: 520px) {
  .chat-input-wrapper {
    padding: 8px 10px 10px;
  }

  .textarea-shell {
    border-radius: 10px;
    padding: 7px 7px 7px 10px;
  }

  .input-action-btn,
  .send-btn {
    padding: 4px 7px;
  }

  .attachment-item {
    width: 50px;
    height: 50px;
  }
}

.attachments-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px 4px 0;
  width: 100%;
}

.attachment-item {
  position: relative;
  width: 60px;
  height: 60px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  overflow: hidden;
  background: var(--el-fill-color-light);
  display: flex;
  align-items: center;
  justify-content: center;
}

.attachment-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.attachment-file {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 4px;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.file-icon {
  font-size: 20px;
  line-height: 1;
}

.file-name {
  font-size: 9px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 12px;
  line-height: 14px;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.attachment-remove:hover {
  background: rgba(0, 0, 0, 0.8);
}

.attach-btn {
  font-size: 16px;
  line-height: 1;
  padding: 4px 6px;
}

.attach-icon {
  display: inline-block;
}

.hidden-file-input {
  display: none;
}
</style>
