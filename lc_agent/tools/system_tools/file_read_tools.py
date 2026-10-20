import base64
import fnmatch
import mimetypes
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from lc_agent.tools.registry import tool
from lc_agent.tools.system_tools._config import (
    multimodal_tool_results_enabled,
    validate_read_path,
)

# 可内联成图片块、直接交给模型查看的格式（provider 普遍支持）
_INLINE_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# 按"图片"处理的全部扩展名：svg 是 XML 文本，交回文本分支读
_IMAGE_EXTENSIONS = _INLINE_IMAGE_EXTENSIONS | {".bmp"}
_DEFAULT_LINE_LIMIT = 1000
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
_MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
_MAX_DIRECTORY_ITEMS = 10_000
# 单次 read_multiple_files 最多内联几张图，避免一次把上下文塞满
_MAX_INLINE_IMAGES_PER_CALL = 5


@tool(group="file_read", group_description="文件读取")
def read_file(
    path: Annotated[str, "Path to the file; absolute or relative to the working directory"],
    offset: Annotated[
        int,
        "Start line (0-indexed). 0 = from the beginning; positive N = start at line N; negative N = tail mode, read the last |N| lines.",
    ] = 0,
    length: Annotated[
        int,
        "Maximum number of lines to read (default 1000). Set -1 to read the entire file.",
    ] = _DEFAULT_LINE_LIMIT,
) -> str | list[dict]:
    """Read a file and return its content. Supports text files (with optional line-range paging) and images — an image file (png/jpeg/gif/webp) is returned to you as viewable image content, so you can look at it directly with no extra steps.

    Relative paths resolve from the agent's working directory; absolute paths are also accepted.
    Files larger than 10 MB return an error — use offset/length to page through large files (default: 1000 lines per call).
    The header also names unusual file encoding when the file has any — `| CRLF line endings`, `| CR line endings`, `| mixed line endings`, `| UTF-8 BOM`; a plain LF file without a BOM adds nothing.
    """
    resolved = validate_read_path(path)
    file_path = Path(resolved)

    if not file_path.exists():
        return f"Error: File not found: {path}"
    if file_path.is_dir():
        return f"Error: '{path}' is a directory, use list_directory instead"

    file_size = file_path.stat().st_size
    if file_path.suffix.lower() in _IMAGE_EXTENSIONS:
        return _read_image(file_path)

    if file_size > _MAX_FILE_SIZE:
        return (
            f"Error: File too large ({file_size / 1024 / 1024:.1f} MB, max {_MAX_FILE_SIZE // 1024 // 1024} MB). "
            f"Use offset/length parameters to read specific sections, or use search_files to find relevant content."
        )

    return _read_text(file_path, offset, length)


def _read_image(file_path: Path) -> str | list[dict]:
    """读取图片文件。

    可内联格式返回标准 content blocks（图片块形如
    ``{"type": "image", "base64": ..., "mime_type": ...}``），模型下一轮即可看到；
    开关关闭时退回旧的 base64 文本形态（供端点不支持工具内联图片时使用）。
    不支持的格式（如 bmp）只回文本提示，绝不把二进制当文本读。
    """
    ext = file_path.suffix.lower()
    name = file_path.name
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    try:
        size = file_path.stat().st_size
    except OSError as e:
        return f"Error reading image: {e}"
    size_kb = size / 1024

    if ext not in _INLINE_IMAGE_EXTENSIONS:
        return (
            f"[Image: {name}, {size_kb:.1f} KB, type={mime}]\n"
            "该图片格式暂不支持查看（仅支持 png/jpeg/gif/webp）。"
        )
    if size > _MAX_IMAGE_SIZE:
        return (
            f"Error: Image too large ({size / 1024 / 1024:.1f} MB). "
            f"Max {_MAX_IMAGE_SIZE // 1024 // 1024} MB."
        )
    try:
        data = file_path.read_bytes()
    except OSError as e:
        return f"Error reading image: {e}"

    b64 = base64.b64encode(data).decode("ascii")
    if not multimodal_tool_results_enabled():
        return f"[Image: {name}, {size_kb:.1f} KB, type={mime}]\ndata:{mime};base64,{b64}"

    return [
        {"type": "text", "text": f"[Image: {name}, {size_kb:.1f} KB, {mime}]"},
        {"type": "image", "base64": b64, "mime_type": mime},
    ]


def _encoding_notes(raw: bytes) -> str:
    """Markers describing unusual file encoding, appended to the read header.

    Detection reads the raw bytes: decoding already normalizes line endings away,
    so the decoded text cannot tell CRLF from LF. Plain LF without BOM yields ""
    so the common case adds no noise.
    """
    crlf = raw.count(b"\r\n")
    cr = raw.count(b"\r") - crlf
    lf = raw.count(b"\n") - crlf
    notes: list[str] = []
    if sum(1 for count in (crlf, lf, cr) if count) > 1:
        notes.append("mixed line endings")
    elif crlf:
        notes.append("CRLF line endings")
    elif cr:
        notes.append("CR line endings")
    if raw.startswith(b"\xef\xbb\xbf"):
        notes.append("UTF-8 BOM")
    return "".join(f" | {note}" for note in notes)


def _decode_text(file_path: Path) -> tuple[str, str]:
    """Return (LF-normalized text, encoding markers) for a text file."""
    raw = file_path.read_bytes()
    text = raw.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    return text, _encoding_notes(raw)


def _read_text(file_path: Path, offset: int, length: int) -> str:
    try:
        text, notes = _decode_text(file_path)
    except Exception as e:
        return f"Error reading file: {e}"

    lines = text.splitlines(keepends=True)
    total = len(lines)

    if offset < 0:
        start = max(0, total + offset)
        selected = lines[start:]
    else:
        start = offset
        selected = lines[start:]

    if length >= 0:
        selected = selected[:length]

    content = "".join(selected)
    end_line = start + len(selected)
    header = f"[Lines {start + 1}-{end_line} of {total} total{notes}]"

    if end_line < total:
        header += f" (use offset={end_line} to read more)"

    return f"{header}\n{content}"


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


@tool(group="file_read", group_description="文件读取")
def read_multiple_files(
    paths: Annotated[list[str], "List of file paths to read"],
) -> str | list[dict]:
    """Read multiple files in one call. Prefer this over sequential read_file calls when you need to read multiple known paths — it's faster and reduces round-trips. A single file failure does not affect the others; each result is prefixed with its path, plus its encoding when that is unusual (`| CRLF line endings`, `| CR line endings`, `| mixed line endings`, `| UTF-8 BOM`). Image files (png/jpeg/gif/webp) are returned as viewable image content; at most 5 images are inlined per call."""
    blocks: list[dict] = []
    inlined_images = 0

    for p in paths:
        try:
            resolved = validate_read_path(p)
            file_path = Path(resolved)
            if not file_path.exists():
                blocks.append(_text_block(f"--- {p} ---\nError: File not found"))
                continue
            if file_path.is_dir():
                blocks.append(_text_block(f"--- {p} ---\nError: Is a directory"))
                continue

            if file_path.suffix.lower() in _IMAGE_EXTENSIONS:
                will_inline = (
                    file_path.suffix.lower() in _INLINE_IMAGE_EXTENSIONS
                    and multimodal_tool_results_enabled()
                    and file_path.stat().st_size <= _MAX_IMAGE_SIZE
                )
                if will_inline and inlined_images >= _MAX_INLINE_IMAGES_PER_CALL:
                    blocks.append(_text_block(
                        f"--- {p} ---\n"
                        f"已省略：单次最多内联查看 {_MAX_INLINE_IMAGES_PER_CALL} 张图片，请分批读取。"
                    ))
                    continue
                if will_inline:
                    inlined_images += 1
                image_result = _read_image(file_path)
                if isinstance(image_result, list):
                    blocks.append(_text_block(f"--- {p} ---"))
                    blocks.extend(image_result)
                else:
                    blocks.append(_text_block(f"--- {p} ---\n{image_result}"))
                continue

            text, notes = _decode_text(file_path)
            lines = text.splitlines(keepends=True)
            if len(lines) > _DEFAULT_LINE_LIMIT:
                content = "".join(lines[:_DEFAULT_LINE_LIMIT])
                content += f"\n... [{len(lines) - _DEFAULT_LINE_LIMIT} more lines truncated]"
            else:
                content = text
            blocks.append(_text_block(f"--- {p} ---{notes}\n{content}"))
        except PermissionError as e:
            blocks.append(_text_block(f"--- {p} ---\nError: {e}"))
        except Exception as e:
            blocks.append(_text_block(f"--- {p} ---\nError: {e}"))

    # 全是文本时仍返回字符串，保持既有返回类型与输出格式不变
    if all(block["type"] == "text" for block in blocks):
        return "\n\n".join(block["text"] for block in blocks)
    return blocks


@tool(group="file_read", group_description="文件读取")
def list_directory(
    path: Annotated[str, "Directory path to list"],
    depth: Annotated[int, "Maximum number of directory levels to list; minimum 1, default 2"] = 2,
    exclude: Annotated[
        list[str] | None,
        "Entry names or glob patterns to exclude from the listing, e.g. ['node_modules', '__pycache__', '*.pyc']. "
        "Matched case-sensitively against basenames at every depth; excluded directories are skipped entirely (not recursed into).",
    ] = None,
) -> str:
    """List directory contents up to the specified depth; depth=1 lists only direct children. Results are capped at 10,000 entries; if truncated, reduce depth and inspect subdirectories individually."""
    if depth < 1:
        return "Error: depth must be at least 1"

    resolved = validate_read_path(path)
    dir_path = Path(resolved)

    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    if not dir_path.is_dir():
        return f"Error: '{path}' is not a directory"

    lines: list[str] = []
    truncated = _walk_dir(dir_path, lines, depth, current_depth=1, exclude=exclude)
    if truncated:
        lines.append(f"... [truncated: showing the first {_MAX_DIRECTORY_ITEMS} entries]")
        lines.append(
            "The directory listing is incomplete. Reduce depth and call list_directory on individual subdirectories to inspect their contents."
        )
    return "\n".join(lines)


_ALWAYS_IGNORE = frozenset({".git"})


def _is_excluded(name: str, patterns: list[str]) -> bool:
    return any(name == p or fnmatch.fnmatchcase(name, p) for p in patterns)


def _walk_dir(
    dir_path: Path, lines: list[str], max_depth: int, current_depth: int, exclude: list[str] | None
) -> bool:
    try:
        entries = sorted(dir_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        lines.append(f"{'  ' * (current_depth - 1)}[Permission denied]")
        return False

    for entry in entries:
        if entry.name in _ALWAYS_IGNORE:
            continue
        if exclude and _is_excluded(entry.name, exclude):
            continue
        if len(lines) >= _MAX_DIRECTORY_ITEMS:
            return True

        indent = "  " * (current_depth - 1)
        if entry.is_dir():
            lines.append(f"{indent}[DIR] {entry.name}/")
            if current_depth < max_depth and _walk_dir(
                entry, lines, max_depth, current_depth + 1, exclude=exclude
            ):
                return True
        else:
            size = entry.stat().st_size
            lines.append(f"{indent}[FILE] {entry.name} ({_format_size(size)})")

    return False


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


@tool(group="file_read", group_description="文件读取")
def get_file_info(
    path: Annotated[str, "File or directory path"],
) -> str:
    """Get detailed metadata for a file or directory: path, type, size, timestamps, and line count. Use this instead of read_file when you only need metadata (e.g. to check size or line count before deciding whether to page through the file)."""
    resolved = validate_read_path(path)
    file_path = Path(resolved)

    if not file_path.exists():
        return f"Error: Path not found: {path}"

    stat = file_path.stat()
    info_lines = [
        f"path: {resolved}",
        f"type: {'directory' if file_path.is_dir() else 'file'}",
        f"size: {_format_size(stat.st_size)}",
        f"created: {datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()}",
        f"modified: {datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()}",
    ]

    if file_path.is_file():
        if stat.st_size > _MAX_FILE_SIZE:
            info_lines.append(f"line_count: [file too large to count, {stat.st_size / 1024 / 1024:.1f} MB]")
        else:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
                info_lines.append(f"line_count: {line_count}")
            except Exception:
                info_lines.append("line_count: [unable to count - binary?]")

    return "\n".join(info_lines)


@tool(group="file_read", group_description="文件读取")
def search_files(
    path: Annotated[str, "Root directory to search in"],
    pattern: Annotated[str, '''Search pattern; regex/text for content search, glob pattern (e.g. '*.py') for file search.
     "search_type='files' 时为匹配完整文件名的通配符模式：'*celery*' 表示文件名包含 celery，"
    "裸词 'celery' 仅匹配名字恰好叫 celery 的文件；"
    "search_type='content' 时为在文件内容中匹配的正则或文本，裸词即可。",
    '''],
    search_type: Annotated[
        str,
        "Search mode: 'content' searches inside file contents; 'files' matches filenames by glob pattern",
    ] = "content",
    max_results: Annotated[int, "Maximum number of results to return"] = 50,
    ignore_case: Annotated[bool, "Case-insensitive matching"] = True,
    file_pattern: Annotated[
        str | None,
        "Filename glob filter for content searches (e.g. '*.py' to search only Python files)",
    ] = None,
    context_lines: Annotated[int, "Context lines to include around each content match"] = 2,
) -> str:
    """Search file names by glob pattern or file contents by regex/text (powered by ripgrep). Use search_type='files' for filename lookup, 'content' for full-text search."""
    resolved = validate_read_path(path)

    rg_path = shutil.which("rg")
    if not rg_path:
        return "Error: ripgrep (rg) not found on PATH. Please install ripgrep."

    if search_type == "files":
        return _search_files_by_name(rg_path, resolved, pattern, max_results, ignore_case)
    else:
        return _search_files_by_content(
            rg_path, resolved, pattern, max_results, ignore_case, file_pattern, context_lines
        )


def _search_files_by_name(
    rg_path: str, root: str, pattern: str, max_results: int, ignore_case: bool
) -> str:
    cmd = [rg_path, "--files"]
    glob_flag = "--iglob" if ignore_case else "--glob"
    cmd.extend([glob_flag, pattern])
    cmd.append(root)

    return _run_rg(cmd, max_results)


def _search_files_by_content(
    rg_path: str,
    root: str,
    pattern: str,
    max_results: int,
    ignore_case: bool,
    file_pattern: str | None,
    context_lines: int,
) -> str:
    cmd = [rg_path, "--line-number", "--no-heading"]
    # 压缩后的单行文件（如 .min.js）一行可达数十万字符，按行数截断挡不住。
    # 限制列宽让 rg 直接弃掉超长行，只保留「文件:行号」定位，避免整行灌进对话上下文。
    cmd.extend(["--max-columns", "1000", "--max-columns-preview"])
    if ignore_case:
        cmd.append("--ignore-case")
    if context_lines > 0:
        cmd.extend(["-C", str(context_lines)])
    if max_results > 0:
        cmd.extend(["-m", str(max_results)])
    if file_pattern:
        cmd.extend(["--glob", file_pattern])
    cmd.extend(["--", pattern, root])

    return _run_rg(cmd, max_results)


def _run_rg(cmd: list[str], max_results: int) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds. Try a more specific pattern or directory."
    except Exception as e:
        return f"Error running search: {e}"

    if result.returncode == 1:
        return "No matches found."
    if result.returncode not in (0, 1):
        return f"Search error (exit code {result.returncode}): {result.stderr.strip()}"

    output = result.stdout
    lines = output.splitlines()
    keep = max_results * 5
    if len(lines) > keep:
        omitted = len(lines) - keep
        output = "\n".join(lines[:keep])
        output += (
            f"\n\n... [output truncated: showing first {keep} of {len(lines)} lines, "
            f"{omitted} more lines omitted — narrow the pattern or path to see the rest]"
        )

    return output
