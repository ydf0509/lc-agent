from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "run_reasoning_probe.py"


def load_probe_module():
    spec = importlib.util.spec_from_file_location("run_reasoning_probe", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_script_covers_requested_models_and_endpoint():
    module = load_probe_module()

    assert module.DEFAULT_URL == "http://localhost:4000/v1/chat/completions"
    assert module.MODELS == [
        "ds-deepseek-v4-flash",
        "ark-doubao-seed-2.0-pro",
        "ark-minimax-m2.7",
        "ark-glm-5.1",
        "ark-kimi-k2.6",
        "ark-deepseek-v4-flash",
    ]


def test_payload_uses_openai_chat_completion_shape_without_api_key():
    module = load_probe_module()

    payload = module.build_payload("ark-glm-5.1", stream=True)
    assert payload["model"] == "ark-glm-5.1"
    assert payload["stream"] is True
    assert payload["messages"][0]["role"] == "user"
    assert "推理" in payload["messages"][0]["content"]
    assert "api_key" not in payload


def test_extracts_reasoning_from_stream_and_non_stream_shapes():
    module = load_probe_module()

    stream_chunk = {
        "choices": [
            {
                "delta": {
                    "reasoning_content": "think-a",
                    "content": "answer-a",
                }
            }
        ]
    }
    non_stream_body = {
        "choices": [
            {
                "message": {
                    "reasoning": "think-b",
                    "content": "answer-b",
                }
            }
        ]
    }

    assert module.extract_reasoning(stream_chunk) == "think-a"
    assert module.extract_answer(stream_chunk) == "answer-a"
    assert module.extract_reasoning(non_stream_body) == "think-b"
    assert module.extract_answer(non_stream_body) == "answer-b"
