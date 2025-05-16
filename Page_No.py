import os
import sys
import time
import requests
from urllib.parse import urlparse, urlunparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# ----------- 配置 ------------
STEAM_ID = 'XXXXXXXXXXXXXXX'
DOWNLOAD_DIR = 'steam_screenshots'
LOG_FILE = '1_300log.txt'
OUTPUT_FILE = '1_300output.txt'

CHROME_BINARY = r"C:\chrome-win64\chrome-win64\chrome.exe"
CHROME_DRIVER = r"C:\chromeDriver\chromedriver.exe"
USER_DATA_DIR = r'C:\Users\XXX\AppData\Local\Google\Chrome for Testing\User Data'
PROFILE_DIR = 'Default' 

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ----------- 输出日志到 log.txt ------------
class Logger(object):
    def __init__(self, filename=LOG_FILE):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        pass

sys.stdout = Logger()

# ----------- 初始化 Chrome 浏览器 ------------
def init_driver():
    options = Options()
    options.binary_location = CHROME_BINARY
    options.add_argument(f'--user-data-dir={USER_DATA_DIR}')
    options.add_argument(f'--profile-directory={PROFILE_DIR}')
    options.add_argument('--log-level=3')
    service = Service(CHROME_DRIVER)
    return webdriver.Chrome(service=service, options=options)

# ----------- 获取截图详情页链接 ------------
def get_screenshot_page_links(driver, page=1):
    url = f'https://steamcommunity.com/profiles/{STEAM_ID}/screenshots/?p={page}&sort=oldestfirst&browsefilter=myfiles&view=grid&privacy=30'
    for attempt in range(6):
        print(f"\nLoading screenshot grid page: {url} (attempt {attempt + 1})")
        driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        thumbs = soup.select('a[href*="/sharedfiles/filedetails/"]')
        links = [a['href'] for a in thumbs if a.get('href')]

        if links:
            print(f"Found {len(links)} screenshot detail links")
            return links
        else:
            print("No screenshot links found, refreshing...")
    print("Failed to load screenshot links after 3 attempts")
    return []

# ----------- 获取高清图片链接 ------------
def get_full_image_url(driver, detail_url):
    for attempt in range(6):
        print(f"Opening detail page: {detail_url} (attempt {attempt + 1})")
        try:
            driver.get(detail_url)
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            img_tag = soup.select_one('img[src*=".steamusercontent.com/ugc/"]')
            if img_tag and img_tag['src']:
                full_url = img_tag['src']
                # 去掉查询参数
                parsed = urlparse(full_url)
                clean_url = urlunparse(parsed._replace(query=''))
                return clean_url
            else:
                print("Image not found, refreshing...")
        except Exception as e:
            print(f"Error loading detail page: {e}")
    print(" Failed to load image after 3 attempts")
    return None

# ----------- 下载图片 ------------
def download_image(url, page, index, retries=3):
    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            ext = response.headers.get("Content-Type", "").split("/")[-1]
            if ext not in ["jpeg", "jpg", "png", "jfif"]:
                ext = "jpg"

            # 使用页码和图片索引生成文件名
            filename = f"Page{page}_No{index + 1:02d}.{ext}"
            filepath = os.path.join(DOWNLOAD_DIR, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)

            print(f"[Saved] {filename}")
            return
        except Exception as e:
            print(f"[Retry {attempt + 1}] Error downloading {url} - {e}")
            time.sleep(2)
    print(f"[Fail] Gave up on {url}")

# ----------- 保存图片链接 ------------
def write_image_urls_to_file(image_urls):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in image_urls:
            f.write(url + "\n")
    print(f"\n Image URLs have been written to {OUTPUT_FILE}")

# ----------- 主程序入口 ------------
def main():
    driver = init_driver()
    image_urls = []

    for page in range(1, 300):  # 可改为 range(1, N) 支持多页
        links = get_screenshot_page_links(driver, page)
        if not links:
            break

        for idx, link in enumerate(links):
            print(f"\nProcessing: {link}")
            img_url = get_full_image_url(driver, link)
            if img_url:
                image_urls.append(img_url)
                print(f"[OK] {img_url}")
                download_image(img_url, page, idx)  # 传入页码和索引
            else:
                print(" Failed to extract image")

    driver.quit()

    if image_urls:
        write_image_urls_to_file(image_urls)
    else:
        print("No image URLs found.")

    print("\n All done.")

if __name__ == "__main__":
    main()
