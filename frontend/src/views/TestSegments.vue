<template>
  <div style="padding:20px; background:var(--el-bg-color-page); min-height:100vh; color:var(--el-text-color-regular);">
    <h2>Tool Cards P0 Preview</h2>
    <div style="margin:10px 0; font-size:12px; color:var(--el-text-color-secondary);">
      编辑 / 新建 / 追加 / 短命令 / 长流式 / 失败命令 / 通用兜底 / 技能加载 / 长入参 / 折叠态出错，共 10 组
    </div>
    <div style="display:flex; flex-direction:column; gap:16px; max-width:860px;">
      <section v-for="sample in samples" :key="sample.label">
        <div style="font-size:12px; color:var(--el-text-color-secondary); margin-bottom:4px;">{{ sample.label }}</div>
        <ToolCardRouter :tool-call="sample.toolCall" :collapsed="sample.collapsed ?? false" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import ToolCardRouter from '@/components/chat/tools/ToolCardRouter.vue'
import type { ToolCall } from '@/stores/chat'

function done(over: Partial<ToolCall>): ToolCall {
  return { status: 'done', duration: 800, startTime: Date.now() - 800, ...over } as ToolCall
}

const samples: { label: string; toolCall: ToolCall; collapsed?: boolean }[] = [
  {
    label: '1. edit_block（有 diff）',
    toolCall: done({
      name: 'file_write__edit_block',
      args: { file_path: 'src/app.py', old_string: 'timeout = 30', new_string: 'timeout = 60' },
      result: 'Replaced 1 occurrence(s) in src/app.py\n  1 lines → 1 lines',
      fileDiff: {
        file: 'src/app.py',
        start_line: 40,
        context_before: ['ctx = load()', 'retry = 3'],
        removed: ['timeout = 30'],
        added: ['timeout = 60'],
        context_after: ['logger.info("ok")'],
      },
    }),
  },
  {
    label: '2. write_file 新建',
    toolCall: done({
      name: 'file_write__write_file',
      args: { path: 'docs/report.md', content: '# 周报\n\n- 进展 ...\n' },
      result: 'Written 20 lines to docs/report.md',
      filePreview: {
        file: 'docs/report.md',
        mode: 'rewrite',
        preview_lines: ['# 周报', '', '- 进展 ...'],
        total_lines: 20,
        start_line: 1,
      },
    }),
  },
  {
    label: '3. write_file 追加',
    toolCall: done({
      name: 'file_write__write_file',
      args: { path: 'logs/app.log', content: '2026-09-10 ok\n', mode: 'append' },
      result: 'Appended 1 lines to logs/app.log',
      filePreview: {
        file: 'logs/app.log',
        mode: 'append',
        preview_lines: ['2026-09-10 ok'],
        total_lines: 101,
        start_line: 101,
      },
    }),
  },
  {
    label: '4. run_command 短命令（成功）',
    toolCall: done({
      name: 'command__run_command',
      args: { command: 'git status --short' },
      result: ' M src/app.py\n?? docs/report.md\n[exit_code=0, duration=230ms]',
    }),
  },
  {
    label: '5. run_command 长流式（进行中）',
    toolCall: {
      name: 'command__run_command',
      args: { command: 'npm run dev --port 3000' },
      status: 'running',
      startTime: Date.now() - 2300,
      streamingOutput: '$ npm run dev --port 3000\nready in 1.2s · listening on :3000\n',
    },
  },
  {
    label: '6. run_command 失败',
    toolCall: {
      name: 'command__run_command',
      args: { command: 'pytest tests/test_missing.py' },
      status: 'error',
      duration: 1500,
      startTime: Date.now() - 1500,
      result: 'ERROR: file or directory not found: tests/test_missing.py\n[exit_code=4, duration=1500ms]',
    },
  },
  {
    label: '7. 通用兜底（read_file）',
    toolCall: done({
      name: 'file_read__read_file',
      args: { path: 'src/app.py', offset: 0, length: 50 },
      result: '[Lines 1-50 of 120 total]\nimport os\n...',
    }),
  },
  {
    label: '8. load_skill（展开区显示原始工具名 + 入参）',
    toolCall: done({
      name: 'load_skill',
      args: { skill_name: 'anysearch' },
      result: '## Overview\nAnySearch is a unified real-time search service supporting general web search, vertical domain search, parallel fetching and structured extraction.\n\n## When to use\n- The user asks for current facts that need the open web.\n',
    }),
  },
  {
    label: '9. 通用兜底（长 / 多行入参走块渲染 + 看全文）',
    toolCall: done({
      name: 'mcp__codegraph__codegraph_explore',
      args: {
        query: 'how does the tool card router dispatch',
        options: { depth: 3, include_tests: false, languages: ['python', 'typescript'] },
        extra_notes: '这是一段很长的说明文字，用来验证超过一行的入参不会再把卡片撑爆，而是收进一个固定高度的块里，右下角给一个看全文的入口，点开走弹层看完整内容。',
      },
      result: 'found 12 symbols',
    }),
  },
  {
    label: '10. 通用兜底（折叠态仍然直接露出错误）',
    collapsed: true,
    toolCall: {
      name: 'file_read__read_file',
      args: { path: 'src/not_exists.py' },
      status: 'error',
      duration: 120,
      startTime: Date.now() - 120,
      result: 'FileNotFoundError: src/not_exists.py',
    },
  },
]
</script>
