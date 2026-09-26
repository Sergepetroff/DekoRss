import hashlib
import http.cookiejar
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import html as html_lib
from datetime import datetime
from email.utils import format_datetime
from bs4 import BeautifulSoup, NavigableString
from feedgen.feed import FeedGenerator
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
LJ_URL = os.getenv("LJ_URL") or "https://dekodeko.livejournal.com"
RSS_FILENAME = "dekodeko_lj_feed.xml"

LJ_EXCLUDED_TAGS = {
    tag.strip().casefold()
    for tag in (os.getenv("LJ_EXCLUDED_TAGS") or "").split(",")
    if tag.strip()
}

ADULT_WARNING_PHRASES = (
    "appropriate for adults",
    "adult content notice",
    "explicit adult content",
    "adult concepts",
    "содержимое только для взрослых",
    "подтвердите свой возраст",
    "you are about to view content",
    "материалы только для взрослых",
)

ADULT_COOKIES_HEADER = (
    "adult_explicit=1; adult_concepts=1; adult_mature=1; adult_content=1; "
    "prop_opt_adult_filter=none; lj_adult=1; bml_opt_adult=1; adult_check=1"
)

# Настройка CookieJar для сохранения сессионных кук LJ и передачи adult-флагов при любых редиректах
cookie_jar = http.cookiejar.CookieJar()
for c_name, c_val in [
    ("adult_explicit", "1"),
    ("adult_concepts", "1"),
    ("adult_mature", "1"),
    ("adult_content", "1"),
    ("prop_opt_adult_filter", "none"),
    ("lj_adult", "1"),
    ("bml_opt_adult", "1"),
    ("adult_check", "1"),
]:
    cookie_jar.set_cookie(
        http.cookiejar.Cookie(
            version=0,
            name=c_name,
            value=c_val,
            port=None,
            port_specified=False,
            domain=".livejournal.com",
            domain_specified=True,
            domain_initial_dot=True,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={"HttpOnly": None},
            rfc2109=False,
        )
    )

http_opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookie_jar)
)

def is_adult_stub(text: str) -> bool:
    """Проверяет, является ли текст заглушкой о возрастном ограничении 18+."""
    if not text:
        return True
    lower = text.lower()
    return any(phrase in lower for phrase in ADULT_WARNING_PHRASES)

def fetch_url(url: str, timeout: int = 25, retries: int = 3, data: bytes = None) -> str:
    """
    Загружает страницу с полным набором 18+ кук, автоматическим сохранением сессии
    и механизмом повторных попыток при сбоях сети/таймаутах.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Cookie": ADULT_COOKIES_HEADER,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://dekodeko.livejournal.com/",
    }

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with http_opener.open(req, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.0 * attempt)

    raise last_err or Exception(f"Failed to fetch {url}")

def extract_single_post(post_url: str) -> tuple[str, list[str], str]:
    """
    Загружает отдельную страницу записи LiveJournal и извлекает:
    (title, tags, clean_html_content).
    При необходимости использует легкий формат ?format=light или отправляет форму подтверждения 18+.
    """
    urls_to_try = [post_url]
    if "?" not in post_url:
        urls_to_try.append(f"{post_url}?format=light")

    title = ""
    tags: list[str] = []
    content_html = ""

    for url_candidate in urls_to_try:
        try:
            html = fetch_url(url_candidate, timeout=15, retries=2)
            soup = BeautifulSoup(html, "html.parser")

            # 1. Заголовок
            title_node = (
                soup.find("h1", class_="aentry-post__title")
                or soup.find("meta", property="og:title")
                or soup.find("title")
            )
            if title_node:
                raw_t = title_node.get("content", "") if title_node.name == "meta" else title_node.get_text(strip=True)
                clean_t = re.sub(r":\s*dekodeko\s*—\s*LiveJournal.*$", "", raw_t, flags=re.IGNORECASE).strip()
                clean_t = re.sub(r"—\s*LiveJournal.*$", "", clean_t, flags=re.IGNORECASE).strip()
                if (
                    clean_t
                    and not is_adult_stub(clean_t)
                    and clean_t not in ("(no subject)", "(без темы)", "No Title")
                ):
                    title = clean_t

            # 2. Авторские теги
            found_tags = [
                a.get_text(strip=True)
                for a in soup.find_all("a", href=lambda h: h and "/tag/" in h)
                if a.get_text(strip=True)
            ]
            if found_tags:
                tags = found_tags

            # 3. Поиск основного текста в известных контейнерах LJ
            candidate_tags = [
                soup.find("div", class_="aentry-post__text"),
                soup.find("div", class_="entry-content"),
                soup.find("div", class_="entry_text"),
                soup.find("div", class_="asset-body"),
                soup.find("div", class_="b-singlepost-body"),
                soup.find("div", class_="j-e-text"),
            ]

            for cand in candidate_tags:
                if not cand:
                    continue
                cand_text = cand.get_text(strip=True)
                # Никогда не принимаем блок, содержащий заглушку 18+
                if not is_adult_stub(cand_text) and len(cand_text) > 15:
                    content_html = cand.decode_contents()
                    break

            if content_html and not is_adult_stub(content_html):
                break

            # 4. Если на странице есть форма подтверждения возраста, отправляем ее (POST)
            adult_form = soup.find(
                "form",
                action=lambda a: a and any(k in a.lower() for k in ("adult", "check", "confirm")),
            )
            if adult_form:
                action = adult_form.get("action") or post_url
                if action.startswith("/"):
                    action = urllib.parse.urljoin(post_url, action)
                form_data = {}
                for inp in adult_form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        form_data[name] = inp.get("value", "")
                form_data["adult_check"] = "1"
                encoded = urllib.parse.urlencode(form_data).encode("utf-8")

                post_resp = fetch_url(action, data=encoded, timeout=15, retries=1)
                soup2 = BeautifulSoup(post_resp, "html.parser")
                for cand in [
                    soup2.find("div", class_="aentry-post__text"),
                    soup2.find("div", class_="entry-content"),
                    soup2.find("div", class_="b-singlepost-body"),
                ]:
                    if cand and not is_adult_stub(cand.get_text(strip=True)):
                        content_html = cand.decode_contents()
                        break
                if content_html:
                    break

        except Exception:
            continue

    return title, tags, content_html

def load_existing_feed(filenames: list[str]) -> dict[str, dict]:
    """
    Загружает предыдущий сгенерированный RSS файл для защиты от перезаписи
    качественных постов пустыми заглушками при временных сетевых ошибках LiveJournal.
    """
    entries = {}
    for filename in filenames:
        if not os.path.exists(filename):
            continue
        try:
            with open(filename, "r", encoding="utf-8", errors="ignore") as f:
                feed_soup = BeautifulSoup(f.read(), "xml")
            for item in feed_soup.find_all("item"):
                link_node = item.find("link")
                link = link_node.get_text(strip=True) if link_node else ""
                title_node = item.find("title")
                title = title_node.get_text(strip=True) if title_node else ""
                content_node = item.find("content:encoded") or item.find("description")
                content = content_node.decode_contents() if content_node else ""
                content_text = content_node.get_text(strip=True) if content_node else ""

                if link and not is_adult_stub(title) and not is_adult_stub(content_text):
                    entries[link] = {
                        "title": title,
                        "content": content,
                        "pubDate": item.find("pubDate").get_text(strip=True) if item.find("pubDate") else None,
                        "guid": item.find("guid").get_text(strip=True) if item.find("guid") else link,
                    }
            if entries:
                print(f"Загружено {len(entries)} сохраненных постов из {filename} для защиты от сбоев.")
                break
        except Exception as e:
            print(f"Предупреждение при чтении {filename}: {e}")
    return entries

def extract_post_tags(post) -> list[str]:
    tag_container = post.find("div", class_="ljtags")
    if not tag_container:
        return []

    return [
        tag_link.get_text(strip=True)
        for tag_link in tag_container.find_all("a", rel=lambda value: value and "tag" in value)
        if tag_link.get_text(strip=True)
    ]

def fix_emoji_sizes(html: str, size: int = 18) -> str:
    """Проставляет явные размеры смайлам/эмодзи, чтобы они не раздувались в RSS."""
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        classes = img.get("class", [])
        src = img.get("src", "") or ""
        is_smiley = any(k in classes for k in ("emoji", "emoticon", "smiley", "emote")) or any(
            x in src for x in ("emoji", "emoticon", "smiley", "smile")
        )
        if is_smiley:
            img["width"] = str(size)
            img["height"] = str(size)
            style = img.get("style", "")
            if "width" not in style and "height" not in style:
                style = (style + f";width:{size}px;height:{size}px;vertical-align:text-bottom").lstrip(";")
            img["style"] = style
        elif img.has_attr("style"):
            del img["style"]
    return str(soup)

def wrap_loose_nodes_in_paragraphs(soup: BeautifulSoup) -> None:
    container = soup.body if soup.body else soup
    block_tags = {"blockquote", "div", "li", "ol", "p", "pre", "ul"}
    inline_buffer = []
    insert_before_node = None

    def flush_inline_buffer() -> None:
        nonlocal inline_buffer, insert_before_node
        if not inline_buffer:
            return

        paragraph = soup.new_tag("p")
        anchor = insert_before_node
        if anchor is None:
            inline_buffer = []
            return

        anchor.insert_before(paragraph)
        for node in inline_buffer:
            paragraph.append(node.extract())

        if not paragraph.get_text(" ", strip=True) and not paragraph.find("img"):
            paragraph.decompose()

        inline_buffer = []
        insert_before_node = None

    for child in list(container.contents):
        is_inline_text = isinstance(child, NavigableString) and bool(str(child).strip())
        is_inline_tag = (
            getattr(child, "name", None) not in block_tags
            if not isinstance(child, NavigableString)
            else False
        )

        if is_inline_text or is_inline_tag:
            if insert_before_node is None:
                insert_before_node = child
            inline_buffer.append(child)
            continue

        flush_inline_buffer()
        if isinstance(child, NavigableString):
            child.extract()

    flush_inline_buffer()

def normalize_rss_html(html: str) -> str:
    """Упрощает HTML из LJ до чистого и предсказуемого RSS-контента."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "svg", "form", "input", "button", "textarea"]):
        tag.decompose()

    for tag_block in soup.find_all("div", class_="ljtags"):
        tag_block.decompose()

    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "") or iframe.get("data-src", "")
        if src:
            replacement = soup.new_tag("p")
            link = soup.new_tag("a", href=src)
            link.string = "Open embedded media"
            replacement.append(link)
            iframe.replace_with(replacement)
        else:
            iframe.decompose()

    for tag in list(soup.find_all()):
        if tag.name in {"html", "body"}:
            tag.unwrap()
            continue

        if tag.name == "div":
            has_block_children = any(
                getattr(child, "name", None) in {"p", "div", "ul", "ol", "li", "blockquote", "pre"}
                for child in tag.children
            )
            if has_block_children:
                tag.unwrap()
            else:
                tag.name = "p"
            continue

        if tag.name in {"span", "font", "section", "article", "header", "footer", "ytd-expander"}:
            tag.unwrap()
            continue

        if "-" in tag.name and tag.name not in {"lj-embed"}:
            tag.unwrap()

    allowed_attrs = {
        "a": {"href", "title"},
        "img": {"src", "alt", "title", "width", "height"},
    }
    allowed_tags = {
        "a", "b", "blockquote", "br", "code", "em", "i", "img", "li", "ol", "p", "pre", "strong", "sub", "sup", "u", "ul"
    }

    for tag in list(soup.find_all()):
        if tag.name not in allowed_tags:
            tag.unwrap()
            continue

        keep_attrs = allowed_attrs.get(tag.name, set())
        attrs_to_remove = [attr_name for attr_name in tag.attrs if attr_name not in keep_attrs]
        for attr_name in attrs_to_remove:
            del tag[attr_name]

        if tag.name == "a":
            href = (tag.get("href") or "").strip()
            if not href:
                tag.unwrap()
            elif href.startswith("//"):
                tag["href"] = f"https:{href}"
            elif href.startswith("/") and LJ_URL:
                tag["href"] = f"{LJ_URL.rstrip('/')}{href}"

        if tag.name == "img":
            src = (tag.get("src") or "").strip()
            if not src:
                tag.decompose()
            elif src.startswith("//"):
                tag["src"] = f"https:{src}"

    wrap_loose_nodes_in_paragraphs(soup)

    normalized_html = str(soup)
    normalized_html = re.sub(r"(?:\s*<br\s*/?>\s*){3,}", "<br/><br/>", normalized_html, flags=re.IGNORECASE)
    normalized_html = re.sub(r"<p>\s*</p>", "", normalized_html, flags=re.IGNORECASE)

    normalized_soup = BeautifulSoup(normalized_html, "html.parser")
    for paragraph in normalized_soup.find_all("p"):
        if not paragraph.get_text(" ", strip=True) and not paragraph.find("img"):
            paragraph.decompose()

    return str(normalized_soup)

def scrape_and_generate_rss():
    print(f"Загрузка главной страницы блога: {LJ_URL}...")
    cached_entries = load_existing_feed([f"docs/{RSS_FILENAME}", RSS_FILENAME])

    try:
        html = fetch_url(LJ_URL, timeout=25, retries=3)
    except Exception as e:
        print(f"Ошибка при загрузке главной страницы: {e}")
        if cached_entries:
            print("Сохраняем существующий RSS без изменений из-за ошибки сети.")
            sys.exit(0)
        sys.exit(1)

    print("Парсинг ленты записей...")
    soup = BeautifulSoup(html, "html.parser")
    fg = FeedGenerator()
    fg.id(LJ_URL)
    fg.title("dekodeko LiveJournal RSS")
    fg.author({"name": "dekodeko"})
    fg.link(href=LJ_URL, rel="alternate")
    fg.description("Auto-generated RSS from LiveJournal")
    fg.language("ru")

    posts = soup.find_all("div", class_="entry-wrap--post")
    if not posts:
        print("Внимание: посты не найдены в ленте!")
        return

    print(f"Найдено постов в ленте: {len(posts)}")

    for idx, post in enumerate(posts):
        # 1. Заголовок из ленты
        titletag = post.find("dt", class_="entry-title")
        raw_title = titletag.get_text(strip=True) if titletag else ""

        # 2. Ссылка
        linktag = titletag.find("a", href=True) if titletag else None
        link = linktag["href"] if linktag else None
        if link and link.startswith("/"):
            link = LJ_URL.rstrip("/") + link
        if not link:
            link = LJ_URL

        # ID поста для формирования резервного заголовка
        post_id_match = re.search(r"/(\d+)\.html", link)
        post_id = post_id_match.group(1) if post_id_match else str(idx + 1)

        # 3. Дата публикации
        datetag = post.find("abbr", class_="updated")
        pubdate = None
        pubdate_str = ""
        if datetag and datetag.has_attr("title"):
            try:
                dt_obj = datetime.fromisoformat(datetag["title"].replace("Z", "+00:00"))
                pubdate = format_datetime(dt_obj)
                pubdate_str = dt_obj.strftime("%d.%m.%Y %H:%M")
            except Exception:
                pubdate = None

        contenttag = post.find("div", class_="entry-content")
        raw_content_text = contenttag.get_text(strip=True) if contenttag else ""
        description = contenttag.decode_contents() if contenttag else ""
        post_tags = extract_post_tags(post)

        # Проверяем, является ли заголовок или контент в ленте заглушкой 18+
        title = raw_title if raw_title and not is_adult_stub(raw_title) else ""
        needs_enrichment = is_adult_stub(raw_content_text) or len(raw_content_text) < 25 or not title

        if needs_enrichment and link.startswith("http"):
            # Для не-первых постов, если они уже есть в качественном кэше, берем из кэша
            if idx >= 5 and link in cached_entries:
                cached = cached_entries[link]
                title = cached.get("title") or title
                description = cached.get("content") or description
            else:
                # Загружаем отдельную страницу поста с обходом 18+
                try:
                    time.sleep(0.3)  # Бережный интервал против рейт-лимита LJ
                    enriched_title, enriched_tags, enriched_html = extract_single_post(link)
                    if enriched_title and not is_adult_stub(enriched_title):
                        title = enriched_title
                    if enriched_tags:
                        post_tags = enriched_tags
                    if enriched_html and not is_adult_stub(enriched_html):
                        description = enriched_html
                    elif link in cached_entries:
                        # Резервный откат к кэшу, если новая попытка не вернула текст
                        cached = cached_entries[link]
                        title = cached.get("title") or title
                        description = cached.get("content") or description
                except Exception as enrich_err:
                    print(f"Ошибка при загрузке {link}: {enrich_err}")
                    if link in cached_entries:
                        cached = cached_entries[link]
                        title = cached.get("title") or title
                        description = cached.get("content") or description

        # Если после всех попыток контент всё еще содержит только заглушку 18+:
        if is_adult_stub(description) or is_adult_stub(BeautifulSoup(description, "html.parser").get_text(strip=True)):
            if link in cached_entries:
                description = cached_entries[link].get("content") or description
                title = cached_entries[link].get("title") or title
            else:
                description = (
                    f"<p>Запись LiveJournal (18+).</p>"
                    f"<p><a href=\"{link}\">Открыть запись в блоге dekodeko</a></p>"
                )

        # Фильтрация по исключённым тегам
        matched_excluded_tags = [
            tag for tag in post_tags if tag.casefold() in LJ_EXCLUDED_TAGS
        ]
        if matched_excluded_tags:
            print(f"- Пропускаю пост '{title or link}' из-за тегов: {', '.join(matched_excluded_tags)}")
            continue

        normalized_description = normalize_rss_html(description)
        fixed_description = fix_emoji_sizes(normalized_description, size=18)

        # Финализация заголовка: никогда не допускаем заголовок с предупреждением 18+
        clean_text_snippet = BeautifulSoup(fixed_description, "html.parser").get_text(" ", strip=True)
        if is_adult_stub(title) or title in ("(без темы)", "(no subject)", "No Title", ""):
            if clean_text_snippet and not is_adult_stub(clean_text_snippet):
                title = clean_text_snippet[:60].replace("\n", " ").strip()
            elif pubdate_str:
                title = f"Запись от {pubdate_str}"
            else:
                title = f"Запись #{post_id}"

        # Добавление в RSS
        fe = fg.add_entry()
        fe.title(title)
        fe.link(href=link)
        fe.content(fixed_description, type="CDATA")

        if pubdate:
            fe.pubDate(pubdate)

        guid = link if link else hashlib.md5(title.encode("utf-8")).hexdigest()
        fe.guid(guid, permalink=bool(link))

        print(f"| {title[:50]} | {pubdate} | {guid}")

    fg.rss_file(RSS_FILENAME)
    print("-" * 40)
    print(f"RSS файл записан: {RSS_FILENAME}")

if __name__ == "__main__":
    scrape_and_generate_rss()
