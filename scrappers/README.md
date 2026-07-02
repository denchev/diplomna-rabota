# marush_denchev_comments_scraper

Инструмент за скрейпване на коментари от четири български новинарски сайта:
**dnes.dir.bg**, **fakti.bg**, **mediapool.bg** и **dir.bg**.

Резултатите се записват в CSV файлове — по един файл на сайт на всяко пускане.

---

## Съдържание

1. [Изисквания](#изисквания)
2. [Инсталация](#инсталация)
3. [Структура на проекта](#структура-на-проекта)
4. [Конфигурация — входни URL-и](#конфигурация--входни-url-и)
5. [Пускане на скрейпърите](#пускане-на-скрейпърите)
6. [dir.bg — специален режим](#dirbg--специален-режим)
7. [Изходни файлове](#изходни-файлове)
8. [Описание на CSV полетата](#описание-на-csv-полетата)

---

## Изисквания

- **Ubuntu 22.04 или по-нова** (тестван на Ubuntu в VirtualBox/Parallels на MacBook)
- **Python 3.10 или по-нов**
- **Google Chrome или Firefox** с инсталирана разширение **Tampermonkey** (само за dir.bg)
- Интернет връзка

---

## Инсталация

### Стъпка 1 — Клониране на проекта

```bash
git clone <repo-url> marush_denchev_comments_scraper
cd marush_denchev_comments_scraper
```

Или разархивирайте ZIP-а и влезте в директорията:

```bash
unzip marush_denchev_comments_scraper.zip
cd marush_denchev_comments_scraper
```

### Стъпка 2 — Виртуална среда

```bash
python3 -m venv venv
source venv/bin/activate
```

След активиране командният ред трябва да показва `(venv)` пред пътя.

### Стъпка 3 — Инсталиране на зависимости

```bash
pip install -r requirements.txt
```

### Стъпка 4 — Инсталиране на Playwright и Chromium

Тази стъпка е задължителна само за **mediapool.bg**. За останалите сайтове не е необходима.

```bash
pip install playwright
playwright install chromium
```

> **Забележка:** `pip install playwright` и `playwright install chromium` са две отделни команди. Втората изтегля самия браузър и може да отнеме известно време.

### Стъпка 5 — Tampermonkey (само за dir.bg)

1. Инсталирайте разширението **Tampermonkey** в Chrome или Firefox.
2. Отворете Tampermonkey → **Dashboard** → бутон **+** (нов скрипт).
3. Изтрийте примерното съдържание и поставете съдържанието на файла `browser_scripts/dir_bg_tampermonkey.js`.
4. Запазете с **Ctrl+S**.

---

## Структура на проекта

```
marush_denchev_comments_scraper/
│
├── main.py                          # Главна точка за стартиране
├── config.py                        # Централна конфигурация
├── requirements.txt                 # Python зависимости
│
├── models/
│   └── comment_record.py            # Модел на един коментарен запис
│
├── services/
│   ├── logging_service.py           # Споделено логване (log + print)
│   ├── request_service.py           # HTTP заявки с retry логика
│   ├── delay_service.py             # Паузи между заявки
│   └── csv_service.py               # Запис в CSV файлове
│
├── utils/
│   ├── text_utils.py                # Почистване на текст
│   ├── url_utils.py                 # Работа с URL-и
│   ├── date_utils.py                # Генериране на timestamps
│   ├── file_utils.py                # Работа с директории
│   └── source_loader.py             # Зареждане на входни URL-и
│
├── parsers/
│   ├── dnes_bg_parser.py            # HTML парсър за dnes.dir.bg
│   ├── fakti_bg_parser.py           # HTML парсър за fakti.bg
│   ├── mediapool_bg_parser.py       # HTML парсър за категории на mediapool.bg
│   └── mediapool_bg_comments_parser.py  # HTML парсър за коментари на mediapool.bg
│
├── scrapers/
│   ├── dnes_bg_scraper.py           # Скрейпър за dnes.dir.bg
│   ├── fakti_bg_scraper.py          # Скрейпър за fakti.bg
│   └── mediapool_bg_scraper.py      # Скрейпър за mediapool.bg (ползва Playwright)
│
├── server/
│   └── flask_receiver.py            # Flask сървър за dir.bg интеграция
│
├── browser_scripts/
│   └── dir_bg_tampermonkey.js       # Tampermonkey скрипт за dir.bg
│
├── input_urls/
│   ├── dnes_bg.txt                  # Начални URL-и за dnes.dir.bg
│   ├── fakti_bg.txt                 # Начални URL-и за fakti.bg
│   ├── mediapool_bg.txt             # Начални URL-и за mediapool.bg
│   └── dir_bg.txt                   # Начални URL-и за dir.bg
│
├── output/                          # Генерирани CSV файлове (създава се автоматично)
└── logs/                            # Лог файлове (създава се автоматично)
```

### Как работи всеки компонент

**`main.py`** — единствената точка за стартиране. Приема аргументи от командния ред (`scrape` или `server` режим) и делегира към съответния скрейпър.

**`config.py`** — всички настройки на едно място: timeout-и, delay-и, пътища до директории, имена на сайтове. Ако искате да промените нещо, търсете тук.

**`parsers/`** — отговарят само за четене на HTML и извличане на данни. Не правят HTTP заявки и не записват файлове.

**`scrapers/`** — оркестрират целия процес за един сайт: зареждат входните URL-и, обхождат страниците, викат парсърите, записват резултатите в CSV.

**`server/flask_receiver.py`** — специален компонент само за dir.bg. Стартира локален HTTP сървър, който дава инструкции на Tampermonkey скрипта в браузъра и получава резултатите обратно.

**`browser_scripts/dir_bg_tampermonkey.js`** — JavaScript скрипт, работещ в браузъра. Пита Flask сървъра за следваща задача, отваря страницата, извлича данните и ги изпраща обратно.

---

## Конфигурация — входни URL-и

Преди пускане трябва да попълните файловете в `input_urls/` с URL-ите, от които да започне обхождането.

### Формат

Всеки файл съдържа по един URL на ред. Празните редове се игнорират.

### Примери

**`input_urls/dnes_bg.txt`**
```
https://dnes.dir.bg/politika
https://dnes.dir.bg/obshtestvo
https://dnes.dir.bg/svyat
```

**`input_urls/fakti_bg.txt`**
```
https://fakti.bg/bulgaria
https://fakti.bg/world
```

**`input_urls/mediapool_bg.txt`**
```
https://www.mediapool.bg/politics
https://www.mediapool.bg/society
```

**`input_urls/dir_bg.txt`**
```
https://dir.bg/topic/predsrochni-izbori-2026
https://dnes.dir.bg/politika
```

> **Как работи обхождането:** Скрейпърът тръгва от дадения URL, извлича всички статии на страницата, след което автоматично следва пагинацията и обхожда всички следващи страници. Не е нужно да въвеждате всяка страница ръчно.

---

## Пускане на скрейпърите

Уверете се, че виртуалната среда е активирана:

```bash
source venv/bin/activate
```

### dnes.dir.bg

```bash
python main.py scrape --source dnes_bg --log-level INFO
```

### fakti.bg

```bash
python main.py scrape --source fakti_bg --log-level INFO
```

### mediapool.bg

```bash
python main.py scrape --source mediapool_bg --log-level INFO
```

> mediapool.bg ползва Playwright (реален браузър), защото коментарите се зареждат динамично. Playwright стартира Chromium в режим **без видим прозорец** (headless). Ако искате да видите какво прави браузърът, отворете `config.py` и сменете `PLAYWRIGHT_HEADLESS = True` на `PLAYWRIGHT_HEADLESS = False`.

### Нива на логване

| Ниво | Кога се използва |
|------|-----------------|
| `DEBUG` | При разработка — показва всяка заявка и парсиран елемент |
| `INFO` | Нормална употреба — показва прогреса по статии и страници |
| `WARNING` | Само предупреждения и грешки |
| `ERROR` | Само грешки |

```bash
python main.py scrape --source dnes_bg --log-level DEBUG
```

---

## dir.bg — специален режим

dir.bg използва Cloudflare, който блокира автоматизирани заявки. Затова архитектурата е различна: **браузърът (с Tampermonkey) е активната страна, Python е пасивен координатор**.

### Как работи

```
Flask сървър (Python)  ←→  Tampermonkey в браузъра
       ↓
   CSV файл
```

1. Flask зарежда URL-ите от `input_urls/dir_bg.txt` и чака.
2. Tampermonkey пита Flask: „Каква е следващата задача?"
3. Flask отговаря: „Отиди на тази страница и извлечи статиите" или „Отиди на тази страница с коментари и извлечи коментарите."
4. Tampermonkey изпълнява задачата в браузъра и праща резултатите обратно.
5. Flask записва коментарите в CSV и дава следваща задача.

### Стартиране

**Стъпка 1** — Попълнете `input_urls/dir_bg.txt`.

**Стъпка 2** — Стартирайте Flask сървъра в терминала:

```bash
source venv/bin/activate
python main.py server --log-level INFO
```

Ще видите:
```
[INFO] Loaded 2 category URL(s) into queue
[INFO] CSV writer opened | path=output/dir_bg_data_2026-04-12_00-05-23.csv
```

**Стъпка 3** — Отворете браузъра (Chrome или Firefox с Tampermonkey) и отидете на произволна dir.bg страница, например `https://dnes.dir.bg`.

Tampermonkey ще се активира автоматично след 2-3 секунди и браузърът ще започне да навигира сам.

**Стъпка 4** — Следете прогреса в терминала. Когато всички задачи приключат, Flask ще спре да получава нови заявки. Натиснете **Ctrl+C** за да спрете сървъра.

> **Важно:** Flask и браузърът трябва да работят едновременно. Не затваряйте терминала докато скрейпването е в ход.

> **Забележка:** В конзолата на браузъра (F12) можете да следите какво прави Tampermonkey в реално време. Всички действия се логват с префикс `[dir.bg-scraper]`.

---

## Изходни файлове

### CSV файлове

Намират се в директорията `output/`. Всяко пускане създава нов файл — съществуващите никога не се презаписват.

Формат на имената:
```
{сайт}_data_{дата}_{час}.csv

Примери:
  dnes_bg_data_2026-04-12_10-30-00.csv
  mediapool_bg_data_2026-04-12_11-00-00.csv
  dir_bg_data_2026-04-12_00-05-23.csv
```

### Лог файлове

Намират се в директорията `logs/`. Съдържат подробна информация за всяко пускане — полезни при проблеми.

```
dnes_bg_2026-04-12_10-30-00.log
```

---

## Описание на CSV полетата

Всеки ред в CSV файла представлява един коментар.

| Поле | Пример | Описание |
|------|--------|----------|
| `source_site` | `dir.bg` | Сайтът, от който е скрейпнат коментарът |
| `category_url` | `https://dir.bg/topic/predsrochni-izbori-2026` | Началният URL от `input_urls/`, откъдето е намерена статията |
| `article_url` | `https://dnes.dir.bg/politika/12-hilyadi-evro-...` | Линк към статията |
| `article_title` | `12 хиляди евро в пояс под дрехите...` | Заглавие на статията |
| `article_published_at` | `13:22 \| 11.04.26` | Час и дата на публикуване (оригинален формат на сайта) |
| `article_views` | `6557` | Брой прегледи на статията |
| `comment_index` | `71004968` | Вътрешно ID на коментара в системата на сайта |
| `comment` | `Тъй като водачите на листи...` | Текст на коментара |
| `author` | `Интересно` | Псевдоним на коментатора |
| `comment_date` | `2026-04-11 23:00:18` | Дата и час на публикуване на коментара |
| `likes` | `1` | Брой „харесвания" |
| `dislikes` | `0` | Брой „не харесвания" |
| `scraped_at` | `2026-04-12 00:07:21` | Момент на записване в CSV от скрейпъра |
