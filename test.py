import asyncio
import random
import csv
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
import uvicorn

# ==== 設定區 ====
PROXY_LIST = [
    None,  # 本地 IP
    # "http://user:pass@ip:port"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 (KHTML, like Gecko) Safari/605.1.15"
]

CSV_FILE = "data/ctee_news.csv"
semaphore = asyncio.Semaphore(1)

app = FastAPI()

# 隨機延遲
async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

# 模擬人類互動：滑鼠移動、滾動、點擊
async def random_human_actions(page):
    for _ in range(random.randint(2, 4)):
        await page.mouse.move(random.randint(100, 800), random.randint(100, 600), steps=random.randint(10, 30))
        await page.mouse.wheel(0, random.randint(300, 1200))
        await page.mouse.click(random.randint(100, 800), random.randint(100, 600))
        await human_delay(1, 3)

# 爬新聞主函數
async def scrape_ctee_news(limit: int = 10):
    async with async_playwright() as p:
        proxy = random.choice(PROXY_LIST)
        ua = random.choice(USER_AGENTS)
        browser_args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]

        browser = await p.chromium.launch(
            headless=False,
            args=browser_args,
            proxy={"server": proxy} if proxy else None
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=ua,
            locale="zh-TW",
            geolocation={"longitude": 121.5654, "latitude": 25.0330},
            permissions=["geolocation"],
        )

        # 隱藏 webdriver 特徵
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-TW','zh','en']});
        """)

        page = await context.new_page()
        page.set_default_navigation_timeout(120000)
        page.set_default_timeout(120000)

        await page.set_extra_http_headers({
            "Referer": "https://www.google.com/",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "DNT": "1",
        })

        # === 列表頁 ===
        await page.goto("https://www.ctee.com.tw/world", timeout=120000, wait_until="load")
        await human_delay(5, 10)
        await random_human_actions(page)

        for _ in range(6):
            await page.mouse.wheel(0, random.randint(500, 1500))
            await human_delay(2, 4)

        links = await page.query_selector_all("h3 a, .title a")
        news_urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href and "/news/" in href:
                if not href.startswith("http"):
                    href = "https://www.ctee.com.tw" + href
                if href not in news_urls:
                    news_urls.append(href)

        news_urls = news_urls[:limit]
        results = []

        # === 逐篇抓新聞 ===
        for news_url in news_urls:
            await page.goto(news_url, timeout=120000, wait_until="load")
            await human_delay(5, 15)
            await random_human_actions(page)

            try:
                title = await page.inner_text("h1")
            except:
                title = ""

            try:
                publish_elements = await page.query_selector_all("li.publish-date, li.publish-time")
                publish_time_list = [await el.inner_text() for el in publish_elements]
                publish_time = " | ".join(publish_time_list)
            except:
                publish_time = ""

            try:
                paragraphs = await page.query_selector_all("div.article-content p, .article p")
                content = [(await p.inner_text()).strip() for p in paragraphs if (await p.inner_text()).strip()]
                full_content = "\n".join(content)
            except:
                full_content = ""

            results.append({
                "title": title,
                "publish_time": publish_time,
                "url": news_url,
                "content": full_content
            })

            await human_delay(5, 10)

        await browser.close()

        # === CSV ===
        os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
        with open(CSV_FILE, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["標題","時間","連結","內文"])
            for item in results:
                writer.writerow([item["title"], item["publish_time"], item["url"], item["content"]])

        return results

# FastAPI
@app.get("/")
async def root():
    return {"message": "CTEE 爬新聞 API 已啟動，請使用 /scrape?limit=數量 呼叫"}

@app.get("/scrape")
async def scrape_api(limit: int = 3):
    async with semaphore:  # 限制同時只有一個抓取任務
        try:
            news_data = await scrape_ctee_news(limit)
            return JSONResponse(content={"status": "success", "data": news_data})
        except Exception as e:
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
