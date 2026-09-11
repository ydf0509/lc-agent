export const TOOL_CARD_ROUTE = {
  edit: 'edit_block',
  write: 'write_file',
  runCommand: 'command__run_command',
  startBg: 'command__start_background_process',
} as const

const READ_NAMES = new Set([
  'file_read__read_file',
  'file_read__read_multiple_files',
])

const DIRECTORY_NAMES = new Set([
  'file_read__list_directory',
])

const SEARCH_NAMES = new Set([
  'file_read__search_files',
])

const INFO_NAMES = new Set([
  'file_read__get_file_info',
  'get_system_info',
  'utility__get_current_time',
])

const FILE_OP_NAMES = new Set([
  'file_write__create_directory',
  'file_write__move_file',
  'file_write__delete_file',
])

const TERMINAL_NAMES = new Set([
  'command__run_command',
  'command__start_background_process',
  'command__read_process_output',
  'command__kill_process',
  'command__list_all_processes',
  'command__list_agent_started_processes',
])

export type ToolCardKind =
  | 'edit'
  | 'write'
  | 'terminal'
  | 'read'
  | 'directory'
  | 'search'
  | 'info'
  | 'fileOp'
  | 'generic'

/** P0 只实现 edit / write / terminal / generic，其余先走 generic（P1/P2 再拆）。 */
export function resolveToolCardKind(name: string): ToolCardKind {
  if (!name) return 'generic'
  if (name === TOOL_CARD_ROUTE.edit || name.endsWith('__edit_block') || name === 'edit_block') return 'edit'
  if (name === TOOL_CARD_ROUTE.write || name.endsWith('__write_file') || name === 'write_file') return 'write'
  if (TERMINAL_NAMES.has(name) || name.startsWith('command__')) return 'terminal'
  if (READ_NAMES.has(name) || name.endsWith('__read_file') || name.endsWith('__read_multiple_files')) return 'read'
  if (DIRECTORY_NAMES.has(name) || name.endsWith('__list_directory')) return 'directory'
  if (SEARCH_NAMES.has(name) || name.endsWith('__search_files')) return 'search'
  if (INFO_NAMES.has(name) || name.endsWith('__get_file_info')) return 'info'
  if (FILE_OP_NAMES.has(name)) return 'fileOp'
  return 'generic'
}
