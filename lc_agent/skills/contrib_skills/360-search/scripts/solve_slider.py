#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""360 牛盾滑块验证码自动求解（配合 agent-browser 使用）。

用法示例:
    python scripts/solve_slider.py --session so360
    python scripts/solve_slider.py --session so360 --url "https://www.so.com/s?q=xxx"
    python scripts/solve_slider.py --session so360 --dry-run

做的事（全部自动完成，不需要 LLM 再写临时脚本）:
1. 读取滑块按钮和拼图块的位置（getBoundingClientRect，自动取整）
2. 导出背景 canvas 和拼图图片
3. 模板匹配算出拼图需要移动的像素（带相关系数校验）
4. 分段拖动滑块（整数坐标、多段、间隔 120ms）
5. 检查是否验证成功，失败自动重试（最多 --max-attempts 次）

输出: JSON 到 stdout。退出码:
    0 = 验证成功（或当前页面本来就不需要验证码）
    3 = 页面上没有拼图（360 加重限流，应立即停止并换引擎）
    1 = 求解失败（已重试到上限）
依赖: requests, pillow, numpy, curl_cffi, agent-browser CLI
"""
import argparse
import base64
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image, ImageFilter

try:
    from curl_cffi import requests as curl_requests
except ImportError:  # pragma: no cover - 依赖缺失时给出明确提示
    curl_requests = None

IMG_UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
}

GET_STATE_JS = (
    "JSON.stringify((()=>{"
    "const btn=document.querySelector('.v-target-btn');"
    "const front=document.querySelector('.v-wrap-img-front');"
    "const bg=document.querySelector('.v-wrap-img-bg');"
    "if(!btn||!front||!bg)return {has_slider:false,url:location.href};"
    "const b=btn.getBoundingClientRect(),f=front.getBoundingClientRect(),c=bg.getBoundingClientRect();"
    "return {has_slider:true,url:location.href,"
    "cx:Math.round(b.x+b.width/2),cy:Math.round(b.y+b.height/2),"
    "frontX:Math.round(f.x),frontW:Math.round(f.width),frontH:Math.round(f.height),"
    "frontSrc:front.src||''}"
    "})())"
)


def _ab_path() -> str:
    """定位 agent-browser CLI（npm 全局安装时是 .cmd 包装）。"""
    found = shutil.which("agent-browser")
    if found:
        return found
    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA") or ""
    for name in ("agent-browser.cmd", "agent-browser"):
        candidate = os.path.join(appdata, "npm", name)
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError("找不到 agent-browser CLI，请先安装：npm i -g agent-browser && agent-browser install")


def ab_run(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    """执行一条 agent-browser 命令。

    输出用临时文件承接而不是管道：会话首次启动时后台 Chrome 会继承并占住管道，
    用管道会导致超时后读取输出时永久阻塞（subprocess.run 内部会 communicate）。
    会话首条命令可能"假挂起"，超时视为已生效，继续后续步骤。
    """
    exe = _ab_path()
    cmd = [exe] + args
    if exe.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c"] + cmd

    with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
        proc = subprocess.Popen(cmd, stdout=out_f, stderr=err_f, stdin=subprocess.DEVNULL)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        out_f.seek(0)
        err_f.seek(0)
        stdout = out_f.read().decode("utf-8", errors="replace")
        stderr = err_f.read().decode("utf-8", errors="replace")
    return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)


def ab_eval(session: str, js: str, timeout: float = 30):
    """执行 eval 并解析出 Python 对象（agent-browser 会把结果再 JSON 编码一次）。"""
    # agent-browser 的 eval 只接受单行 JS：多行会静默返回 null，这里统一压平
    js = " ".join(js.splitlines())
    proc = ab_run(["--session", session, "eval", js], timeout=timeout)
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    try:
        outer = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end < 0:
            return None
        try:
            outer = json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    if isinstance(outer, str):
        # agent-browser 会把结果再 JSON 编码一次；只有看起来像 JSON 的才二次解析
        candidate = outer.strip()
        if candidate.startswith(("{", "[")):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return outer
        return outer
    return outer


def _load_image_from_dataurl(data_url: str) -> Image.Image:
    _, _, b64 = data_url.partition(",")
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


def _download_image(url: str) -> Image.Image:
    headers = dict(IMG_UA)
    if curl_requests is not None:
        resp = curl_requests.get(url, impersonate="chrome", headers=headers, timeout=15)
    else:
        import requests as plain_requests
        resp = plain_requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return Image.open(io.BytesIO(resp.content)).convert("RGBA")


def match_offset(bg: Image.Image, front: Image.Image, display_w: int, display_h: int,
                 rgb_threshold: float) -> tuple[int, float, str]:
    """定位缺口，返回 (水平位移 dx, 置信度, 方法)。

    两种方法，优先用边缘匹配（对颜色不敏感——拼图块和缺口可能是亮/暗任意组合）：
    - edge：把拼图块的轮廓叠到背景的梯度图上，取梯度响应最高的位置；用"峰值/均值"比值判断可靠性
    - rgb ：整块像素做归一化相关，仅在边缘匹配不可靠时兜底

    dx 均为整数像素（滑块与拼图是 1:1 线性映射）。
    """
    front = front.resize((display_w, display_h), Image.LANCZOS)
    fa = np.asarray(front).astype(np.float32)
    mask = fa[:, :, 3] > 128
    if not mask.any():
        return 0, 0.0, "empty"

    bg_arr = np.asarray(bg).astype(np.float32)
    h, w = bg_arr.shape[:2]

    # --- 边缘匹配：拼图轮廓 vs 背景梯度 ---
    gray = np.asarray(bg.convert("L")).astype(np.float32)
    gy, gx = np.gradient(gray)
    grad = np.hypot(gx, gy)
    grad = grad / (grad.max() + 1e-6)

    mask_img = Image.fromarray((mask * 255).astype(np.uint8))
    eroded = np.asarray(mask_img.filter(ImageFilter.MinFilter(5))) > 128
    boundary = mask & ~eroded
    bys, bxs = np.where(boundary)

    edge_best, edge_dx = -1.0, 0
    edge_sum = 0.0
    edge_n = 0
    if len(bys):
        for dx in range(0, max(1, w - display_w + 1)):
            sx = np.clip(bxs + dx, 0, w - 1)
            score = float(grad[bys, sx].mean())
            edge_sum += score
            edge_n += 1
            if score > edge_best:
                edge_best, edge_dx = score, dx
    edge_mean = edge_sum / edge_n if edge_n else 0.0
    edge_ratio = edge_best / edge_mean if edge_mean > 0 else 0.0

    # --- RGB 匹配（兜底） ---
    patch = fa[:, :, :3][mask]
    patch_c = patch - patch.mean()
    patch_n = float(np.sqrt((patch_c ** 2).sum()))
    rgb_best, rgb_dx = -1.0, 0
    for dx in range(0, max(1, w - display_w + 1)):
        region = bg_arr[:h, dx:dx + display_w][mask]
        if region.shape != patch.shape:
            continue
        region_c = region - region.mean()
        den = patch_n * float(np.sqrt((region_c ** 2).sum()))
        if den <= 0:
            continue
        corr = float((patch_c * region_c).sum() / den)
        if corr > rgb_best:
            rgb_best, rgb_dx = corr, dx

    # 边缘峰值显著（峰值/均值 >= 1.5）即采信；否则退回 RGB
    if edge_ratio >= 1.5:
        return edge_dx, round(edge_ratio, 2), "edge"
    if rgb_best >= rgb_threshold:
        return rgb_dx, round(rgb_best, 2), "rgb"
    # 两者都不可靠：用边缘结果，但把低置信度如实报告
    return edge_dx, round(edge_ratio, 2), "edge_low_conf"


def refresh_puzzle(session: str) -> None:
    """点击验证码右上/右下角的刷新按钮，换一张新拼图。"""
    ab_run(["--session", session, "click", ".verify-refresh"], timeout=15)
    time.sleep(1.2)


def drag_slider(session: str, cx: int, cy: int, distance: int, steps: int = 8, delay: float = 0.12) -> None:
    """整数坐标分段拖动：按下 → 多段移动 → 松手。"""
    ab_run(["--session", session, "mouse", "move", str(cx), str(cy)], timeout=20)
    ab_run(["--session", session, "mouse", "down"], timeout=20)
    for i in range(1, steps + 1):
        x = cx + int(round(distance * i / steps))
        ab_run(["--session", session, "mouse", "move", str(x), str(cy)], timeout=20)
        time.sleep(delay)
    ab_run(["--session", session, "mouse", "up"], timeout=20)


def current_url(session: str) -> str:
    proc = ab_run(["--session", session, "get", "url"], timeout=20)
    return (proc.stdout or "").strip().splitlines()[-1].strip() if proc.stdout else ""


def solve(session: str, url: str | None, max_attempts: int, threshold: float,
          dry_run: bool, steps: int) -> dict:
    if url:
        # 首条命令可能"假挂起"，超时即视为已启动
        ab_run(["--session", session, "--headed", "open", url], timeout=20)
        ab_run(["--session", session, "wait", "--load", "networkidle"], timeout=25)
        time.sleep(2)

    attempts = []
    for attempt in range(1, max_attempts + 1):
        state = ab_eval(session, GET_STATE_JS)
        if not state:
            return {"success": False, "reason": "eval_failed", "attempts": attempts}

        if not state.get("has_slider"):
            # 没有滑块 → 要么本来就不需要验证，要么是"网络或服务器异常"页
            page_url = state.get("url", "")
            if "qcaptcha" not in page_url:
                return {"success": True, "reason": "no_captcha", "final_url": page_url, "attempts": attempts}
            return {"success": False, "reason": "no_puzzle", "final_url": page_url, "attempts": attempts}

        front_src = state.get("frontSrc", "")
        if not front_src or front_src.endswith("/undefined"):
            return {"success": False, "reason": "no_puzzle_image",
                    "final_url": state.get("url", ""), "attempts": attempts}

        data_url = ab_eval(session, "document.querySelector('.v-wrap-img-bg').toDataURL('image/png')", timeout=30)
        if not isinstance(data_url, str) or "," not in data_url:
            return {"success": False, "reason": "bg_export_failed", "attempts": attempts}

        bg_img = _load_image_from_dataurl(data_url)
        front_img = _download_image(front_src)
        dx, confidence, method = match_offset(
            bg_img, front_img, int(state["frontW"]), int(state["frontH"]), threshold
        )

        rec = {"attempt": attempt, "drag_px": dx, "confidence": confidence, "method": method}
        attempts.append(rec)

        if method == "edge_low_conf":
            rec["note"] = "边缘匹配置信度不足，结果可能不准（可在浏览器里肉眼核对缺口）"

        if dry_run:
            return {"success": False, "reason": "dry_run", "drag_px": dx,
                    "confidence": confidence, "method": method, "attempts": attempts}

        drag_slider(session, int(state["cx"]), int(state["cy"]), dx, steps=steps)
        time.sleep(2.5)

        page_url = current_url(session)
        rec["final_url"] = page_url
        if "qcaptcha" not in page_url:
            return {"success": True, "reason": "passed", "drag_px": dx,
                    "confidence": confidence, "method": method,
                    "final_url": page_url, "attempts": attempts}

        # 失败后拼图不一定自动刷新，主动点一次刷新按钮换新图再重试
        refresh_puzzle(session)

    return {"success": False, "reason": "max_attempts_reached",
            "final_url": current_url(session), "attempts": attempts}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="360 牛盾滑块验证码自动求解（配合 agent-browser）"
    )
    parser.add_argument("--session", default="so360", help="agent-browser 会话名（默认 so360，务必复用同一会话）")
    parser.add_argument("--url", help="可选：先打开这个搜索页（会触发验证码）")
    parser.add_argument("--max-attempts", type=int, default=3, help="最多尝试次数（默认 3）")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="RGB 兜底匹配的相关系数阈值（默认 0.6；边缘匹配优先，不受此值影响）")
    parser.add_argument("--steps", type=int, default=8, help="拖动分段数（默认 8）")
    parser.add_argument("--dry-run", action="store_true", help="只计算拖动距离，不实际拖动")
    args = parser.parse_args()

    try:
        result = solve(args.session, args.url, max(1, args.max_attempts),
                       args.threshold, args.dry_run, max(2, args.steps))
    except Exception as exc:
        result = {"success": False, "reason": f"error: {type(exc).__name__}: {exc}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("success"):
        sys.exit(0)
    if "no_puzzle" in str(result.get("reason", "")):
        sys.exit(3)
    sys.exit(1)


if __name__ == "__main__":
    main()
