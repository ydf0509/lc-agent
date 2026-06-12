# Glassmorphism UI Redesign

## Goal

Transform the current flat dark-theme UI into a modern glassmorphism design with layered depth, frosted panels, gradient accents, and smooth micro-interactions — creating a premium AI agent dashboard experience.

## Current State

- Dark-only theme, GitHub Dark inspired palette
- Element Plus components, mostly un-styled
- 11 CSS variables (no spacing/radius/shadow/animation tokens)
- No transitions or animations
- Flat panels with solid backgrounds and 1px borders
- System font stack, basic typography

## Design Principles

1. **Depth through translucency** — Panels float above a rich gradient background via backdrop-blur
2. **Subtlety over excess** — Effects enhance usability, never distract
3. **Consistent motion** — All animations use the same easing curve and scale proportionally
4. **Progressive disclosure** — Complex UI reveals detail on interaction (hover, expand)
5. **Performance-first** — Use `will-change` sparingly, prefer `transform/opacity` for animations

## Architecture

### Design Token System Expansion

Extend `style.css` `:root` from 11 to ~30 variables organized into categories:

**Glass tokens:**
```css
--lc-glass-bg: rgba(255, 255, 255, 0.03);
--lc-glass-bg-hover: rgba(255, 255, 255, 0.06);
--lc-glass-bg-active: rgba(255, 255, 255, 0.08);
--lc-glass-border: rgba(255, 255, 255, 0.08);
--lc-glass-blur: 12px;
--lc-glass-blur-heavy: 20px;
```

**Gradient tokens:**
```css
--lc-gradient-bg: linear-gradient(135deg, #0d0d2b 0%, #0a1628 40%, #0d1f2d 100%);
--lc-gradient-accent: linear-gradient(135deg, #58a6ff 0%, #a371f7 100%);
--lc-gradient-user-bubble: linear-gradient(135deg, #1a3a5c 0%, #1a2744 100%);
```

**Spacing scale:**
```css
--lc-space-xs: 4px;
--lc-space-sm: 8px;
--lc-space-md: 12px;
--lc-space-lg: 16px;
--lc-space-xl: 24px;
```

**Radius scale:**
```css
--lc-radius-sm: 6px;
--lc-radius-md: 10px;
--lc-radius-lg: 14px;
--lc-radius-xl: 20px;
```

**Shadow/glow tokens:**
```css
--lc-shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.2);
--lc-shadow-md: 0 4px 16px rgba(0, 0, 0, 0.3);
--lc-shadow-glow: 0 0 20px rgba(88, 166, 255, 0.15);
--lc-shadow-glow-active: 0 0 30px rgba(88, 166, 255, 0.25);
```

**Animation tokens:**
```css
--lc-transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
--lc-transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
--lc-transition-slow: 400ms cubic-bezier(0.4, 0, 0.2, 1);
```

### Component Changes

#### 1. App Shell (`App.vue`)

- Body background becomes `var(--lc-gradient-bg)`
- Remove all solid panel backgrounds, replaced with glass effect
- Add a subtle animated gradient overlay (CSS-only, low-opacity background movement)

#### 2. Header (`AppHeader.vue`)

- Glass background: `backdrop-filter: blur(var(--lc-glass-blur-heavy))`
- Semi-transparent border-bottom
- Agent selector: pill/capsule buttons with glow on active
- Connection dot: pulse animation (CSS `@keyframes`)
- Hover states: slight scale + glow

#### 3. Left Sidebar (`LeftSidebar.vue`)

- Glass panel background
- "新对话" button: gradient fill with hover glow
- Session items: transparent hover → glass-bg-hover with border highlight
- Active session: left border glow + slightly brighter glass
- Group headers: uppercase, tracked, with faint separator line
- Smooth height transitions when groups collapse/expand

#### 4. Chat Area (`ChatView.vue` + `ChatBubble.vue`)

**User messages:**
- Gradient background (`--lc-gradient-user-bubble`)
- Aligned right, rounded with larger bottom-right radius cut
- Subtle inner shadow for depth

**AI messages:**
- Glass card: `--lc-glass-bg` + backdrop-blur
- Aligned left, standard rounded corners
- Code blocks maintain `github-dark` but get glass-card wrapper with copy button

**Message animations:**
- Enter: `opacity 0→1` + `translateY(8px→0)` over 300ms
- Use `transition-group` with staggered delay

**Streaming indicator:**
- Blinking cursor character (CSS animation)
- Or 3-dot bounce animation in a glass pill

**Tool calls (`ToolCallCard.vue`):**
- Glass card with colored left accent border (blue=running, green=done, red=error)
- Expand/collapse with smooth height transition
- Running state: subtle shimmer animation on the card

#### 5. Right Panel (`RightPanel.vue` + `ToolGroupPanel.vue`)

- Section cards: individual glass containers
- Category headers with icon + label
- Tool group items: glass rows with hover highlight
- MCP status: colored dot indicator (green pulse for connected)
- Switches: custom-styled or override Element Plus switch with glow effect
- Skills: pill tags with glass background

#### 6. Dialogs (`AgentEditorDialog.vue`, `InterruptDialog.vue`)

- Glass overlay background (darker blur)
- Dialog panel: heavy glass blur + larger radius
- Form inputs: transparent backgrounds with glass border on focus
- Action buttons: primary gets gradient fill, secondary gets glass outline

#### 7. Chat Input (`ChatInput.vue`)

- Glass container with border-glow on focus
- Send button: gradient fill, scale animation on hover
- Textarea: transparent background, placeholder with secondary color

### Global Animations (CSS)

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes float-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(88, 166, 255, 0.2); }
  50% { box-shadow: 0 0 24px rgba(88, 166, 255, 0.4); }
}
```

### Utility Classes (added to `style.css`)

```css
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

.glow-accent {
  box-shadow: var(--lc-shadow-glow);
  transition: box-shadow var(--lc-transition-normal);
}

.glow-accent:hover {
  box-shadow: var(--lc-shadow-glow-active);
}
```

## Performance Considerations

- `backdrop-filter` on 3-4 elements max (sidebar, header, right panel, dialogs)
- Chat bubbles use solid semi-transparent backgrounds (not blur) for scroll performance
- Animations only on `transform` and `opacity` (GPU-composited)
- `will-change: transform` only on elements actively animating (removed after)
- No JS-driven animations; all CSS transitions/keyframes

## Scope

### In scope:
- All 12 `.vue` files get visual updates
- `style.css` expanded with design tokens + utility classes + keyframes
- All existing functionality preserved (no logic changes)

### Out of scope:
- Light theme / theme toggle (future enhancement)
- Custom icon set (continue using Element Plus icons)
- New component library (keep Element Plus)
- Mobile responsive redesign (just ensure nothing breaks)
- New page/view additions

## File Change Summary

| File | Type | Scope |
|------|------|-------|
| `frontend/src/style.css` | Modify | Design tokens, keyframes, utilities |
| `frontend/src/App.vue` | Modify | Gradient background, layout polish |
| `frontend/src/components/layout/AppHeader.vue` | Modify | Glass nav, pill selector, pulse dot |
| `frontend/src/components/layout/LeftSidebar.vue` | Modify | Glass panel, glow items, animations |
| `frontend/src/components/layout/RightPanel.vue` | Modify | Glass cards, status dots, switch glow |
| `frontend/src/views/ChatView.vue` | Modify | Message transition group |
| `frontend/src/components/chat/ChatBubble.vue` | Modify | Glass/gradient bubbles, entrance anim |
| `frontend/src/components/chat/ChatInput.vue` | Modify | Glass input, focus glow, send button |
| `frontend/src/components/chat/ToolCallCard.vue` | Modify | Glass card, accent border, shimmer |
| `frontend/src/components/chat/InterruptDialog.vue` | Modify | Glass overlay + dialog |
| `frontend/src/components/dialogs/AgentEditorDialog.vue` | Modify | Glass dialog styling |
| `frontend/src/components/panels/ToolGroupPanel.vue` | Modify | Glass rows, hover effects |
| `frontend/src/components/panels/ModelSelector.vue` | Modify | Glass dropdown styling |

## Testing Strategy

- Visual verification in browser after each component update
- Performance check: ensure smooth 60fps scrolling in chat with 100+ messages
- Verify Element Plus components still function (switches, dialogs, selects)
- Check backdrop-filter works in target browsers (Chrome, Firefox, Edge)
