"""tools/view_x.py - 跨平台 RTSP 摄像头探路 + 播放（自动识别系统和播放器）

TOOL_META:
{
  "name": "view_x",
  "description": "输入摄像头 IP，自动扫开放端口，逐路径探测 RTSP 流，找到后用 mpv 或 ffplay 打开画面，支持 Windows/Linux/macOS",
  "category": "recon",
  "test_target": "传入已知开放 RTSP 554 端口的摄像头 IP",
  "test_args": "--ip 192.168.1.1",
  "version": "2.0"
}
"""
import subprocess
import sys
import time
import socket
import shutil
import platform

if len(sys.argv) < 2:
    print("用法：python view_x.py <IP>")
    sys.exit(1)

ip = sys.argv[1]
OS = platform.system()   # Windows / Linux / Darwin


# ── 自动选播放器：优先 mpv，其次 ffplay ──────────────────
def find_player():
    for p in ["mpv", "ffplay"]:
        if shutil.which(p):
            return p
    return None

player = find_player()
if not player:
    print("❌ 未找到播放器")
    if OS == "Windows":
        print("  安装 ffmpeg: winget install -e --id Gyan.FFmpeg.Essentials")
    else:
        print("  安装 mpv:    sudo apt install mpv  (或 brew install mpv)")
    sys.exit(1)

print(f">> player={player}  os={OS}")


def build_cmd(transport, url, title):
    """根据播放器生成命令，mpv 和 ffplay 参数不同"""
    if player == "mpv":
        return [
            "mpv",
            f"--rtsp-transport={transport}",
            "--demuxer-lavf-format=rtsp",
            "--no-cache", "--profile=low-latency", "--cache=no",
            f"--title={title}", "--geometry=1280x720", "--ontop",
            url,
        ]
    else:  # ffplay：加 analyzeduration/probesize 解决 unspecified pixel format
        return [
            "ffplay",
            "-rtsp_transport", transport,
            "-analyzeduration", "10000000",
            "-probesize", "10000000",
            url,
        ]


def port_open(host, port, timeout=1.0):
    """快速检查端口是否开着，避免对关闭端口浪费 5 秒等待"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


ports = [554, 8554, 5540, 8555, 37777]
transports = ["tcp", "udp"]
auths = ["", "admin:@"]
paths = ["/11", "/ch1", "/ch0", "/stream", "/live", "/",
         "/stream1", "/livestream", "/cam", "/realmonitor"]

print(f"scanning ports on {ip}...")
open_ports = [p for p in ports if port_open(ip, p)]
if not open_ports:
    print(f"❌ {ip} 所有端口均关闭")
    sys.exit(1)
print(f">> open ports: {open_ports}\n")

found = False
for port in open_ports:
    for transport in transports:
        for auth in auths:
            for p in paths:
                url = (f"rtsp://{auth}{ip}:{port}{p}" if auth
                       else f"rtsp://{ip}:{port}{p}")
                print(f"try {url} ({transport})", end=" ", flush=True)
                try:
                    proc = subprocess.Popen(
                        build_cmd(transport, url, f"cam {ip}:{port}{p}"),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    time.sleep(5)
                    if proc.poll() is None:
                        print("✅ 连上了！按 q 退出")
                        found = True
                        proc.wait()
                        break
                    else:
                        print("❌")
                except FileNotFoundError:
                    print(f"\n❌ {player} 找不到")
                    sys.exit(1)
            if found:
                break
        if found:
            break
    if found:
        break

if not found:
    print("\n❌ 所有路径均失败")