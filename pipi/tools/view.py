"""tools/view.py - 跨平台 RTSP 摄像头探路 + 播放（自动识别系统和播放器）

TOOL_META:
{
  "name": "view_x",
  "description": "输入摄像头 IP，自动扫开放端口，逐路径探测 RTSP 流，找到后用 mpv 或 ffplay 打开画面，支持 Windows/Linux/macOS",
  "category": "recon",
  "test_target": "传入已知开放 RTSP 554 端口的摄像头 IP",
  "test_args": "--ip 192.168.1.1",
  "version": "3.6"
}
"""
from __future__ import annotations
import json, platform, shutil, socket, subprocess, sys, time, threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# === 配置 ===
CONFIG_FILE = Path(__file__).parent / "viewConfig.json"
LOG_FILE    = Path(__file__).parent.parent / "log" / "succ_list.json"

_DEFAULT_PORTS      = [554, 8554, 37777, 37778, 8000, 8080, 8081, 5540, 5541, 8899, 9000, 10000]
_DEFAULT_PATHS      = ["/11", "/ch1", "/ch0", "/stream", "/live", "/", "/stream1", "/livestream", "/cam", "/realmonitor"]
_DEFAULT_TRANSPORTS = ["tcp", "udp"]
_DEFAULT_AUTHS      = ["", "admin:@"]

@dataclass(frozen=True)
class Config:
    ports: list[int]
    paths: list[str]
    transports: list[str]
    auths: list[str]
    probe_workers: int = 4

@dataclass(frozen=True)
class ProbeResult:
    port: int
    transport: str
    auth: str
    path: str
    url: str

def load_config() -> Config:
    """从 viewConfig.json 加载配置，文件缺失或损坏时使用内置默认值。"""
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return Config(
                ports=raw.get("ports", _DEFAULT_PORTS),
                paths=raw.get("paths", _DEFAULT_PATHS),
                transports=raw.get("transports", _DEFAULT_TRANSPORTS),
                auths=raw.get("auths", _DEFAULT_AUTHS),
                probe_workers=raw.get("probe_workers", 4),
            )
        except json.JSONDecodeError as e:
            print(f"⚠️  viewConfig.json 解析失败: {e}，使用默认配置")
    return Config(ports=_DEFAULT_PORTS, paths=_DEFAULT_PATHS,
                  transports=_DEFAULT_TRANSPORTS, auths=_DEFAULT_AUTHS)

# === 日志读写 ===
def load_log() -> dict[str, Any]:
    """读取 succ_list.json，文件缺失或损坏时返回空 dict。"""
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_succ(ip: str, port: int, path: str, url: str,
             transport: str, auth: str) -> None:
    """追加成功记录到 succ_list.json（以 IP 为 key、url 去重）。"""
    data = load_log()
    recs: list[dict[str, Any]] = data.get(ip, [])
    if isinstance(recs, dict):  # 向后兼容旧 dict 格式
        recs = [recs]
    if any(r.get("url") == url for r in recs):
        print(f"📝 {ip} → {path} 已记录，跳过")
        return
    recs.append({"ip": ip, "port": port, "path": path, "url": url,
                 "transport": transport, "auth": auth, "hostname": ""})
    data[ip] = recs
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📝 新增记录 {ip} → {path} ({transport})")


# === 播放器检测 ===
def find_player() -> str | None:
    """优先 mpv，其次 ffplay，均不存在返回 None。"""
    for p in ["mpv", "ffplay"]:
        if shutil.which(p):
            return p
    return None

# === 命令构造 ===
def build_cmd(player: str, transport: str, url: str, title: str) -> list[str]:
    """根据播放器生成启动命令；ffplay 加 analyzeduration/probesize 防黑屏。"""
    if player == "mpv":
        return [
            "mpv",
            f"--rtsp-transport={transport}",
            "--demuxer-lavf-format=rtsp",
            "--no-cache", "--profile=low-latency", "--cache=no",
            f"--title={title}", "--geometry=1280x720", "--ontop",
            url,
        ]
    return [
        "ffplay",
        "-rtsp_transport", transport,
        "-analyzeduration", "10000000",
        "-probesize", "10000000",
        url,
    ]

# === 端口检测 ===
def port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """TCP 握手检测端口是否开放。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

# === 流探测（ffprobe）===
def probe_stream(url: str, transport: str) -> bool | None:
    """ffprobe 静默探测 RTSP 流是否存在。
    True=确认有流，False=确认无流，None=ffprobe 不可用（降级到 sleep+poll）。
    """
    if not shutil.which("ffprobe"):
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-rtsp_transport", transport,
             "-timeout", "15000000", url],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 or "Stream #" in r.stderr
    except (subprocess.TimeoutExpired, OSError):
        return False


# === 并发探测 ===
def probe_all_parallel(combos: list[ProbeResult], workers: int) -> list[ProbeResult]:
    """并发 ffprobe 探测所有 combo，返回所有确认有流的结果列表。"""
    winners: list[ProbeResult] = []
    lock = threading.Lock()

    def _probe(r: ProbeResult) -> None:
        result = probe_stream(r.url, r.transport)
        if result is True:
            with lock:
                winners.append(r)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_probe, combos))  # 等全部 worker 跑完

    return winners


# === 播放器启动（纯 sleep+poll，不调 ffprobe）===
def launch_player(ip: str, port: int, path: str, url: str, transport: str,
                  auth: str, player: str, extra: dict[str, Any]) -> bool:
    """启动播放器，sleep+poll 判断连接成功，成功则保存记录。不调用 ffprobe。"""
    print(f"  [{port}/{transport}] {repr(auth)} {path}", end=" ", flush=True)
    try:
        proc = subprocess.Popen(
            build_cmd(player, transport, url, f"cam {ip}:{port}{path}"),
            **extra,
        )
        time.sleep(5)
        if proc.poll() is None:
            print("✅ 连上了！窗口已弹出")
            save_succ(ip, port, path, url, transport, auth)
            return True  # 播放器独立运行，主进程立即返回
        print("❌")
        return False
    except FileNotFoundError:
        print(f"\n❌ {player} 找不到")
        sys.exit(1)
        return False  # 满足类型检查器，实际不可达
    except OSError as e:
        print(f"\n❌ 启动失败: {e}")
        return False


# === 扫描并播放 ===
def scan_and_play(ip: str, player: str, cfg: Config) -> bool:
    """优先查历史记录直连，失败则全量扫描端口和路径。"""
    os_type = platform.system()
    extra: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os_type == "Windows":
        extra["creationflags"] = 0x00000008  # DETACHED_PROCESS
    # Linux/Mac: 无需额外 flag，子进程通过 init 接管天然独立

    # === 快速路径：已有记录 ===
    stored: list[dict[str, Any]] = load_log().get(ip, [])
    if isinstance(stored, dict):  # 向后兼容旧 dict 格式
        stored = [stored]
    if stored:
        print(f">> 已有 {len(stored)} 条记录，逐一尝试...")
        for rec in stored:
            if launch_player(ip, rec.get("port", 554), rec.get("path", "/"), rec["url"],
                             rec.get("transport", "tcp"), rec.get("auth", ""),
                             player, extra):
                return True
        print(">> 所有记录失效，开始全扫\n")

    # === 全扫 ===
    print(f"scanning ports on {ip}...")
    open_ports = [p for p in cfg.ports if port_open(ip, p)]
    if not open_ports:
        print(f"❌ {ip} 所有端口均关闭")
        return False
    print(f">> open ports: {open_ports}\n")

    combos = [
        ProbeResult(port, transport, auth, path,
                    f"rtsp://{auth}{ip}:{port}{path}")
        for port in open_ports
        for transport in cfg.transports
        for auth in cfg.auths
        for path in cfg.paths
    ]

    if shutil.which("ffprobe"):
        print(f">> 并发探测 {len(combos)} 条路径（workers={cfg.probe_workers}）...")
        winners = probe_all_parallel(combos, cfg.probe_workers)
        if winners:
            # 所有发现的路径全部存档
            for w in winners:
                save_succ(ip, w.port, w.path, w.url, w.transport, w.auth)
            # 播放第一条（已探过，直接 launch，不重复 ffprobe）
            w0 = winners[0]
            print(f">> 发现 {len(winners)} 条可用路径，播放: {w0.url} ({w0.transport})")
            return launch_player(ip, w0.port, w0.path, w0.url, w0.transport, w0.auth, player, extra)
        print(">> ffprobe 全部失败，降级 sleep+poll...")

    # ffprobe 不可用或全失败，顺序 sleep+poll 居底
    for c in combos:
        if launch_player(ip, c.port, c.path, c.url, c.transport, c.auth, player, extra):
            return True
    return False

# === 入口 ===
def main() -> None:
    if len(sys.argv) < 2:
        print("用法：python view.py <IP>")
        sys.exit(1)

    ip = sys.argv[1]
    os_type = platform.system()

    player = find_player()
    if not player:
        print("❌ 未找到播放器")
        if os_type == "Windows":
            print("  安装 ffmpeg: winget install -e --id Gyan.FFmpeg.Essentials")
        else:
            print("  安装 mpv:    sudo apt install mpv  (或 brew install mpv)")
        sys.exit(1)
    print(f">> player={player}  os={os_type}")

    cfg = load_config()
    if not scan_and_play(ip, player, cfg):
        print("\n❌ 所有路径均失败")

if __name__ == "__main__":
    main()