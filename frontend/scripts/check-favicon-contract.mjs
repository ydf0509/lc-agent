import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const indexHtml = readFileSync(join(root, 'index.html'), 'utf8')
const faviconPath = join(root, 'public', 'favicon.svg')
const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) failures.push(`${name} 缺少: ${expected}`)
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) failures.push(`${name} ${message}`)
}

expectIncludes('index.html', indexHtml, '<link rel="icon" type="image/svg+xml" href="/favicon.svg" />')

if (!existsSync(faviconPath)) {
  failures.push('frontend/public/favicon.svg 不存在')
} else {
  const favicon = readFileSync(faviconPath, 'utf8')
  expectIncludes('favicon.svg', favicon, '<title>lc_agent</title>')
  expectIncludes('favicon.svg', favicon, 'viewBox="0 0 64 64"')
  expectMatch('favicon.svg', favicon, /<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/, '缺少 SVG 命名空间')
  expectMatch('favicon.svg', favicon, /#[0-9A-Fa-f]{6}/, '应使用明确颜色，保证标签页小尺寸可辨识')
}

if (failures.length > 0) {
  console.error('favicon 契约测试失败:')
  for (const failure of failures) console.error(`- ${failure}`)
  process.exit(1)
}

console.log('favicon 契约测试通过')
