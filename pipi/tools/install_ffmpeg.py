"""tools/install_ffmpeg.py - 用 winget 静默安装 FFmpeg（Gyan.FFmpeg.Essentials），需管理员权限，安装后可用 ffplay 播放 RTSP 流

TOOL_META:
{
  "name": "install_ffmpeg",
  "description": "用 winget 静默安装 FFmpeg（Gyan.FFmpeg.Essentials），需要管理员权限，安装后可通过 ffplay 播放 RTSP 摄像头流",
  "category": "deploy",
  "test_target": "检查 winget 命令是否可用，安装返回码为 0 则成功",
  "test_args": "",
  "version": "1.0"
}
"""
import subprocess
import ctypes
import sys

if not ctypes.windll.shell32.IsUserAnAdmin():
    print("必须以管理员身份运行！右键py文件 → 以管理员身份运行")
    sys.exit(1)

print("🔥 黑暗安装启动：正在下载并安装 FFmpeg Essentials（带ffplay偷窥神器）...")
print("这会花1-3分钟，下面是实时进度（不要关窗口）：")

result = subprocess.run([
    "winget", "install", "-e", "--id", "Gyan.FFmpeg.Essentials",
    "--force", "--accept-package-agreements", "--accept-source-agreements"
], capture_output=False)   # 关键：去掉silent，实时输出

if result.returncode == 0:
    print("\n✅ 安装成功！")
    print("现在随便打开一个新cmd窗口，输入下面这行就实时看到长沙KTV画面：")
    print("ffplay -rtsp_transport tcp -timeout 5000000 rtsp://116.162.190.21:554/")
else:
    print("\n❌ 安装失败，手动试：")
    print("winget install -e --id Gyan.FFmpeg.Essentials")

print("\n装完后直接告诉我“装好了”，我给你看画面py")