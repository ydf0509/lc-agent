import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) failures.push(`${name} ${message}`)
}

const headerPath = join(root, 'src', 'components', 'layout', 'AppHeader.vue')
const controlsPath = join(root, 'src', 'components', 'layout', 'DesktopWindowControls.vue')
const desktopStorePath = join(root, 'src', 'stores', 'desktop.ts')
const useDesktopPath = join(root, 'src', 'composables', 'useDesktop.ts')

for (const p of [headerPath, controlsPath, desktopStorePath, useDesktopPath]) {
  if (!existsSync(p)) failures.push(`文件不存在: ${p}`)
}
if (failures.length > 0) {
  console.error('desktop 契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

const header = readFileSync(headerPath, 'utf8')
const controls = readFileSync(controlsPath, 'utf8')
const desktopStore = readFileSync(desktopStorePath, 'utf8')
const useDesktop = readFileSync(useDesktopPath, 'utf8')

// ===== 隔离：浏览器默认不受影响（条件渲染，无模式不挂载） =====
expectIncludes('AppHeader.vue', header, 'v-if="showDesktopChrome"')
expectIncludes('AppHeader.vue', header, 'showDesktopChrome = computed(() => desktop.isDesktop && desktop.isFrameless)')
expectIncludes('DesktopWindowControls.vue', controls, 'v-if="isDesktop && isFrameless"')

// ===== 拖拽：pywebview-drag-region 只出现在手柄节点，不出现在 header 自身 =====
expectMatch(
  'AppHeader.vue',
  header,
  /<header class="app-header">/,
  'header 自身必须干净（不带 drag 类），否则内部按钮/选择器会被拖拽吞掉点击',
)
expectIncludes('AppHeader.vue', header, 'desktop-drag-block pywebview-drag-region')
expectIncludes('AppHeader.vue', header, 'desktop-drag-spacer pywebview-drag-region')
// header-center / header-right 绝不允许出现 drag 类
for (const m of header.matchAll(/<div class="header-(center|right)"[^>]*>/g)) {
  if (m[0].includes('pywebview-drag-region')) {
    failures.push(`AppHeader.vue header-${m[1]} 绝不能带 pywebview-drag-region`)
  }
}

// ===== 三按钮：最小化/最大化-还原/关闭齐全，走 bridge 零参调用 =====
expectIncludes('DesktopWindowControls.vue', controls, "callDesktopApi('minimize')")
expectIncludes('DesktopWindowControls.vue', controls, 'toggleMax')
expectIncludes('DesktopWindowControls.vue', controls, 'closeWindow')
expectIncludes('useDesktop.ts', useDesktop, 'await api[fn]()')
expectIncludes('stores/desktop.ts', desktopStore, "callDesktopApi('toggle_max')")

// ===== 桌面 store：单例状态 + bridge 就绪门控 =====
expectIncludes('stores/desktop.ts', desktopStore, 'defineStore(')
expectIncludes('stores/desktop.ts', desktopStore, 'bridgeReady')
expectIncludes('DesktopWindowControls.vue', controls, ':disabled="!bridgeReady"')
expectIncludes('AppHeader.vue', header, 'pywebviewready')

// ===== 双击标题栏切换最大化 =====
expectIncludes('AppHeader.vue', header, '@dblclick="desktop.toggleMax()"')

if (failures.length > 0) {
  console.error('desktop 契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('desktop 契约测试通过')
