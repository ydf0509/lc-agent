#!/usr/bin/env python3
"""Direct OpenAI-compatible chat-completions probe (no LangChain).

Why this exists
---------------
When lc-agent/BFZS hits ``httpx.ReadError`` during a long stream, this script
isolates the provider/edge by sending the same kind of request with only
``httpx`` + ``tiktoken``:

    POST {base_url}/chat/completions
    Authorization: Bearer {key}
    stream=true

It builds a prompt of approximately N tokens, streams SSE, and prints:
- HTTP status / request id / first-data latency
- chunk count, content chars, finish_reason, usage
- the full exception cause chain (including httpcore/OS errors)

It never imports LangChain or lc_agent, and never prints the API key.

Examples
--------
Dry run (no network, no key needed)::

    python probe.py --dry-run --target-tokens 255000

Small smoke test against CommandCode (raw model name, not ``cm-*`` alias)::

    python probe.py \
      --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" \
      --model deepseek/deepseek-v4.1-flash \
      --target-tokens 1000 --max-tokens 8

Large-context test (the one that reproduces the failure)::

    python probe.py \
      --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" \
      --model deepseek/deepseek-v4.1-flash \
      --target-tokens 340000 --max-tokens 8 --timeout 180

Long-output test (closer to a real agent turn)::

    python probe.py \
      --env-file "D:/codes/ydfhome/importtantdir/envs/sec_dotenv.env" \
      --model deepseek/deepseek-v4.1-flash \
      --target-tokens 340000 --max-tokens 2000 --long-output --timeout 300

Non-streaming comparison::

    python probe.py ... --target-tokens 340000 --no-stream
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

DEFAULT_BASE_URL = "https://api.commandcode.ai/provider/v1"
DEFAULT_MODEL = "deepseek/deepseek-v4.1-flash"
DEFAULT_API_KEY_ENV = "COMMANDCODE_API_KEY"
DEFAULT_CHAT_PATH = "/chat/completions"

FILLER = (
    "This is a context-length probe. The text is intentionally repetitive and "
    "contains no task. Ignore it and continue reading until the final instruction. "
)
FINAL_INSTRUCTION = "\n\nIgnore all repeated text above. Reply with exactly: OK"
LONG_INSTRUCTION = (
    "\n\nIgnore all repeated text above. Write a detailed technical explanation "
    "of why long-lived HTTP streaming connections can fail, about 1500 words. "
    "Do not stop early and do not reply with just OK."
)
TOOL_INSTRUCTION = (
    "\n\nIgnore all repeated text above. Call the get_current_time tool now. "
    "Do not answer in text."
)
TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Return the current time.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }
]

_TOKEN_ENCODER = None
try:
    import tiktoken

    _TOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    # The script still works without tiktoken; character count is only an estimate.
    _TOKEN_ENCODER = None


def count_tokens(text: str) -> int:
    if _TOKEN_ENCODER is not None:
        return len(_TOKEN_ENCODER.encode(text))
    return max(1, len(text) // 4)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Raw OpenAI-compatible streaming probe for long-context ReadError diagnosis.",
    )
    parser.add_argument(
        "--base-url",
        default=(
            os.getenv("RAW_BASE_URL")
            or os.getenv("COMMANDCODE_BASE_URL")
            or DEFAULT_BASE_URL
        ),
        help="API base URL, e.g. https://api.commandcode.ai/provider/v1",
    )
    parser.add_argument("--chat-path", default=DEFAULT_CHAT_PATH)
    parser.add_argument(
        "--model",
        default=os.getenv("RAW_MODEL") or os.getenv("COMMANDCODE_MODEL") or DEFAULT_MODEL,
        help="Raw model name sent to the API (CommandCode uses names like xiaomi/mimo-v2.6-pro, not cm-* aliases).",
    )
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument(
        "--api-key",
        default=None,
        help="Prefer env/--env-file; passing a key on the CLI can leak into shell history.",
    )
    parser.add_argument(
        "--env-file",
        default=None,
        help="dotenv file to load if the key is not already in the environment.",
    )
    parser.add_argument("--target-tokens", type=int, default=2000)
    parser.add_argument("--system-tokens", type=int, default=0)
    parser.add_argument("--instruction", default=None)
    parser.add_argument("--long-output", action="store_true")
    parser.add_argument("--tool-call", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    parser.add_argument("--include-usage", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--request-file",
        default=None,
        help="Exact OpenAI chat-completions JSON body to replay (e.g. from chat_ui_messages.http_traces request.body).",
    )
    parser.add_argument(
        "--override-max-tokens",
        type=int,
        default=None,
        help="Override max_tokens / max_completion_tokens from the request file (useful for a cheap replay).",
    )
    parser.add_argument(
        "--override-model",
        default=None,
        help="Override model from the request file (e.g. replay an ark trace against CommandCode).",
    )
    return parser.parse_args()


def load_env_values(args: argparse.Namespace) -> dict[str, str]:
    values: dict[str, str] = {}
    candidates: list[Path] = []
    if args.env_file:
        candidates.append(Path(args.env_file))
    else:
        candidates.extend([Path.cwd() / ".env", Path.cwd() / ".env.local"])
    for path in candidates:
        if path.exists():
            values.update({k: v for k, v in dotenv_values(path).items() if v is not None})
            print(f"env_file: {path}")
    return values


def resolve_api_key(args: argparse.Namespace, env_values: dict[str, str]) -> str | None:
    if args.api_key:
        return args.api_key
    key = os.getenv(args.api_key_env) or env_values.get(args.api_key_env)
    if key:
        return key
    for name in ("COMMANDCODE_API_KEY", "OPENAI_API_KEY", "ARK_API_KEY"):
        key = os.getenv(name) or env_values.get(name)
        if key:
            return key
    return None


def build_messages(
    target_tokens: int,
    system_tokens: int,
    instruction: str,
) -> tuple[list[dict[str, str]], int]:
    target_tokens = max(1, target_tokens)
    system_tokens = max(0, min(system_tokens, target_tokens - 1))
    filler_tokens = max(1, count_tokens(FILLER))
    total_repeats = max(1, target_tokens // filler_tokens)
    system_repeats = system_tokens // filler_tokens
    user_repeats = max(1, total_repeats - system_repeats)

    messages: list[dict[str, str]] = []
    if system_repeats:
        messages.append({"role": "system", "content": FILLER * system_repeats})
    messages.append({"role": "user", "content": FILLER * user_repeats + instruction})
    estimated = sum(count_tokens(m["content"]) for m in messages)
    return messages, estimated


def build_url(base_url: str, chat_path: str) -> str:
    base = base_url.rstrip("/")
    path = chat_path if chat_path.startswith("/") else "/" + chat_path
    if base.endswith(path):
        return base
    return base + path


def proxy_env_names() -> list[str]:
    names = (
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    )
    return [name for name in names if os.getenv(name)]


def print_response_meta(response: httpx.Response) -> None:
    print(f"status: {response.status_code} {response.reason_phrase}")
    print(f"http_version: {response.http_version}")
    for header in ("content-type", "x-request-id", "cf-ray", "server"):
        value = response.headers.get(header)
        if value:
            print(f"{header}: {value}")


def print_exception_chain(error: BaseException) -> None:
    print("--- ERROR ---")
    current: BaseException | None = error
    seen: set[int] = set()
    depth = 0
    while current is not None and id(current) not in seen and depth < 8:
        seen.add(id(current))
        try:
            text = str(current)[:1000]
        except BaseException:
            text = "<str() failed>"
        print(f"  {type(current).__module__}.{type(current).__name__}: {text!r}")
        try:
            print(f"    repr: {repr(current)[:1000]}")
        except BaseException:
            print("    repr: <repr() failed>")
        current = current.__cause__ or current.__context__
        depth += 1


def report_exception(
    error: BaseException,
    *,
    start: float,
    first_data_at: float | None,
    chunks: int,
    response: httpx.Response | None,
    tool_call_chunks: int = 0,
    tool_arg_chars: int = 0,
) -> None:
    print_exception_chain(error)
    print(f"elapsed: {time.monotonic() - start:.2f}s")
    print(f"first_data_at: {first_data_at if first_data_at is not None else 'None'}")
    print(f"chunks: {chunks}")
    print(f"tool_call_chunks: {tool_call_chunks}")
    print(f"tool_arg_chars: {tool_arg_chars}")
    if response is not None:
        print_response_meta(response)
    request = getattr(error, "request", None)
    if request is not None:
        print(f"request_url: {request.url}")


def run_stream(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> int:
    start = time.monotonic()
    response: httpx.Response | None = None
    first_data_at: float | None = None
    chunks = 0
    content_chars = 0
    tool_call_chunks = 0
    tool_arg_chars = 0
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    stream_error: Any = None

    try:
        with client.stream("POST", url, headers=headers, json=payload) as response:
            print_response_meta(response)
            if response.status_code != 200:
                body = response.read().decode("utf-8", "replace")
                print(f"body[:4000]: {body[:4000]}")
                print(f"elapsed: {time.monotonic() - start:.2f}s")
                return 1

            for line in response.iter_lines():
                if not line:
                    continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if first_data_at is None:
                    first_data_at = time.monotonic() - start
                    print(f"first_data_at: {first_data_at:.2f}s")
                if "error" in obj:
                    stream_error = obj["error"]
                    print(f"stream_error: {json.dumps(stream_error, ensure_ascii=False)[:2000]}")
                    break
                chunks += 1
                if obj.get("usage"):
                    usage = obj["usage"]
                for choice in obj.get("choices", []):
                    delta = choice.get("delta") or {}
                    text = delta.get("content") or delta.get("reasoning_content") or ""
                    content_chars += len(text)
                    tool_calls = delta.get("tool_calls") or []
                    if tool_calls:
                        tool_call_chunks += 1
                    for tool_call in tool_calls:
                        args_text = (tool_call.get("function") or {}).get("arguments") or ""
                        tool_arg_chars += len(args_text)
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

            print(f"chunks: {chunks}")
            print(f"content_chars: {content_chars}")
            print(f"tool_call_chunks: {tool_call_chunks}")
            print(f"tool_arg_chars: {tool_arg_chars}")
            print(f"finish_reason: {finish_reason}")
            print(f"usage: {json.dumps(usage, ensure_ascii=False) if usage else None}")
            print(f"elapsed: {time.monotonic() - start:.2f}s")
            if stream_error is not None:
                print("RESULT: STREAM_ERROR")
                return 2
            print("RESULT: OK")
            return 0
    except httpx.ReadTimeout as error:
        report_exception(
            error,
            start=start,
            first_data_at=first_data_at,
            chunks=chunks,
            response=response,
            tool_call_chunks=tool_call_chunks,
            tool_arg_chars=tool_arg_chars,
        )
        print("RESULT: READ_TIMEOUT")
        return 3
    except httpx.ReadError as error:
        report_exception(
            error,
            start=start,
            first_data_at=first_data_at,
            chunks=chunks,
            response=response,
            tool_call_chunks=tool_call_chunks,
            tool_arg_chars=tool_arg_chars,
        )
        print("RESULT: READ_ERROR")
        return 2
    except httpx.HTTPError as error:
        report_exception(
            error,
            start=start,
            first_data_at=first_data_at,
            chunks=chunks,
            response=response,
            tool_call_chunks=tool_call_chunks,
            tool_arg_chars=tool_arg_chars,
        )
        print("RESULT: HTTP_ERROR")
        return 2
    except Exception as error:
        report_exception(
            error,
            start=start,
            first_data_at=first_data_at,
            chunks=chunks,
            response=response,
            tool_call_chunks=tool_call_chunks,
            tool_arg_chars=tool_arg_chars,
        )
        print("RESULT: ERROR")
        return 2


def run_non_stream(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> int:
    start = time.monotonic()
    response: httpx.Response | None = None
    try:
        response = client.post(url, headers=headers, json=payload)
        print_response_meta(response)
        if response.status_code != 200:
            print(f"body[:4000]: {response.text[:4000]}")
            print(f"elapsed: {time.monotonic() - start:.2f}s")
            return 1
        data = response.json()
        if "error" in data:
            print(f"stream_error: {json.dumps(data['error'], ensure_ascii=False)[:2000]}")
            print("RESULT: API_ERROR")
            return 2
        for choice in data.get("choices", []):
            message = choice.get("message") or {}
            print(f"content_chars: {len(message.get('content') or '')}")
            print(f"finish_reason: {choice.get('finish_reason')}")
        print(f"usage: {json.dumps(data.get('usage'), ensure_ascii=False) if data.get('usage') else None}")
        print(f"elapsed: {time.monotonic() - start:.2f}s")
        print("RESULT: OK")
        return 0
    except httpx.ReadTimeout as error:
        report_exception(error, start=start, first_data_at=None, chunks=0, response=response)
        print("RESULT: READ_TIMEOUT")
        return 3
    except httpx.ReadError as error:
        report_exception(error, start=start, first_data_at=None, chunks=0, response=response)
        print("RESULT: READ_ERROR")
        return 2
    except httpx.HTTPError as error:
        report_exception(error, start=start, first_data_at=None, chunks=0, response=response)
        print("RESULT: HTTP_ERROR")
        return 2
    except Exception as error:
        report_exception(error, start=start, first_data_at=None, chunks=0, response=response)
        print("RESULT: ERROR")
        return 2


def run_request_file(args: argparse.Namespace, api_key: str | None) -> int:
    """Replay an exact chat-completions JSON body captured from http_traces."""
    path = Path(args.request_file)
    if not path.exists():
        print(f"ERROR: request file not found: {path}")
        return 4
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        print(f"ERROR: failed to read request file: {type(error).__name__}: {error}")
        return 4
    if not isinstance(data, dict):
        print("ERROR: request file must contain a JSON object")
        return 4

    if args.override_model:
        data["model"] = args.override_model
    if args.override_max_tokens is not None:
        if "max_completion_tokens" in data:
            data["max_completion_tokens"] = args.override_max_tokens
        if data.get("max_tokens") is not None:
            data["max_tokens"] = args.override_max_tokens
        if "max_completion_tokens" not in data and data.get("max_tokens") is None:
            data["max_completion_tokens"] = args.override_max_tokens
    if args.no_stream:
        data["stream"] = False

    url = build_url(args.base_url, args.chat_path)
    messages = data.get("messages") or []
    tools = data.get("tools") or []
    stream = bool(data.get("stream", True))

    print("=== raw chat-completions replay ===")
    print(f"request_file: {path}")
    print(f"url: {url}")
    print(f"model: {data.get('model')}")
    print(f"stream: {stream}")
    print(f"max_tokens: {data.get('max_tokens')}")
    print(f"max_completion_tokens: {data.get('max_completion_tokens')}")
    print(f"messages: {len(messages)}")
    print(f"tools: {len(tools)}")
    print(f"request_body_bytes: {len(json.dumps(data, ensure_ascii=False).encode('utf-8'))}")
    print(f"timeout_s: {args.timeout}")
    print(f"api_key: {'present' if api_key else 'MISSING'}")

    if args.dry_run:
        print("DRY RUN: no API request sent.")
        return 0
    if not api_key:
        print(
            f"ERROR: no API key. Set {args.api_key_env} in the environment, "
            "pass --env-file, or pass --api-key.",
        )
        return 4

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if stream else "application/json",
        "User-Agent": "lc-agent-raw-context-probe/1.0",
    }
    timeout = httpx.Timeout(
        connect=min(30.0, args.timeout),
        read=args.timeout,
        write=args.timeout,
        pool=min(30.0, args.timeout),
    )
    with httpx.Client(timeout=timeout, trust_env=not args.no_proxy) as client:
        if stream:
            return run_stream(client, url, headers, data)
        return run_non_stream(client, url, headers, data)


def main() -> int:
    args = parse_args()
    env_values = load_env_values(args)
    api_key = resolve_api_key(args, env_values)

    if args.request_file:
        return run_request_file(args, api_key)

    if args.tool_call:
        instruction = args.instruction or TOOL_INSTRUCTION
    elif args.long_output:
        instruction = args.instruction or LONG_INSTRUCTION
    else:
        instruction = args.instruction or FINAL_INSTRUCTION

    messages, estimated_tokens = build_messages(
        args.target_tokens,
        args.system_tokens,
        instruction,
    )
    prompt_chars = sum(len(message["content"]) for message in messages)
    prompt_bytes = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
    url = build_url(args.base_url, args.chat_path)

    print("=== raw chat-completions probe ===")
    print(f"url: {url}")
    print(f"model: {args.model}")
    print(f"stream: {not args.no_stream}")
    print(f"target_tokens: {args.target_tokens}")
    print(f"system_tokens: {args.system_tokens}")
    print(f"long_output: {args.long_output}")
    print(f"tool_call: {args.tool_call}")
    print(f"estimated_prompt_tokens: {estimated_tokens} (cl100k_base)")
    print(f"prompt_chars: {prompt_chars}")
    print(f"prompt_body_bytes: {prompt_bytes}")
    print(f"max_output_tokens: {args.max_tokens}")
    print(f"timeout_s: {args.timeout}")
    print(f"proxy_env: {', '.join(proxy_env_names()) or 'none'}")
    print(f"no_proxy: {args.no_proxy}")
    print(f"api_key: {'present' if api_key else 'MISSING'}")

    if args.dry_run:
        print("DRY RUN: no API request sent.")
        return 0
    if not api_key:
        print(
            f"ERROR: no API key. Set {args.api_key_env} in the environment, "
            "pass --env-file, or pass --api-key.",
        )
        return 4

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json" if args.no_stream else "text/event-stream",
        "User-Agent": "lc-agent-raw-context-probe/1.0",
    }
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": messages,
        "max_tokens": args.max_tokens,
        "temperature": 0,
        "stream": not args.no_stream,
    }
    if args.include_usage and not args.no_stream:
        payload["stream_options"] = {"include_usage": True}
    if args.tool_call:
        payload["tools"] = TOOL_SCHEMA

    timeout = httpx.Timeout(
        connect=min(30.0, args.timeout),
        read=args.timeout,
        write=args.timeout,
        pool=min(30.0, args.timeout),
    )
    with httpx.Client(timeout=timeout, trust_env=not args.no_proxy) as client:
        if args.no_stream:
            return run_non_stream(client, url, headers, payload)
        return run_stream(client, url, headers, payload)


if __name__ == "__main__":
    sys.exit(main())
