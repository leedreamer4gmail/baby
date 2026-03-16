'import urllib.request
def call_home():
    try:
        req = urllib.request.Request("http://httpbin.org/get?callhome=baby_v109", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(resp.getcode())
    except Exception as e:
        print(str(e))
call_home()'