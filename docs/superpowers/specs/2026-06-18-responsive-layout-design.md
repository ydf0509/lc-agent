# Responsive Web Layout for Desktop and Mobile

**Date:** 2026-06-18
**Status:** Approved
**Scope:** Make the lc-agent Vue frontend usable on desktop and phone-sized web viewports without replacing Element Plus or Vue Element Plus X.

## Goal

Keep the existing desktop chat workspace while adding a mobile-first single-column experience. On phones, the chat should be the primary screen, with the session list and tools/status panel available through lightweight drawers.

## Current Problem

The current application shell is desktop-only:

- `App.vue` keeps `.app-body` as a horizontal flex row at every viewport width.
- `LeftSidebar.vue` uses a fixed `312px` width, or `68px` when collapsed.
- `RightPanel.vue` uses a fixed `450px` width.
- `AppHeader.vue` keeps a `240px` agent selector plus several text buttons and status labels in one row.

At a phone viewport width, the sidebars consume more width than the viewport before the chat surface is considered, so the page overflows horizontally and the chat input becomes uncomfortable.

## Non-Goals

- Do not replace `element-plus`.
- Do not replace `vue-element-plus-x`.
- Do not change backend APIs, WebSocket contracts, agent/session stores, or MCP/tool logic.
- Do not redesign the visual theme beyond responsive layout and spacing fixes.
- Do not add native mobile app behavior; this remains a responsive web UI.

## Responsive Strategy

### Desktop

Desktop behavior remains familiar:

- Header at the top.
- Left sidebar visible for conversations.
- Center chat view fills remaining space.
- Right panel visible for model, tools, MCP, skills, and status.
- Existing collapse behavior for the left sidebar remains available.

### Mobile

Phone-sized viewports switch to a single-column chat layout:

- The chat area is the default visible workspace.
- The left conversation sidebar becomes an overlay drawer opened from the header.
- The right tools/status panel becomes an overlay drawer opened from the header.
- Header content is condensed so it fits in one row.
- Chat messages, tool cards, code blocks, and the input area fit within the viewport without horizontal page overflow.

## Breakpoints

Use CSS breakpoints rather than JavaScript viewport listeners:

- `> 900px`: desktop layout.
- `<= 900px`: mobile/tablet layout with drawer side panels.
- `<= 520px`: phone tightening for header, chat padding, bubbles, and tool cards.

The `900px` breakpoint is intentionally generous because the existing right panel is `450px`; tablets and narrow desktop windows benefit from the mobile drawer pattern too.

## Component Design

### App Shell

`App.vue` owns responsive shell state:

- `sidebarCollapsed`: existing desktop collapse state.
- `mobileLeftOpen`: whether the conversation drawer is open on mobile.
- `mobileRightOpen`: whether the tools/status drawer is open on mobile.

The app body gains layout classes that distinguish desktop and mobile behavior using CSS. The sidebars remain mounted so their stores and component state do not need a second mobile-specific implementation.

### Header

`AppHeader.vue` gets two optional mobile controls:

- A left menu button that opens the conversation drawer.
- A right panel button that opens the tools/status drawer.

On mobile:

- The logo text may shrink.
- The agent selector uses a fluid width with a smaller max width.
- `编辑` and `+ 新Agent` are hidden because they are lower-frequency controls.
- `+ 新对话` remains visible but becomes compact.
- The long model badge is hidden.
- The connected status keeps a small dot and may hide the text label on narrow phones.

### Left Sidebar Drawer

`LeftSidebar.vue` is reused. On mobile, its width becomes `min(86vw, 340px)` and it is positioned as an overlay panel from the left. A backdrop closes the drawer when clicked.

When a session is selected on mobile, `App.vue` closes the drawer after routing to the session.

### Right Panel Drawer

`RightPanel.vue` is reused. On mobile, its width becomes `min(90vw, 380px)` and it is positioned as an overlay panel from the right. A backdrop closes the drawer when clicked.

The panel keeps its current sections, but padding is reduced slightly so MCP and skill rows remain readable.

### Chat View

`ChatView.vue` gains mobile spacing rules:

- Reduce `.messages-container` padding.
- Increase bubble max width from desktop `85%` to mobile `100%`.
- Ensure markdown code blocks and tool result blocks use horizontal scrolling instead of widening the page.
- Keep the input fixed within the flex column rather than overlaying content.

### Chat Input

`ChatInput.vue` gains mobile spacing rules:

- Reduce wrapper padding.
- Ensure the Element Plus X sender is full width.
- Keep the contenteditable area readable on small screens.

## Accessibility and Interaction

- Mobile drawer buttons use Element Plus icon buttons with clear `aria-label` attributes.
- Backdrop click closes an open drawer.
- Pressing a session in the left drawer closes it on mobile.
- Drawer panels should not create horizontal body scrolling.
- The chat input remains reachable after opening and closing drawers.

## Testing Strategy

### Automated Tests

Add component-level tests for the responsive shell behavior:

- `AppHeader` renders mobile menu and tools buttons when handlers are supplied.
- Clicking the mobile menu button emits `openMobileSidebar`.
- Clicking the mobile tools button emits `openMobileTools`.
- `App.vue` closes the mobile left drawer after a session switch.

Use the existing frontend test setup if present. If no frontend test runner exists, add a minimal Vitest + Vue Test Utils setup scoped to these responsive components.

### Build Verification

Run:

```powershell
npm run build
```

from `D:\codes\lc-agent\frontend`.

### Browser Verification

After rebuilding and restarting bfzs, verify:

- Desktop viewport, e.g. `1440x900`: three-column layout remains usable.
- Phone viewport, e.g. `390x844`: no horizontal page overflow, chat input visible, left drawer opens/closes, right drawer opens/closes.
- Existing chat send flow still works on desktop and mobile.

## Risks

- Element Plus X internal class names may change across versions. Keep selectors scoped and focused on layout rather than internal styling where possible.
- Reusing the same sidebar components inside mobile drawers keeps behavior consistent, but CSS must carefully override fixed desktop widths.
- Header controls can become crowded on very narrow phones if agent names are long; use constrained widths and ellipsis.

## Acceptance Criteria

- Desktop layout still shows left sidebar, chat area, and right panel at wide viewports.
- Mobile layout shows only the chat workspace by default.
- Mobile users can open and close conversation and tools/status drawers.
- Mobile viewport has no document-level horizontal scrolling.
- Chat input and message content remain usable at `390px` width.
- Existing build succeeds.
