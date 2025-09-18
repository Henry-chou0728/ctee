import asyncio
import random
import csv
from playwright.async_api import async_playwright

PROXY_SERVER = None  # 代理設定

async def human_delay(min_sec=2, max_sec=5):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def main():
    async with async_playwright() as p:
        browser_args = [
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
        ]
        if PROXY_SERVER:
            browser = await p.chromium.launch(headless=False, args=browser_args,
                                              proxy={"server": PROXY_SERVER})
        else:
            browser = await p.chromium.launch(headless=False, args=browser_args)

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        await page.goto("https://www.ctee.com.tw/world", timeout=60000)

        await human_delay(3, 6)

        for _ in range(random.randint(2, 5)):
            await page.mouse.wheel(0, random.randint(500, 1500))
            await human_delay(1, 3)

        links = await page.query_selector_all("h3 a")
        news_urls = []
        for link in links:
            href = await link.get_attribute("href")
            if href and "/news/" in href:
                if not href.startswith("http"):
                    href = "https://www.ctee.com.tw" + href
                news_urls.append(href)

        news_urls = news_urls[:10]  # 限制只爬前20則
        print(f" 找到 {len(news_urls)}")

        # 開啟 CSV 檔案準備寫入
        with open("ctee_news.csv", mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["標題", "時間", "聯結", "內文"])  # 寫入標題欄

            for idx, news_url in enumerate(news_urls, start=1):
                print(f"\n 正在處理第 {idx} 則新聞：{news_url}")

                await page.goto(news_url, timeout=60000)
                await human_delay(2, 5)

                await page.mouse.wheel(0, random.randint(500, 1500))
                await human_delay(1, 3)

                try:
                    title = await page.inner_text("h1")
                except:
                    title = ""

                try:
                    # 抓所有符合的元素
                    publish_elements = await page.query_selector_all("li.publish-date, li.publish-time")
                    # 把每個元素的文字抓下來並去掉多餘空白
                    publish_time_list = [await el.inner_text() for el in publish_elements]
                    # 用空格或其他符號連起來
                    publish_time = " | ".join(publish_time_list)
                except:
                    publish_time = ""

                paragraphs = await page.query_selector_all('p[style="font-size: 100%;"]')
                content = []
                for p_tag in paragraphs:
                    text = (await p_tag.inner_text()).strip()
                    if text:
                        content.append(text)
                full_content = "\n".join(content)

                print(f"- 標題: {title}")
                print(f"- 時間: {publish_time}")
                print(f"- 網頁連結 {news_url}")
                print(f"- 內文前100字:\n{full_content[:100]}...")

                # 寫入 CSV
                writer.writerow([title, publish_time, news_url, full_content])

                await human_delay(2, 5)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
