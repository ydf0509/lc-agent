# Model Thinking Probe

These scripts call the local OpenAI-compatible endpoint with `requests` and check whether each model returns `reasoning_content` or `reasoning`.

Endpoint:

```text
http://localhost:4000/v1/chat/completions
```

Run all models:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe D:\codes\lc-agent\testsmy\modelthinktest\run_reasoning_probe.py
```

Run one model:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe D:\codes\lc-agent\testsmy\modelthinktest\run_reasoning_probe.py --model ark-glm-5.1
```

Or use the per-model wrappers such as:

```powershell
D:\ProgramData\Miniconda3\envs\py312\python.exe D:\codes\lc-agent\testsmy\modelthinktest\probe_ark_glm_5_1.py
```

The scripts do not send an API key or Authorization header.
