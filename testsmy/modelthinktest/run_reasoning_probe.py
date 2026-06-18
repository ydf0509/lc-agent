from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import requests


DEFAULT_URL = "http://localhost:4000/v1/chat/completions"

MODELS = [
    "ds-deepseek-v4-flash",
    "ark-doubao-seed-2.0-pro",
    "ark-minimax-m2.7",
    "ark-glm-5.1",
    "ark-kimi-k2.6",
    "ark-deepseek-v4-flash",
]

DEFAULT_PROMPT = (
    "请解决一个需要推理的小问题：9.11 和 9.8 哪个数字更大？"
    "请给出简短推理和最终答案。"
)


@dataclass
class ProbeResult:
    model: str
    ok: bool
    status_code: int | None
    reasoning: str
    answer: str
    error: str = ""

    @property
    def has_reasoning(self) -> bool:
        return bool(self.reasoning.strip())

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "ok": self.ok,
            "status_code": self.status_code,
            "has_reasoning": self.has_reasoning,
            "reasoning_chars": len(self.reasoning),
            "answer_chars": len(self.answer),
            "reasoning_preview": preview(self.reasoning),
            "answer_preview": preview(self.answer),
            "error": self.error,
        }


def build_payload(model: str, *, stream: bool = True, prompt: str = DEFAULT_PROMPT) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    if stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


def request_headers() -> dict[str, str]:
    # The local gateway in this test does not require an API key.
    return {
        "Content-Type": "application/json",
        "Accept": "text/event-stream, application/json",
    }


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(normalize_text(item.get("text") or item.get("content")))
            else:
                parts.append(normalize_text(item))
        return "".join(parts)
    return json.dumps(value, ensure_ascii=False)


def first_field(data: Any, field_names: set[str]) -> str:
    if isinstance(data, dict):
        for name in field_names:
            text = normalize_text(data.get(name))
            if text:
                return text
        for key in ("delta", "message", "choice"):
            text = first_field(data.get(key), field_names)
            if text:
                return text
        for choice in data.get("choices") or []:
            text = first_field(choice, field_names)
            if text:
                return text
    elif isinstance(data, list):
        for item in data:
            text = first_field(item, field_names)
            if text:
                return text
    return ""


def extract_reasoning(data: dict[str, Any]) -> str:
    return first_field(data, {"reasoning_content", "reasoning"})


def extract_answer(data: dict[str, Any]) -> str:
    return first_field(data, {"content"})


def iter_sse_json_lines(response: requests.Response) -> Iterable[dict[str, Any]]:
    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        line = raw_line.strip()
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line or line == "[DONE]":
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            yield {"_raw": line}


def probe_stream(url: str, model: str, *, prompt: str, timeout: float) -> ProbeResult:
    try:
        with requests.post(
            url,
            headers=request_headers(),
            json=build_payload(model, stream=True, prompt=prompt),
            stream=True,
            timeout=timeout,
        ) as response:
            reasoning_parts: list[str] = []
            answer_parts: list[str] = []
            if response.status_code >= 400:
                return ProbeResult(
                    model=model,
                    ok=False,
                    status_code=response.status_code,
                    reasoning="",
                    answer=response.text,
                    error=f"HTTP {response.status_code}",
                )
            for chunk in iter_sse_json_lines(response):
                reasoning = extract_reasoning(chunk)
                answer = extract_answer(chunk)
                if reasoning:
                    reasoning_parts.append(reasoning)
                if answer:
                    answer_parts.append(answer)
            return ProbeResult(
                model=model,
                ok=True,
                status_code=response.status_code,
                reasoning="".join(reasoning_parts),
                answer="".join(answer_parts),
            )
    except requests.RequestException as exc:
        return ProbeResult(model=model, ok=False, status_code=None, reasoning="", answer="", error=str(exc))


def probe_non_stream(url: str, model: str, *, prompt: str, timeout: float) -> ProbeResult:
    try:
        response = requests.post(
            url,
            headers=request_headers(),
            json=build_payload(model, stream=False, prompt=prompt),
            timeout=timeout,
        )
        if response.status_code >= 400:
            return ProbeResult(
                model=model,
                ok=False,
                status_code=response.status_code,
                reasoning="",
                answer=response.text,
                error=f"HTTP {response.status_code}",
            )
        data = response.json()
        return ProbeResult(
            model=model,
            ok=True,
            status_code=response.status_code,
            reasoning=extract_reasoning(data),
            answer=extract_answer(data),
        )
    except (requests.RequestException, json.JSONDecodeError) as exc:
        return ProbeResult(model=model, ok=False, status_code=None, reasoning="", answer="", error=str(exc))


def probe_model(url: str, model: str, *, prompt: str, stream: bool, timeout: float) -> ProbeResult:
    if stream:
        return probe_stream(url, model, prompt=prompt, timeout=timeout)
    return probe_non_stream(url, model, prompt=prompt, timeout=timeout)


def preview(text: str, limit: int = 160) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def write_report(results: list[ProbeResult], report_path: Path | None) -> None:
    if report_path is None:
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps([result.as_dict() for result in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def print_result(result: ProbeResult) -> None:
    mark = "YES" if result.has_reasoning else "NO"
    print(f"\n=== {result.model} ===")
    print(f"ok: {result.ok}  status: {result.status_code}  reasoning: {mark}")
    if result.error:
        print(f"error: {result.error}")
    print(f"reasoning_chars: {len(result.reasoning)}")
    if result.reasoning:
        print(f"reasoning_preview: {preview(result.reasoning, 300)}")
    print(f"answer_chars: {len(result.answer)}")
    if result.answer:
        print(f"answer_preview: {preview(result.answer, 300)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe local OpenAI-compatible models for reasoning content.")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"Chat completions URL. Default: {DEFAULT_URL}")
    parser.add_argument("--model", action="append", choices=MODELS, help="Model to test. Repeatable. Defaults to all.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt used for all model probes.")
    parser.add_argument("--timeout", type=float, default=120.0, help="Request timeout in seconds.")
    parser.add_argument("--no-stream", action="store_true", help="Use non-stream response mode.")
    parser.add_argument("--report", type=Path, default=Path("reasoning_probe_report.json"), help="JSON report path.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    models = args.model or MODELS
    results = [
        probe_model(args.url, model, prompt=args.prompt, stream=not args.no_stream, timeout=args.timeout)
        for model in models
    ]

    for result in results:
        print_result(result)
    write_report(results, args.report)

    without_reasoning = [result.model for result in results if result.ok and not result.has_reasoning]
    failed = [result.model for result in results if not result.ok]
    print("\n=== summary ===")
    print(f"models: {len(results)}")
    print(f"with_reasoning: {sum(result.has_reasoning for result in results)}")
    print(f"without_reasoning: {without_reasoning}")
    print(f"failed: {failed}")
    print(f"report: {args.report}")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
