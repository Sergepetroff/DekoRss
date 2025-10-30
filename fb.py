import asyncio
from playwright.async_api import async_playwright
from feedgen.feed import FeedGenerator
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

USERNAME = os.getenv("LJ_USERNAME")
PASSWORD = os.getenv("LJ_PASSWORD")
FACEBOOK_URL = "https://www.facebook.com"
RSS_FILE = "facebook_feed.xml"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto(FACEBOOK_URL)
        
        await page.fill('input[name="email"]', USERNAME)
        await page.fill('input[name="pass"]', PASSWORD)
        await page.click('button[name="login"]')
        await page.wait_for_load_state('networkidle')
        
        await page.goto(FACEBOOK_URL)
        await page.wait_for_selector('div[role="feed"]')
        
        posts = await page.query_selector_all('div[data-pagelet^="FeedUnit_"]')
        
        fg = FeedGenerator()
        fg.title("Facebook Feed")
        fg.link(href=FACEBOOK_URL, rel="self")
        fg.description("Latest posts from Facebook feed")
        
        for post in posts:
            content = await post.inner_text()
            fe = fg.add_entry()
            fe.title("Facebook post")
            fe.description(content[:2000])  # Ограничение длины описания
            fe.pubDate(datetime.now())
            fe.link(href=FACEBOOK_URL)
        
        fg.rss_file(RSS_FILE)
        print(f"RSS файл создан: {RSS_FILE}")
        
        await browser.close()

asyncio.run(run())
