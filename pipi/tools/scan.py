import socket
import threading
from queue import Queue
import time
import datetime
import sys

print("😈 黑暗扫描器 v5.0 启动 → 实时过程 + 交互模式")

# ================== 选择模式 ==================
print("\n请选择扫描模式：")
print("1. 只扫常见端口（XiongMai专用，27个，超快，推荐！）")
print("2. 扫全端口（1-65535，狠但慢，可能要几分钟）")
choice = input("请输入 1 或 2： ").strip()

if choice == "1":
    ports = [21, 22, 23, 25, 53, 80, 81, 443, 554, 8000, 8080, 8081, 8554, 8888, 8899, 9000,
             37777, 37778, 37779, 4000, 5000, 6000, 7000, 9001, 10000, 10001, 20000]
    mode = "常见端口模式（快速）"
elif choice == "2":
    ports = list(range(1, 65536))
    mode = "全端口模式（狠版）"
    print("⚠️ 全端口模式启动... 这会很慢，建议先试1！")
else:
    print("❌ 输入错误，自动使用模式1")
    ports = [21, 22, 23, 25, 53, 80, 81, 443, 554, 8000, 8080, 8081, 8554, 8888, 8899, 9000,
             37777, 37778, 37779, 4000, 5000, 6000, 7000, 9001, 10000, 10001, 20000]
    mode = "常见端口模式（默认）"

if len(sys.argv) > 1:
    target = sys.argv[1]
else:
    target = input("请输入目标IP（默认42.200.145.92）：").strip() or "42.200.145.92"

threads = 30 if choice == "1" else 100
open_ports = []
queue = Queue()

def scan_port(port):
    print(f"🔍 正在黑暗扫描端口 {port} ...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((target, port))
        if result == 0:
            open_ports.append(port)
            print("🔥 [+] 打开了！")
        else:
            print("❌ 关闭")
        sock.close()
    except:
        print("❌ 关闭（异常）")

def worker():
    while not queue.empty():
        port = queue.get()
        scan_port(port)
        queue.task_done()

# ================== 开始扫描 ==================
print(f"\n😈 {mode} 启动 → 目标 {target}")
start_time = time.time()

for port in ports:
    queue.put(port)

for _ in range(threads):
    t = threading.Thread(target=worker, daemon=True)
    t.start()

queue.join()

# ================== 输出 TXT ==================
filename = f"open_ports_{target}.txt"
with open(filename, "w", encoding="utf-8") as f:
    f.write(f"扫描时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"目标 IP: {target}\n")
    f.write(f"模式: {mode}\n")
    f.write(f"扫描用时: {time.time()-start_time:.1f} 秒\n")
    f.write("="*60 + "\n")
    if open_ports:
        f.write(f"🔓 打开的端口（共 {len(open_ports)} 个）:\n")
        for p in sorted(open_ports):
            f.write(f"  - 端口 {p}\n")
        f.write("\n🚀 建议拉流地址（重点试这些！）:\n")
        for p in sorted(open_ports):
            if p == 80:
                f.write(f"  http://{target}/DVR.htm\n")
                f.write(f"  http://{target}/cgi-bin/mjpg/video.cgi?subtype=1\n")
                f.write(f"  http://{target}/cgi-bin/mjpg/video.cgi?channel=1\n")
            elif p == 81:
                f.write(f"  http://{target}:81/DVR.htm\n")
            elif p == 37777:
                f.write(f"  http://{target}:37777\n")
            elif p == 8000:
                f.write(f"  http://{target}:8000\n")
            elif p == 554:
                f.write(f"  rtsp://admin:@ {target}:554/cam/realmonitor?channel=1&subtype=0\n")
    else:
        f.write("😭 一个都没开！\n")

print(f"\n✅ 扫描结束！结果保存到 {filename}")
print("   用记事本打开就能看全部骚过程 + 拉流地址！")