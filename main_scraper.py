import hashlib, os, re, sys, urllib.request
import html as html_lib
from bs4 import BeautifulSoup, NavigableString
from feedgen.feed import FeedGenerator
from datetime import datetime
from email.utils import format_datetime
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

def fetch_url(url: str, timeout: int = 25) -> str:
    """Загружает страницу с кукой adult_explicit=1 для обхода 18+ ограничений"""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Cookie": "adult_explicit=1",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")

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
    """
    Проставляет явные размеры смайлам/эмодзи, чтобы они не раздувались в RSS.
    """
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        classes = img.get("class", [])
        src = img.get("src", "") or ""
        is_smiley = any(k in classes for k in ("emoji", "emoticon", "smiley", "emote")) \
                    or any(x in src for x in ("emoji", "emoticon", "smiley", "smile"))
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
        is_inline_tag = getattr(child, "name", None) not in block_tags if not isinstance(child, NavigableString) else False

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
    """
    Упрощает HTML из LJ до более чистого и предсказуемого RSS-контента.
    """
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
    try:
        html = fetch_url(LJ_URL)
    except Exception as e:
        print(f"Ошибка при загрузке главной страницы: {e}")
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

    for post in posts:
        # Заголовок
        titletag = post.find("dt", class_="entry-title")
        title = titletag.get_text(strip=True) if titletag else "No Title"

        # Ссылка
        linktag = titletag.find("a", href=True) if titletag else None
        link = linktag["href"] if linktag else None
        if link and link.startswith("/"):
            link = LJ_URL.rstrip("/") + link
        if not link:
            link = LJ_URL

        # Дата публикации
        datetag = post.find("abbr", class_="updated")
        if datetag and datetag.has_attr("title"):
            try:
                dt_obj = datetime.fromisoformat(datetag["title"].replace("Z", "+00:00"))
                pubdate = format_datetime(dt_obj)
            except Exception:
                pubdate = None
        else:
            pubdate = None

        contenttag = post.find("div", class_="entry-content")
        title_candidate = contenttag.get_text(strip=True) if contenttag else ""
        description = contenttag.decode_contents() if contenttag else ""
        post_tags = extract_post_tags(post)

        # Если в ленте вместо текста заглушка 18+ или пустой текст:
        # Загружаем страницу поста напрямую с кукой adult_explicit=1
        if "appropriate for adults" in description or not description.strip() or len(title_candidate) < 15:
            if link and link.startswith("http"):
                try:
                    post_html = fetch_url(link, timeout=15)
                    post_soup = BeautifulSoup(post_html, "html.parser")

                    # Извлекаем заголовок
                    single_title = post_soup.find("h1", class_="aentry-post__title") or post_soup.find("title")
                    if single_title:
                        raw_t = single_title.get_text(strip=True)
                        clean_t = re.sub(r":\s*dekodeko\s*—\s*LiveJournal.*$", "", raw_t).strip()
                        if clean_t and clean_t not in ("(no subject)", "(без темы)"):
                            title = clean_t

                    # Извлекаем авторские теги
                    single_tags = [
                        a.get_text(strip=True)
                        for a in post_soup.find_all("a", href=lambda h: h and "/tag/" in h)
                        if a.get_text(strip=True)
                    ]
                    if single_tags:
                        post_tags = single_tags

                    # Извлекаем полный текст записи
                    single_content = post_soup.find("div", class_="aentry-post__text") or post_soup.find("article")
                    if single_content:
                        description = single_content.decode_contents()
                        title_candidate = single_content.get_text(strip=True)
                except Exception as enrich_err:
                    print(f"Ошибка при загрузке {link}: {enrich_err}")

        # Фильтрация по исключённым тегам
        matched_excluded_tags = [
            tag for tag in post_tags if tag.casefold() in LJ_EXCLUDED_TAGS
        ]
        if matched_excluded_tags:
            print(f"- Пропускаю пост '{title}' из-за тегов: {', '.join(matched_excluded_tags)}")
            continue

        normalized_description = normalize_rss_html(description)
        fixed_description = fix_emoji_sizes(normalized_description, size=18)

        if title in ("(без темы)", "(no subject)", "No Title") and title_candidate:
            title = title_candidate[:60]

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
