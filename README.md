# LiveJournal RSS Scraper  
Скрипт автоматизирует вход в LiveJournal и создает Full Text RSS-ленту для указанного пользователя или блога. Даже если штатный RSS - отключен.

## Функциональность  
- Авторизация через Playwright (в том числе 18+ страницы)  
- Скрапинг постов с заданного URL  
- Очистка HTML и корректировка размеров эмодзи  
- Генерация RSS-файла (`..._lj_feed.xml`)  
- Поддержка русскоязычных блогов  

## Требования  
- Python ≥ 3.10  
- Playwright, BeautifulSoup4, Feedgen, python-dotenv  

## Установка  
```bash
pip install -r requirements.txt
playwright install chromium
```

## Переменные окружения (.env)
```bash
LJ_URL=https://username.livejournal.com
LJ_USERNAME=your_login
LJ_PASSWORD=your_password
LJ_EXCLUDED_TAGS=видео,#shorts
```

`LJ_EXCLUDED_TAGS` опционален. Если задан, скрипт пропускает все посты, у которых есть хотя бы один тег из списка. Значения перечисляются через запятую, сравнение идет без учета регистра и лишних пробелов.

Для локального ручного теста можно скопировать шаблон:

```bash
cp .env.example .env
```

`PLAYWRIGHT_HEADLESS=false` включает видимый браузер, чтобы руками проверить логин, 18+ подтверждение и загрузку постов.

## Ручная проверка перед merge

### Локально
```bash
cp .env.example .env
pip install playwright beautifulsoup4 feedgen python-dotenv
playwright install chromium
PLAYWRIGHT_HEADLESS=false python main_scraper.py
```

После выполнения проверьте файл `dekodeko_lj_feed.xml`.

### Через GitHub Actions
1. Откройте workflow `Generate, Preview and Publish RSS`.
2. Нажмите **Run workflow** на нужной ветке.
3. Оставьте `Deploy generated RSS to GitHub Pages` выключенным, если нужен только preview.
4. Скачайте artifact `rss-preview` и проверьте `dekodeko_lj_feed.xml`.
5. Если результат устраивает, повторно запустите workflow с включенным publish или мержите изменения.

Для ручной проверки GroQ отдельно используйте workflow `GroQ Manual Tone Test` или локально:

```bash
python groq_manual_test.py "Тестовый абзац"
```

## Автодеплой (GitHub Actions)

`deploy.yml` по расписанию автоматически генерирует и публикует RSS-файл через GitHub Pages artifact. При ручном запуске workflow можно сначала получить preview-артефакт без публикации.

Сгенерированный файл `docs/dekodeko_lj_feed.xml` больше не коммитится обратно в `main`, поэтому он не должен создавать постоянные конфликты при merge/rebase.

Для работы workflow в настройках репозитория GitHub Pages должен использовать источник `GitHub Actions`.
