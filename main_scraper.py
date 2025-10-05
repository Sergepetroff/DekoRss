import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from email.utils import format_datetime

LOGIN_URL = "https://www.livejournal.com/login.bml"
LJ_URL = "https://dekodeko.livejournal.com"
RSS_FILENAME = "dekodeko_lj_feed.xml"
RSS_URL = "https://sergepetroff.github.io/DekoRss/dekodeko_lj_feed.xml"

USERNAME = "3bepb01"
PASSWORD = "NUJbWCajZ96!P8t"

async def login_and_scrape(page):
    print("Переход на страницу логина...")
    await page.goto(LOGIN_URL, timeout=180000, wait_until="domcontentloaded")
    await page.fill('input[name="user"]', USERNAME)
    await page.fill('input[name="password"]', PASSWORD)
    print("Отправляю форму логина...")
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("domcontentloaded")

    print(f"Переход на страницу: {LJ_URL}")
    try:
        await page.goto(LJ_URL, timeout=180000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"Ошибка перехода на страницу {LJ_URL}: {e}")
        raise

    print("Проверка и обход 18+...")
    try:
        confirm = page.locator('text="Yes, I am at least 18 years old."')
        visible = await confirm.is_visible()
        print(f"18+ кнопка видима: {visible}")
        if visible:
            await confirm.click()
            await page.wait_for_load_state('domcontentloaded')
    except Exception as e:
        print(f"Кнопка 18+ отсутствует или ошибка: {e}")

    await page.wait_for_selector("div.entry-wrap--post", timeout=180000)

async def scrape_and_generate_rss():
    async with async_playwright() as p:
        print("Запуск браузера...")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])

        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36")

        try:
            await login_and_scrape(page)
        except Exception as e:
            print(f"Ошибка при переходе на целевую страницу: {e}")
            await browser.close()
            return

        print("Получаем HTML страницы...")
        html = await page.content()
        await browser.close()

    print("Генерируем RSS...")
    soup = BeautifulSoup(html, "html.parser")
    fg = FeedGenerator()
    fg.id(LJ_URL)
    fg.title("LiveJournal RSS")
    fg.author({"name": USERNAME})
    fg.link(href=LJ_URL, rel="alternate")
    fg.language("ru")
    fg.atom_link(href=RSS_URL, rel="self")

    posts = soup.find_all("div.entry-wrap--post")
    if not posts:
        print("Внимание: посты не найдены!")

    for post in posts:
        titletag = post.find("h3", class_="item-title") or post.find("h2", class_="entry-title")
        title = titletag.get_text(strip=True) if titletag else "No Title"
        linktag = titletag.find("a", href=True) if titletag else None
        link = linktag["href"] if linktag else LJ_URL
        datetag = post.find("time", class_="item-date") or post.find("span", class_="entry-date")
        pubdate_raw = datetag.get("datetime") if datetag and datetag.has_attr("datetime") else None

        if pubdate_raw:
            dt_obj = datetime.fromisoformat(pubdate_raw)
            pubdate_formatted = format_datetime(dt_obj)
        else:
            pubdate_formatted = format_datetime(datetime.now(timezone.utc))

        contenttag = post.find("div", class_="entry-content")
        content = contenttag.get_text(strip=True)[:500] if contenttag else ""

        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(content)
        fe.published(pubdate_formatted)
        fe.guid(link)

    fg.rss_file(RSS_FILENAME)
    print(f"RSS файл создан: {RSS_FILENAME}")

if __name__ == "__main__":
    asyncio.run(scrape_and_generate_rss())
