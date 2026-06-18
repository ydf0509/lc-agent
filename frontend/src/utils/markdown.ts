import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

function escapeAttr(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function normalizeLanguage(lang: string): string {
  return lang.trim().split(/\s+/)[0]?.toLowerCase() || ''
}

function renderCodeBlock(source: string, lang: string): string {
  const language = normalizeLanguage(lang)
  const knownLanguage = language && hljs.getLanguage(language)
  const highlighted = knownLanguage
    ? hljs.highlight(source, { language }).value
    : md.utils.escapeHtml(source)
  const label = language || 'text'
  const languageClass = language ? ` language-${escapeAttr(language)}` : ''
  const encodedSource = escapeAttr(encodeURIComponent(source))

  return [
    `<div class="markdown-code-block" data-language="${escapeAttr(label)}">`,
    '<div class="markdown-code-toolbar">',
    '<span class="markdown-code-window" aria-hidden="true"><i></i><i></i><i></i></span>',
    `<span class="markdown-code-language">${escapeAttr(label)}</span>`,
    `<button class="markdown-code-copy" type="button" data-code="${encodedSource}" aria-label="复制代码">复制</button>`,
    '</div>',
    `<pre class="hljs"><code class="hljs${languageClass}">${highlighted}</code></pre>`,
    '</div>',
  ].join('')
}

const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str: string, lang: string): string {
    try {
      return renderCodeBlock(str, lang)
    } catch {
      return renderCodeBlock(str, '')
    }
  },
})

export function renderMarkdown(text: string): string {
  return md.render(text)
}
