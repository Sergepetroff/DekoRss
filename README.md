# LiveJournal RSS Scraper  
Скрипт автоматизирует вход в LiveJournal и создает Full Text RSS-ленту для указанного пользователя или блога. Даже если штатный RSS - отключен.

## Функциональность  
- Авторизация через Playwright (в том числе 18+ страницы)  
- Скрапинг постов с заданного URL  
- Очистка HTML и корректировка размеров эмодзи  
- Опциональный tone-анализ через GroQ (простая шкала M/F 0..2)  
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
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
```

`LJ_EXCLUDED_TAGS` опционален. Если задан, скрипт пропускает все посты, у которых есть хотя бы один тег из списка. Значения перечисляются через запятую, сравнение идет без учета регистра и лишних пробелов.
`GROQ_API_KEY` опционален. Если задан, для каждого поста добавляется AI-оценка тона (M/F 0..2) и прозрачность текста в RSS меняется на основе разницы этих оценок.

## Автодеплой (GitHub Actions)

`deploy.yml` автоматически генерирует и публикует RSS-файл через GitHub Pages artifact.

Сгенерированный файл `docs/dekodeko_lj_feed.xml` больше не коммитится обратно в `main`, поэтому он не должен создавать постоянные конфликты при merge/rebase.

Для работы workflow в настройках репозитория GitHub Pages должен использовать источник `GitHub Actions`.
