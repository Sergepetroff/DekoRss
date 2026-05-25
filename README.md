# LiveJournal RSS Scraper  
Скрипт автоматизирует вход в LiveJournal и создает Full Text RSS-ленту для указанного пользователя или блога. Даже если штатный RSS - отключен.

## Функциональность  
- Авторизация через Playwright (в том числе 18+ страницы)  
- Скрапинг постов с заданного URL  
- Очистка HTML и корректировка размеров эмодзи  
- Генерация RSS-файла (`..._lj_feed.xml`)  
- Поддержка русскоязычных блогов  
- Опциональный AI-анализ тона текста через Groq  
- Опциональная цветовая разметка HTML-абзацев по tone score  

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

`GROQ_API_KEY` нужен только для AI-функций. Без него основной RSS-скрапер продолжает работать, но tone analysis и colorization будут недоступны.

`GROQ_MODEL` опционален. По умолчанию используется `llama-3.1-8b-instant`.

## AI-анализ тона

Проект также содержит отдельные утилиты для AI-анализа текста через Groq. Они не встроены в `main_scraper.py`, не участвуют в автодеплое RSS и запускаются вручную.

Что умеет AI-блок:
- Оценивать тон отдельного текста по шкале от `-2` до `2`
- Анализировать HTML по абзацам
- Добавлять цветовую разметку и badge с tone score в HTML-вывод

Текущая шкала:
- `-2` — выраженно в сторону female
- `-1` — умеренно в сторону female
- `0` — нейтрально или баланс
- `1` — умеренно в сторону male
- `2` — выраженно в сторону male

Цвета в HTML-интерпретации:
- положительные значения: оттенки синего
- отрицательные значения: оттенки розового
- `0`: янтарный / нейтральный
- если анализ недоступен: серый блок с пометкой `Tone unavailable`

### Быстрые примеры

Проверить один абзац:
```bash
python groq_manual_test.py "Текст для проверки"
```

Проверить один абзац с явным выбором модели:
```bash
python groq_manual_test.py "Текст для проверки" --model llama-3.1-8b-instant
```

Раскрасить локальный HTML-файл по абзацам:
```bash
python html_tone_manual_test.py test.html --output colored_test.html
```

Если `--output` не указан, файл будет перезаписан на месте.

Подробности о prompt-логике и шкале находятся в `docs/tone_prompts.md`.

## Автодеплой (GitHub Actions)

`deploy.yml` автоматически генерирует и публикует RSS-файл через GitHub Pages artifact.

Сгенерированный файл `docs/dekodeko_lj_feed.xml` больше не коммитится обратно в `main`, поэтому он не должен создавать постоянные конфликты при merge/rebase.

Для работы workflow в настройках репозитория GitHub Pages должен использовать источник `GitHub Actions`.
