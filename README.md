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
```

## Автодеплой (GitHub Actions)

`deploy.yml` автоматически публикует сгенерированный RSS-файл при каждом обновлении.
