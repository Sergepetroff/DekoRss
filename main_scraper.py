import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone

# Конфигурация
LOGIN_URL = "https://www.livejournal.com/login.bml"
LJ_URL = "https://dekodeko.livejournal.com"  # Страница для скрапинга после логина
RSS_FILENAME = "dekodeko_lj_feed.xml"

USERNAME = "3bepb01"
PASSWORD = "NUJbWCajZ96!P8t"

async def login_and_scrape(page):
    print("Переход на страницу логина...")
    await page.goto(LOGIN_URL, timeout=120000, wait_until="domcontentloaded")
    await page.fill('input[name="user"]', USERNAME)
    await page.fill('input[name="password"]', PASSWORD)
    print("Отправляю форму логина...")
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("load")

    print(f"Переход на страницу: {LJ_URL}")
    await page.goto(LJ_URL, timeout=60000, wait_until="load")

    print("Проверка и обход 18+...")
    try:
        confirm = page.locator('text="Yes, I am at least 18 years old."')
        visible = await confirm.is_visible()
        print(f"18+ кнопка видима: {visible}")
        if visible:
            await confirm.click()
            await page.wait_for_load_state('load')
    except Exception as e:
        print(f"Кнопка 18+ отсутствует или ошибка: {e}")

    # Ждём появления постов
    await page.wait_for_selector("div.entry-wrap--post", timeout=30000)

async def scrape_and_generate_rss():
    async with async_playwright() as p:
        print("Запуск браузера...")
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        page.on("requestfailed", lambda request: print(f"Request failed: {request.url}"))

        await login_and_scrape(page)

        print("Ожидание загрузки постов...")
        try:
            await page.wait_for_selector("div.entry-wrap--post", timeout=60000)
        except Exception as e:
            print(f"Не дождался постов: {e}")

        print("Получение HTML страницы...")
        html = await page.content()
        print("Завершаю работу браузера...")
        await browser.close()

    print("Парсинг и генерация RSS...")
    soup = BeautifulSoup(html, "html.parser")
    fg = FeedGenerator()
    fg.id(LJ_URL)
    fg.title("LiveJournal RSS")
    fg.author({"name": USERNAME})
    fg.link(href=LJ_URL, rel="alternate")
    fg.description("Auto-generated RSS from LiveJournal")
    fg.language("ru")

    posts = soup.find_all("div", class_="entry-wrap--post")
    if not posts:
        print("Внимание: посты не найдены!")

    for post in posts:
        titletag = post.find("h3", class_="item-title") or post.find("h2", class_="entry-title")
        title = titletag.get_text(strip=True) if titletag else "No Title"
        linktag = titletag.find("a", href=True) if titletag else None
        link = linktag["href"] if linktag else LJ_URL
        datetag = post.find("time", class_="item-date") or post.find("span", class_="entry-date")
        pubdate = datetag.get("datetime") if datetag and datetag.has_attr("datetime") else datetime.now(timezone.utc).isoformat()
        contenttag = post.find("div", class_="entry-content")
        content = contenttag.get_text(strip=True)[:500] if contenttag else ""
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.description(content)
        fe.published(pubdate)

    fg.rss_file(RSS_FILENAME)
    print(f"RSS успешно создан: {RSS_FILENAME}")

if __name__ == "__main__":
    asyncio.run(scrape_and_generate_rss())
