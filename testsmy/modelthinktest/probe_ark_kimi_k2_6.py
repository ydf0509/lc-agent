from run_reasoning_probe import DEFAULT_URL, probe_model, print_result


if __name__ == "__main__":
    result = probe_model(
        DEFAULT_URL,
        "ark-kimi-k2.6",
        prompt="请进行简短推理后回答：9.11 和 9.8 哪个数字更大？",
        stream=True,
        timeout=120.0,
    )
    print_result(result)
    raise SystemExit(0 if result.ok else 2)
