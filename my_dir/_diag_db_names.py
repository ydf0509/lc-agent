"""临时诊断：流式扫描 bfzs checkpoint 库里的工具名变体。用后删除。"""
import re
from collections import Counter
from pathlib import Path

db = Path(r"D:\codes\lc-agent-bfzs\bfzs_checkpoints.db")
pattern = re.compile(rb"mcp__[A-Za-z0-9_\-]*docs[A-Za-z0-9_\-]*langchain[A-Za-z0-9_\-]*")

counts: Counter = Counter()
tail = b""
chunk_size = 64 * 1024 * 1024
with db.open("rb") as f:
    while True:
        chunk = f.read(chunk_size)
        if not chunk:
            break
        buf = tail + chunk
        for m in pattern.findall(buf):
            counts[m] += 1
        tail = buf[-120:]

for name, cnt in counts.most_common():
    print(cnt, name.decode())
print("total matches:", sum(counts.values()))
