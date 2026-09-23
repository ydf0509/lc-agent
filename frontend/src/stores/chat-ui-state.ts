import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Attachment } from '@/utils/fileUpload'

export interface ChatDraft {
  text: string
  attachments: Attachment[]
}

/** 手动压缩（/compact）结果，按会话记一条（刷新后清空，重新压缩会自愈） */
export interface CompactionRecord {
  summarizedCount: number
  keptCount: number
  keptUserCount: number
  timestamp: number
  /**
   * 压缩前后 checkpoint 历史的估算 token 数（后端返回，不含 system/tools 开销）。
   * 水位条用它算压缩比例做“预估·待更新”展示：供应商真实 input_tokens 要等下一轮才回来。
   */
  checkpointTokensBefore?: number | null
  checkpointTokensAfter?: number | null
}

/**
 * 按会话保存的聊天区 UI 态。
 *
 * 原本这些是 ChatView / ChatInput 的组件本地 ref：切标签时滚动位置会丢、
 * 输入框草稿两个标签共用一个框。又因为 `/` 与 `/c/:id` 之间 ChatView 会真正
 * 销毁重建，这份状态不能放在组件本地 ref。
 */
export const useChatUiStateStore = defineStore('chatUiState', () => {
  const scrollTopBySession = ref<Record<string, number>>({})
  const draftBySession = ref<Record<string, ChatDraft>>({})
  const compactionBySession = ref<Record<string, CompactionRecord>>({})

  function rememberScrollTop(sessionId: string, value: number): void {
    scrollTopBySession.value = { ...scrollTopBySession.value, [sessionId]: value }
  }

  function getScrollTop(sessionId: string): number | undefined {
    return scrollTopBySession.value[sessionId]
  }

  function rememberDraft(sessionId: string, draft: ChatDraft): void {
    draftBySession.value = { ...draftBySession.value, [sessionId]: draft }
  }

  function getDraft(sessionId: string): ChatDraft | undefined {
    return draftBySession.value[sessionId]
  }

  function rememberCompaction(sessionId: string, record: CompactionRecord): void {
    compactionBySession.value = { ...compactionBySession.value, [sessionId]: record }
  }

  function getCompaction(sessionId: string): CompactionRecord | undefined {
    return compactionBySession.value[sessionId]
  }

  function clearSession(sessionId: string): void {
    const nextScroll = { ...scrollTopBySession.value }
    delete nextScroll[sessionId]
    scrollTopBySession.value = nextScroll

    const nextDraft = { ...draftBySession.value }
    delete nextDraft[sessionId]
    draftBySession.value = nextDraft

    const nextCompaction = { ...compactionBySession.value }
    delete nextCompaction[sessionId]
    compactionBySession.value = nextCompaction
  }

  /** 会话 id 改写（本地 id → 真实 id）时搬迁本 store 里的 per-session 状态 */
  function migrateSession(oldId: string, newId: string): void {
    if (oldId === newId) return
    const draft = draftBySession.value[oldId]
    const scrollTop = scrollTopBySession.value[oldId]
    const compaction = compactionBySession.value[oldId]
    clearSession(oldId)
    if (draft) rememberDraft(newId, draft)
    if (scrollTop !== undefined) rememberScrollTop(newId, scrollTop)
    if (compaction) rememberCompaction(newId, compaction)
  }

  return {
    scrollTopBySession,
    draftBySession,
    compactionBySession,
    rememberScrollTop,
    getScrollTop,
    rememberDraft,
    getDraft,
    rememberCompaction,
    getCompaction,
    clearSession,
    migrateSession,
  }
})
