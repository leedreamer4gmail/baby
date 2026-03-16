'import urllib.request
import urllib.error
import sys

def call_home():
    try:
        req = urllib.request.Request(
            "http://213.210.5.226:80",
            headers={"User-Agent": "baby-remote-base/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print("call_home_success status:", resp.status)
            print("call_home_success ip_reached: 213.210.5.226")
    except Exception as e:
        print("call_home_failed:", str(e))

print("alive from remote base")
call_home()
print("remote base init complete")'