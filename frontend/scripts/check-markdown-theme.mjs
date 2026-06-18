import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

const files = {
  markdown: read('src/utils/markdown.ts'),
  theme: read('src/styles/markdown-theme.css'),
  chatView: read('src/views/ChatView.vue'),
}

const failures = []

function expectIncludes(name, content, expected) {
  if (!content.includes(expected)) {
    failures.push(`${name} 缺少: ${expected}`)
  }
}

function expectNotIncludes(name, content, unexpected) {
  if (content.includes(unexpected)) {
    failures.push(`${name} 不应包含: ${unexpected}`)
  }
}

function expectMatch(name, content, pattern, message) {
  if (!pattern.test(content)) {
    failures.push(`${name} ${message}`)
  }
}

expectNotIncludes('markdown.ts', files.markdown, 'highlight.js/styles/github')
expectIncludes('markdown.ts', files.markdown, 'markdown-code-block')
expectIncludes('markdown.ts', files.markdown, 'markdown-code-toolbar')
expectIncludes('markdown.ts', files.markdown, 'markdown-code-copy')
expectIncludes('markdown.ts', files.markdown, 'data-code')
expectIncludes('markdown.ts', files.markdown, 'language-')

expectIncludes('markdown-theme.css', files.theme, '--md-text')
expectIncludes('markdown-theme.css', files.theme, '--md-muted')
expectIncludes('markdown-theme.css', files.theme, '--md-code-bg')
expectIncludes('markdown-theme.css', files.theme, '--md-link')
expectIncludes('markdown-theme.css', files.theme, '.markdown-code-block')
expectIncludes('markdown-theme.css', files.theme, '.markdown-code-toolbar')
expectIncludes('markdown-theme.css', files.theme, '.markdown-code-copy')
expectIncludes('markdown-theme.css', files.theme, 'border-collapse: separate')
expectIncludes('markdown-theme.css', files.theme, 'border-radius: 14px')
expectMatch('markdown-theme.css', files.theme, /html\.dark[\s\S]*--md-code-bg/, '缺少暗色主题 Markdown 变量')
expectMatch('markdown-theme.css', files.theme, /html:not\(\.dark\)[\s\S]*--md-code-bg/, '缺少亮色主题 Markdown 变量')
expectMatch('markdown-theme.css', files.theme, /\.hljs-keyword[\s\S]*color:/, '缺少自定义 highlight.js token 颜色')
expectNotIncludes('markdown-theme.css', files.theme, '#f6f8fa')
expectNotIncludes('markdown-theme.css', files.theme, '#24292f')

expectIncludes('ChatView.vue', files.chatView, 'markdown-code-block')
expectIncludes('ChatView.vue', files.chatView, 'markdown-code-copy')

if (failures.length > 0) {
  console.error('Markdown 主题契约测试失败:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('Markdown 主题契约测试通过')
