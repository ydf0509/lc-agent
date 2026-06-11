<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-left">
        <span class="logo">⚡ lc_agent</span>
      </div>
      <div class="header-center">
        <span class="current-agent">Default Agent</span>
        <el-tag size="small" type="info">deepseek-chat</el-tag>
      </div>
      <div class="header-right">
        <el-tag size="small" effect="dark" type="success">已连接</el-tag>
      </div>
    </header>

    <div class="app-body">
      <aside class="left-sidebar">
        <div class="sidebar-section">
          <el-button type="primary" size="small" style="width:100%">+ 新对话</el-button>
        </div>
        <div class="sidebar-section">
          <h4>会话历史</h4>
          <div class="session-item active">当前对话</div>
        </div>
      </aside>

      <main class="chat-main">
        <div class="chat-messages">
          <p class="empty-state">⚡ 开始新的对话</p>
        </div>
        <div class="chat-input-area">
          <el-input
            type="textarea"
            placeholder="输入消息... (Enter发送, Shift+Enter换行)"
            :autosize="{ minRows: 2, maxRows: 6 }"
          />
          <el-button type="primary" class="send-btn">发送</el-button>
        </div>
      </main>

      <aside class="right-panel">
        <div class="panel-section">
          <h4>模型</h4>
          <el-tag>deepseek-chat</el-tag>
        </div>
        <div class="panel-section">
          <h4>工具组</h4>
          <p class="empty-hint">暂无工具</p>
        </div>
        <div class="panel-section">
          <h4>MCP 服务器</h4>
          <p class="empty-hint">暂无 MCP 服务器</p>
        </div>
        <div class="panel-section">
          <h4>Skills</h4>
          <p class="empty-hint">暂无 Skills</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: var(--lc-bg-secondary);
  border-bottom: 1px solid var(--lc-border);
  height: 48px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: var(--lc-accent);
}

.header-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.current-agent {
  font-weight: 500;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.left-sidebar {
  width: 240px;
  background: var(--lc-bg-secondary);
  border-right: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.sidebar-section {
  margin-bottom: 16px;
}

.sidebar-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
}

.session-item {
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}

.session-item.active {
  background: var(--lc-bg-tertiary);
  border-left: 2px solid var(--lc-accent);
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  color: var(--lc-text-secondary);
  font-size: 18px;
}

.chat-input-area {
  padding: 12px 16px;
  border-top: 1px solid var(--lc-border);
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: var(--lc-bg-secondary);
}

.chat-input-area :deep(.el-textarea) {
  flex: 1;
}

.send-btn {
  height: 40px;
}

.right-panel {
  width: 280px;
  background: var(--lc-bg-secondary);
  border-left: 1px solid var(--lc-border);
  padding: 12px;
  overflow-y: auto;
}

.panel-section {
  margin-bottom: 16px;
}

.panel-section h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--lc-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-hint {
  font-size: 12px;
  color: var(--lc-text-secondary);
  margin: 4px 0;
}
</style>
