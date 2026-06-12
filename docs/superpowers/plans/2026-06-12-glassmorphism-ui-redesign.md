# Glassmorphism UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the flat dark-theme frontend into a premium glassmorphism AI dashboard with frosted panels, gradient accents, and smooth micro-interactions.

**Architecture:** CSS-first approach. Expand design token system, add utility classes and keyframes to `style.css`, then update each component's scoped styles. No logic changes.

**Tech Stack:** Vue 3 (scoped CSS), CSS custom properties, `backdrop-filter`, CSS animations/transitions

**Python Interpreter:** `D:\ProgramData\miniconda3\envs\py312\python.exe`

---

## File Structure

### Modify
- `frontend/src/style.css` — Design tokens, keyframes, utility classes
- `frontend/src/App.vue` — Gradient background, layout gaps
- `frontend/src/components/layout/AppHeader.vue` — Glass nav bar, pulse dot
- `frontend/src/components/layout/LeftSidebar.vue` — Glass panel, glow effects
- `frontend/src/components/layout/RightPanel.vue` — Glass cards, status dots
- `frontend/src/views/ChatView.vue` — Message transition group
- `frontend/src/components/chat/ChatBubble.vue` — Glass/gradient bubbles, entrance anim
- `frontend/src/components/chat/ChatInput.vue` — Glass input, focus glow
- `frontend/src/components/chat/ToolCallCard.vue` — Glass card, accent border, shimmer
- `frontend/src/components/chat/InterruptDialog.vue` — Glass overlay
- `frontend/src/components/dialogs/AgentEditorDialog.vue` — Glass dialog
- `frontend/src/components/panels/ToolGroupPanel.vue` — Glass rows
- `frontend/src/components/panels/ModelSelector.vue` — Glass select

---

### Task 1: Design Tokens + Utilities + Keyframes

**Files:**
- Modify: `frontend/src/style.css`

- [ ] **Step 1: Replace `style.css` with expanded design system**

```css
:root {
  /* === Base palette === */
  --lc-bg-primary: #0d1117;
  --lc-bg-secondary: #161b22;
  --lc-bg-tertiary: #21262d;
  --lc-border: #30363d;
  --lc-text-primary: #e6edf3;
  --lc-text-secondary: #8b949e;
  --lc-accent: #58a6ff;
  --lc-accent-hover: #79c0ff;
  --lc-success: #3fb950;
  --lc-warning: #d29922;
  --lc-danger: #f85149;

  /* === Glass tokens === */
  --lc-glass-bg: rgba(255, 255, 255, 0.03);
  --lc-glass-bg-hover: rgba(255, 255, 255, 0.06);
  --lc-glass-bg-active: rgba(255, 255, 255, 0.09);
  --lc-glass-border: rgba(255, 255, 255, 0.08);
  --lc-glass-border-hover: rgba(255, 255, 255, 0.14);
  --lc-glass-blur: 12px;
  --lc-glass-blur-heavy: 20px;

  /* === Gradients === */
  --lc-gradient-bg: linear-gradient(135deg, #0d0d2b 0%, #0a1628 40%, #0d1f2d 100%);
  --lc-gradient-accent: linear-gradient(135deg, #58a6ff 0%, #a371f7 100%);
  --lc-gradient-user-bubble: linear-gradient(135deg, #1a3a5c 0%, #1a2744 100%);

  /* === Spacing === */
  --lc-space-xs: 4px;
  --lc-space-sm: 8px;
  --lc-space-md: 12px;
  --lc-space-lg: 16px;
  --lc-space-xl: 24px;
  --lc-space-2xl: 32px;

  /* === Radius === */
  --lc-radius-sm: 6px;
  --lc-radius-md: 10px;
  --lc-radius-lg: 14px;
  --lc-radius-xl: 20px;

  /* === Shadows === */
  --lc-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
  --lc-shadow-md: 0 4px 16px rgba(0, 0, 0, 0.3);
  --lc-shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.4);
  --lc-shadow-glow: 0 0 20px rgba(88, 166, 255, 0.15);
  --lc-shadow-glow-active: 0 0 30px rgba(88, 166, 255, 0.3);

  /* === Transitions === */
  --lc-transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --lc-transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
  --lc-transition-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* === Base === */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--lc-gradient-bg);
  color: var(--lc-text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

* {
  box-sizing: border-box;
}

/* === Scrollbar === */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* === Keyframes === */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

@keyframes float-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(88, 166, 255, 0.15); }
  50% { box-shadow: 0 0 24px rgba(88, 166, 255, 0.35); }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes dot-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* === Utility classes === */
.glass-panel {
  background: var(--lc-glass-bg);
  backdrop-filter: blur(var(--lc-glass-blur));
  -webkit-backdrop-filter: blur(var(--lc-glass-blur));
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-lg);
}

.glass-panel-heavy {
  background: var(--lc-glass-bg);
  backdrop-filter: blur(var(--lc-glass-blur-heavy));
  -webkit-backdrop-filter: blur(var(--lc-glass-blur-heavy));
  border: 1px solid var(--lc-glass-border);
  border-radius: var(--lc-radius-xl);
}

/* === Element Plus overrides for dark glass === */
.el-dialog {
  background: rgba(22, 27, 34, 0.9) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border: 1px solid var(--lc-glass-border) !important;
  border-radius: var(--lc-radius-xl) !important;
  box-shadow: var(--lc-shadow-lg) !important;
}

.el-dialog__header {
  border-bottom: 1px solid var(--lc-glass-border) !important;
}

.el-input__wrapper {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid var(--lc-glass-border) !important;
  border-radius: var(--lc-radius-sm) !important;
  transition: border-color var(--lc-transition-fast), box-shadow var(--lc-transition-fast) !important;
}

.el-input__wrapper:focus-within {
  border-color: var(--lc-accent) !important;
  box-shadow: 0 0 12px rgba(88, 166, 255, 0.1) !important;
}

.el-select__wrapper {
  background: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid var(--lc-glass-border) !important;
  border-radius: var(--lc-radius-sm) !important;
}
```

- [ ] **Step 2: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 2: App Shell + Header

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/layout/AppHeader.vue`

- [ ] **Step 1: Update `App.vue` styles**

Replace the `<style scoped>` section:

```css
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--lc-gradient-bg);
  position: relative;
  overflow: hidden;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 1px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
```

- [ ] **Step 2: Redesign `AppHeader.vue` styles**

Apply glass nav bar styling. Keep template and script intact; replace `<style scoped>`:

Key changes:
- Background → `var(--lc-glass-bg)` with `backdrop-filter: blur(var(--lc-glass-blur-heavy))`
- Border-bottom → `var(--lc-glass-border)`
- Agent selector items → pill-shaped with hover glow
- Connection dot → green pulse animation
- Overall padding and height adjustments

- [ ] **Step 3: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 3: Left Sidebar

**Files:**
- Modify: `frontend/src/components/layout/LeftSidebar.vue`

- [ ] **Step 1: Update sidebar styles to glass**

Key changes:
- `.left-sidebar` → glass panel background + blur
- `.session-item` → transparent base, glass-bg-hover on hover
- `.session-item.active` → glow-pulse border + brighter glass
- "新对话" button → gradient accent with hover glow animation
- Context menu → glass-panel-heavy styling
- Group headers → subtle separator line below
- Add `transition` to all interactive elements

- [ ] **Step 2: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 4: Chat Area (ChatView + ChatBubble + ChatInput)

**Files:**
- Modify: `frontend/src/views/ChatView.vue`
- Modify: `frontend/src/components/chat/ChatBubble.vue`
- Modify: `frontend/src/components/chat/ChatInput.vue`

- [ ] **Step 1: Add message transition to `ChatView.vue`**

Wrap messages in `<TransitionGroup>`:
```vue
<TransitionGroup name="msg" tag="div" class="messages-area" ref="messagesRef">
  <ChatBubble v-for="msg in messages" :key="msg.id" :message="msg" />
</TransitionGroup>
```

Add transition CSS:
```css
.msg-enter-active {
  animation: float-in var(--lc-transition-slow) ease both;
}
```

- [ ] **Step 2: Redesign `ChatBubble.vue`**

User messages:
- Background: `var(--lc-gradient-user-bubble)`
- Aligned right with `margin-left: auto`
- Border-radius: `14px 14px 4px 14px`
- Border: `1px solid rgba(88, 166, 255, 0.2)`

AI messages:
- Background: `var(--lc-glass-bg)`
- Border: `1px solid var(--lc-glass-border)`
- Border-radius: `14px 14px 14px 4px`
- Full width

Streaming state:
- Blinking cursor after content via `::after` pseudo-element

- [ ] **Step 3: Redesign `ChatInput.vue`**

- Container: glass panel with bottom margin
- Textarea: transparent background, no border, focus ring on container
- Send button: gradient accent, scale on hover (1.05), rounded
- Container focus state: glow shadow

- [ ] **Step 4: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 5: Tool Call Card + Interrupt Dialog

**Files:**
- Modify: `frontend/src/components/chat/ToolCallCard.vue`
- Modify: `frontend/src/components/chat/InterruptDialog.vue`

- [ ] **Step 1: Redesign `ToolCallCard.vue`**

- Glass card background
- Left accent border: 3px solid (blue=running, green=done, red=error)
- Running state: shimmer animation overlay
- Done state: fade border to green
- Tool name: bold, tool result: collapsible with smooth height transition
- Entry animation: float-in

- [ ] **Step 2: Update `InterruptDialog.vue`**

- Overlay: dark glass blur
- Dialog: glass-panel-heavy
- Buttons: accent gradient for approve, glass outline for reject

- [ ] **Step 3: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 6: Right Panel + Tool Groups + Model Selector

**Files:**
- Modify: `frontend/src/components/layout/RightPanel.vue`
- Modify: `frontend/src/components/panels/ToolGroupPanel.vue`
- Modify: `frontend/src/components/panels/ModelSelector.vue`

- [ ] **Step 1: Redesign `RightPanel.vue`**

- Panel: glass background + blur
- Each section (Models, Tools, MCP, Skills): separate glass card
- Section headers: icon + bold text + subtle bottom border
- MCP status dots: green=connected (pulse), red=error, gray=disabled
- Switch overrides: add glow when active

- [ ] **Step 2: Update `ToolGroupPanel.vue`**

- Each tool group row: glass-bg-hover on hover
- Switch + label: horizontal flex, aligned
- Disabled state: reduced opacity, cursor not-allowed

- [ ] **Step 3: Update `ModelSelector.vue`**

- Dropdown: glass panel
- Selected item: accent glow border

- [ ] **Step 4: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 7: Agent Editor Dialog

**Files:**
- Modify: `frontend/src/components/dialogs/AgentEditorDialog.vue`

- [ ] **Step 1: Update dialog styles**

- Uses Element Plus `el-dialog` which is already overridden globally in style.css
- Form inputs: inherit global glass input overrides
- Radio groups: pill-style buttons with glass background
- Checkbox groups: glass card container with max-height scroll
- Save button: gradient accent
- Cancel button: glass outline border

- [ ] **Step 2: Verify build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds

---

### Task 8: Final Build + Restart + Verify

- [ ] **Step 1: Full frontend build**

Run: `cd D:\codes\lc-agent\frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 2: Restart server**

```powershell
$pids = (Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue).OwningProcess | Sort-Object -Unique | Where-Object { $_ -ne 0 }
if ($pids) { $pids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }
Start-Sleep 2
D:\ProgramData\miniconda3\envs\py312\python.exe -m bfzs.main --port 8001
```

Working directory: `D:\codes\lc-agent-bfzs`

- [ ] **Step 3: Visual verification checklist**

Open `http://127.0.0.1:8001` and verify:
1. Gradient background visible (not solid black)
2. Header has frosted glass effect
3. Left sidebar is translucent glass
4. Chat messages appear with animation
5. User bubbles have gradient background
6. AI bubbles have glass effect
7. Tool calls show colored accent border
8. Right panel sections are distinct glass cards
9. 60fps scrolling with 20+ messages
10. All Element Plus components still functional (dialog, switch, select)

---

## Summary

After completing all 8 tasks:
- Complete glassmorphism visual overhaul across all 13 files
- 30+ design tokens for consistent styling
- CSS keyframes for pulse, float-in, shimmer, glow, dot-bounce
- Utility classes (`.glass-panel`, `.glass-panel-heavy`, `.glow-accent`)
- Element Plus global overrides for dark glass consistency
- Zero logic/functionality changes — all existing features preserved
- Performant: blur limited to 3-4 parent containers, animations on GPU-composited properties only
