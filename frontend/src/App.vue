<template>
  <div class="app-container">
    <AppHeader
      :model-name="toolsStore.currentModel || agentsStore.currentAgent?.default_model || 'N/A'"
      :connected="chatStore.isConnected"
      @edit-agent="editCurrentAgent"
      @new-agent="createNewAgent"
      @new-chat="handleNewChat"
    />

    <div class="app-body">
      <LeftSidebar
        :collapsed="sidebarCollapsed"
        @new-chat="handleNewChat"
        @switch-session="handleSwitchSession"
        @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      />

      <main class="chat-main">
        <router-view />
      </main>

      <RightPanel />
    </div>

    <AgentEditorDialog ref="agentEditorRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore } from '@/stores/agents'
import { useSessionsStore } from '@/stores/sessions'
import AppHeader from '@/components/layout/AppHeader.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightPanel from '@/components/layout/RightPanel.vue'
import AgentEditorDialog from '@/components/dialogs/AgentEditorDialog.vue'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()
const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()
const sessionsStore = useSessionsStore()
const agentEditorRef = ref<InstanceType<typeof AgentEditorDialog>>()
const sidebarCollapsed = ref(false)
let skipAgentWatch = false

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
    sessionsStore.init(),
  ])

  const agentQuery = route.query.agent as string
  if (agentQuery && agentsStore.agents.find(a => a.id === agentQuery)) {
    agentsStore.selectAgent(agentQuery)
  }

  const sessionId = route.params.sessionId as string
  if (sessionId) {
    restoreSession(sessionId)
  }
})

watch(() => route.params.sessionId, (newId) => {
  if (newId && typeof newId === 'string') {
    restoreSession(newId)
  }
})

async function restoreSession(sessionId: string) {
  const session = sessionsStore.sessions.find(s => s.id === sessionId)
  if (session) {
    sessionsStore.selectSession(sessionId)
    if (session.agent_id && session.agent_id !== agentsStore.currentAgentId) {
      skipAgentWatch = true
      agentsStore.selectAgent(session.agent_id)
    }
    chatStore.clearMessages()
    chatStore.disconnect()
    await chatStore.loadMessages(sessionId)
    chatStore.connect(sessionId)
  }
}

function handleNewChat() {
  const session = sessionsStore.createLocalSession(agentsStore.currentAgentId)
  chatStore.clearMessages()
  chatStore.disconnect()
  router.push({ name: 'chat', params: { sessionId: session.id }, query: { agent: agentsStore.currentAgentId } })
}

async function handleSwitchSession(sessionId: string) {
  const session = sessionsStore.sessions.find(s => s.id === sessionId)
  sessionsStore.selectSession(sessionId)
  chatStore.clearMessages()
  chatStore.disconnect()
  await chatStore.loadMessages(sessionId)
  chatStore.connect(sessionId)
  const agentId = session?.agent_id || agentsStore.currentAgentId
  if (session?.agent_id && session.agent_id !== agentsStore.currentAgentId) {
    skipAgentWatch = true
    agentsStore.selectAgent(session.agent_id)
  }
  router.push({ name: 'chat', params: { sessionId }, query: { agent: agentId } })
}

watch(() => agentsStore.currentAgentId, (newAgentId) => {
  if (skipAgentWatch) {
    skipAgentWatch = false
    return
  }
  if (route.name === 'home' || route.name === 'chat') {
    const session = sessionsStore.createLocalSession(newAgentId)
    chatStore.clearMessages()
    chatStore.disconnect()
    router.push({ name: 'chat', params: { sessionId: session.id }, query: { agent: newAgentId } })
  }
})

function editCurrentAgent() {
  agentEditorRef.value?.open(agentsStore.currentAgent)
}

function createNewAgent() {
  agentEditorRef.value?.open()
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--lc-gradient-bg);
  position: relative;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
