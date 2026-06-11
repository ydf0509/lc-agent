<template>
  <div class="app-container">
    <AppHeader
      :model-name="toolsStore.currentModel || agentsStore.currentAgent?.default_model || 'N/A'"
      :connected="chatStore.isConnected"
      @edit-agent="editCurrentAgent"
      @new-agent="createNewAgent"
    />

    <div class="app-body">
      <LeftSidebar @new-chat="handleNewChat" @switch-session="handleSwitchSession" />

      <main class="chat-main">
        <ChatView />
      </main>

      <RightPanel />
    </div>

    <AgentEditorDialog ref="agentEditorRef" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useToolsStore } from '@/stores/tools'
import { useAgentsStore } from '@/stores/agents'
import { useSessionsStore } from '@/stores/sessions'
import AppHeader from '@/components/layout/AppHeader.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightPanel from '@/components/layout/RightPanel.vue'
import ChatView from '@/views/ChatView.vue'
import AgentEditorDialog from '@/components/dialogs/AgentEditorDialog.vue'

const chatStore = useChatStore()
const toolsStore = useToolsStore()
const agentsStore = useAgentsStore()
const sessionsStore = useSessionsStore()
const agentEditorRef = ref<InstanceType<typeof AgentEditorDialog>>()

onMounted(async () => {
  await Promise.all([
    toolsStore.init(),
    agentsStore.init(),
    sessionsStore.init(),
  ])
})

async function handleNewChat() {
  const session = await sessionsStore.createSession()
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect(session.id)
}

function handleSwitchSession(sessionId: string) {
  sessionsStore.selectSession(sessionId)
  chatStore.clearMessages()
  chatStore.disconnect()
  chatStore.connect(sessionId)
}

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
