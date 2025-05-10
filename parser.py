import datetime
from bs4 import BeautifulSoup
import asyncio

# ИМПОРТЫ ДЛЯ PLAYWRIGHT
from playwright.async_api import async_playwright

# Константы URL
urlMatches = 'https://www.hltv.org/matches'
urlEvents = 'https://www.hltv.org/events#tab-ALL'

# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ HTML С ИСПОЛЬЗОВАНИЕМ PLAYWRIGHT
async def getting_html_with_playwright(url: str) -> str | None:
    print(f'Начинает сбор инфы с {url} используя Playwright (асинхронно)...')
    browser = None # Инициализируем browser вне try, чтобы он был доступен в finally

    try:
        async with async_playwright() as p:
            # Запускаем Chromium браузер.
            # headless=True: браузер запускается в фоновом режиме без графического интерфейса.
            # Для отладки headless=False, чтобы видеть окно браузера.
            browser = await p.chromium.launch(headless=True) # <-- Можно попробовать headless=False для отладки
            
            # Создаем новую страницу браузера с пользовательским User-Agent.
            # Помогает имитировать обычный браузер.
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Переходим на URL. timeout установлен в 60 секунд (60000 миллисекунд),
            await page.goto(url, timeout=60000, wait_until="networkidle")
            
            # Получаем HTML-содержимое текущей страницы.
            html_content = await page.content()
            print(f'Страница {url} загружена (через Playwright).')
            return html_content
    except Exception as e:
        print(f'Ошибка загрузки страницы {url} через Playwright: {e}.')
        print(f'Тип ошибки: {type(e).__name__}')
        return None
    finally:
        # Закрыть браузер, чтобы освободить ресурсы системы.
        if browser:
            await browser.close()

# Функция для парсинга live матчей
def get_live_matches(html_content: str) -> list[dict]:
    if not html_content:
        print("Не могу парсить live-матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    live_matches_data = []

    # Находим контейнер, содержащий все live-матчи
    live_matches_container = soup.find('div', class_='matches-list-column')

    if live_matches_container:
        # Ищем каждый отдельный live-матч внутри контейнера
        live_matches = live_matches_container.find_all('div', class_='match-wrapper live-match-container')
        
        for j, match in enumerate(live_matches):
            print(live_matches)
            live_matches_data.append(dict())
            live_matches_data[j]['url'] = match.find('a').get('href')
            live_matches_data[j]['event'] = match.find('div', class_='match-event text-ellipsis')\
                .find('div', class_='text-ellipsis').text
            live_matches_data[j]['format'] = match.find('div', class_='match-meta').text
            # Get team
            team_in_live = match.find_all('div', class_='match-teamname text-ellipsis')
            for i, team in enumerate(team_in_live):
                live_matches_data[j][f'team{i+1}'] = team.text

    return live_matches_data

def get_all_upcoming_matches(html_content: str) -> list[dict]:
    if not html_content:
        print("Не могу парсить предстоящие матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    match_data = []

    print(f"Начинаем сбор всех предстоящих матчей со страницы...")

    # Находим все заголовки дневных разделов
    sections = soup.find_all('div', class_='matches-list-section')

    for section in sections: 
        matches = section.find_all('div', class_='match')
        for j, match in enumerate(matches):
            try:
                match_data.append(dict())
                match_data[j]['url'] = match.find('a').get('href')
                match_data[j]['team1'] = match.find('div', class_='match-team team1')\
                   .find('div', class_='text-ellipsis').text
                match_data[j]['team2'] = match.find('div', class_='match-team team2')\
                    .find('div', class_='text-ellipsis').text
                match_data[j]['format'] = match.find('div', class_='match-meta').text
                match_data[j]['event'] = match.find('div', class_='match-event').text
                match_data[j]['start_time'] = match.find('div', class_='match-time').get('data-unix') 
            except BaseException as e:
                print(e)
                match_data.pop()
            
    print(f"Завершён сбор всех предстоящих матчей. Найдено: {len(match_data)}.")
    return match_data

