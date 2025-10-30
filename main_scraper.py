import asyncio, hashlib, os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from email.utils import format_datetime
from dotenv import load_dotenv
load_dotenv()

# Конфигурация
LOGIN_URL = "https://www.livejournal.com/login.bml"
#LJ_URL = "https://dekodeko.livejournal.com"  
RSS_FILENAME = "dekodeko_lj_feed.xml"

LJ_URL = os.getenv("LJ_URL")                # Страница для скрапинга после логина
LJ_USERNAME = os.getenv("LJ_USERNAME")
LJ_PASSWORD = os.getenv("LJ_PASSWORD")

if not LJ_USERNAME or not LJ_PASSWORD:
    raise ValueError(f"LJ_USERNAME or LJ_PASSWORD not set! LJ_USERNAME={LJ_USERNAME}, LJ_PASSWORD={LJ_PASSWORD}")

def fix_emoji_sizes(html: str, size: int = 18) -> str:
    """
    Проставляет явные размеры смайлам/эмодзи, чтобы они не раздувались в RSS.
    Эвристики: по классам и по подстрокам в src.
    """
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        classes = img.get("class", [])
        src = img.get("src", "") or ""
        # простые эвристики для LJ-смайлов
        is_smiley = any(k in classes for k in ("emoji", "emoticon", "smiley", "emote")) \
                    or any(x in src for x in ("emoji", "emoticon", "smiley", "smile"))
        if is_smiley:
            img["width"] = str(size)
            img["height"] = str(size)
            style = img.get("style", "")
            if "width" not in style and "height" not in style:
                style = (style + f";width:{size}px;height:{size}px;vertical-align:text-bottom").lstrip(";")
            img["style"] = style
    return str(soup)
    
async def login_and_scrape(page):
    print("Переход на страницу логина...")
    await page.goto(LOGIN_URL, timeout=120000, wait_until="domcontentloaded")
    await page.fill('input[name="user"]', LJ_USERNAME)
    await page.fill('input[name="password"]', LJ_PASSWORD, timeout=90000)  # 90s
    print("Отправляю форму логина...")
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("load")

    print(f"Переход на страницу: {LJ_URL}")
    await page.goto(LJ_URL, timeout=120000, wait_until="load")

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

    await page.wait_for_selector("div.entry-wrap--post", timeout=120000)         # Ждём появления постов

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
    fg.title("dekodeko LiveJournal RSS")
    fg.author({"name": LJ_USERNAME})
    fg.link(href=LJ_URL, rel="alternate")
    fg.description("Auto-generated RSS from LiveJournal")
    fg.language("ru")

    posts = soup.find_all("div", class_="entry-wrap--post")
    if not posts:
        print("Внимание: посты не найдены!")

    for post in posts:
        # Заголовок
        titletag = post.find('dt', class_='entry-title')
        title = titletag.get_text(strip=True) if titletag else "No Title"

        # Ссылка
        linktag = titletag.find('a', href=True) if titletag else None
        link = linktag['href'] if linktag else None
        if link and link.startswith('/'):
            link = LJ_URL + link
        if not link:
            link = LJ_URL

        # Дата публикации
        datetag = post.find('abbr', class_='updated')
        if datetag and datetag.has_attr('title'):
            dt_obj = datetime.fromisoformat(datetag['title'].replace('Z', '+00:00'))  # поддержка Z
#            pubdate = dt_obj.strftime("%Y-%m-%d %H:%M")
            pubdate = format_datetime(dt_obj)

        else:
            pubdate = None

        contenttag = post.find("div", class_="entry-content")
        title_candidate = contenttag.get_text(strip=True) if contenttag else "" # Вырезаем только чистый текст:
        description = contenttag.decode_contents() if contenttag else ""
        fixed_description = fix_emoji_sizes(description, size=18)
        if title == "(без темы)" and title_candidate:
            title = title_candidate[:40]

        # Добавление в RSS
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
#        fe.description(description)
        fe.content(fixed_description, type="CDATA")

        if pubdate:
            fe.pubDate(pubdate)

        guid = link if link else hashlib.md5(title.encode('utf-8')).hexdigest()
        fe.guid(guid, permalink=bool(link))

        print(f"| {title} | {pubdate} | {guid}")
        fg.rss_file(RSS_FILENAME)         # После того, как все записи добавлены

    print("-" * 40)
    print(f"RSS файл записан: {RSS_FILENAME}")

if __name__ == "__main__":
    asyncio.run(scrape_and_generate_rss())
