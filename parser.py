import aiohttp
import asyncio
import datetime
from bs4 import BeautifulSoup
import cloudscraper
import functools # Для использования functools.partial с run_in_executor

urlMatches = 'https://www.hltv.org/matches'
urlEvents = 'https://www.hltv.org/calendar'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br', # brotli уже установлен, поэтому оставляем
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1', # Важно для HTTPS
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache'
}

async def getting_html_with_cloudscraper_async(url):
    print(f'Начинает сбор инфы с {url} используя cloudscraper (асинхронно)...')
    loop = asyncio.get_running_loop()
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        },
    )
    scraper.headers.update(headers) # Метод .update() добавляет/обновляет заголовки из словаря

    try:
        # Выполняем синхронный вызов scraper.get в отдельном потоке
        response = await loop.run_in_executor(
            None, # Используем пул по умолчанию
            functools.partial(scraper.get, url)
        )
        response.raise_for_status() # Вызывает исключение для статусов 4xx/5xx
        text = response.text
        print(f'Страница {url} загружена (через cloudscraper).')
        return text
    except Exception as e:
        print(f'Ошибка загрузки страницы {url} через cloudscraper: {e}.')
        # Дополнительно выведем тип ошибки для диагностики
        print(f'Тип ошибки: {type(e).__name__}')
        return None

# Функция для парсинга live матчей
def update_schedule(html_content):
    if not html_content:
        print("Не могу парсить live-матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    all_live_matches_data = []

    live_matches_container = soup.select_one('.liveMatches') # Селектор для live матчей

    if live_matches_container:
        live_matches = live_matches_container.select('.match-wrapper.live-match-container')

        for match in live_matches:
            match_data = {}

            team_names = match.select('.match-teamname')
            match_data['team1'] = team_names[0].get_text(strip=True) if len(team_names) >= 1 else 'N/A'
            match_data['team2'] = team_names[1].get_text(strip=True) if len(team_names) >= 2 else 'N/A'

            event_name_element = match.select_one('.match-event .text-ellipsis')
            match_data['event'] = event_name_element.get_text(strip=True) if event_name_element else 'N/A'

            score_elements = match.select('.current-map-score')
            match_data['combined_score'] = f'{score_elements[0].get_text(strip=True)}:{score_elements[1].get_text(strip=True)}'

            match_link_element = match.select_one('a.match-top')
            href = match_link_element.get('href') if match_link_element else None
            match_data['match_url'] = f"https://www.hltv.org{href}" if href else "N/A"

            all_live_matches_data.append(match_data)

    return all_live_matches_data

# Функция для парсинга предстоящих матчей на сегодня
def get_upcoming_matches_today(html_content):
    if not html_content:
        print("Не могу парсить предстоящие матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    upcoming_matches_today_data = []
    today = datetime.date.today()

    # Ищем общий контейнер со списками матчей, сгруппированных по событиям
    matches_list_column = soup.select_one('.matches-list-column')

    if not matches_list_column:
        print("Не найден основной столбец со списками матчей (.matches-list-column).")
        return []

    # Находим все контейнеры событий
    event_wrappers = matches_list_column.select('.matches-event-wrapper')

    if not event_wrappers:
        print("Не найдены контейнеры событий (.matches-event-wrapper).")
        return []

    for event_wrapper in event_wrappers:
        # Извлекаем название события
        event_name_element = event_wrapper.select_one('.event-headline-wrapper .event-headline-text')
        event_name = event_name_element.get_text(strip=True) if event_name_element else 'N/A Event'

        # Находим список матчей внутри текущего события
        matches_list_container = event_wrapper.select_one('.matches-list')
        if not matches_list_container:
            continue

        # Находим все отдельные матчи внутри этого списка
        match_elements = matches_list_container.select('.match-wrapper')

        for match in match_elements:
            # Проверяем, что это не live матч (атрибут live="false")
            if match.get('live') == 'false':
                match_data = {}
                match_data['event'] = event_name # Присваиваем имя текущего события

                # Время матча и Unix-таймстамп
                time_element = match.select_one('.match-time')
                if time_element and 'data-unix' in time_element.attrs:
                    unix_timestamp_ms = int(time_element['data-unix'])
                    match_datetime = datetime.datetime.fromtimestamp(unix_timestamp_ms / 1000) # Unix в секундах
                    match_date = match_datetime.date()

                    if match_date == today:
                        match_data['time'] = match_datetime.strftime("%H:%M") # Формат HH:MM
                        # Названия команд
                        team_names = match.select('.match-teamname')
                        match_data['team1'] = team_names[0].get_text(strip=True) if len(team_names) >= 1 else 'N/A'
                        match_data['team2'] = team_names[1].get_text(strip=True) if len(team_names) >= 2 else 'N/A'

                        # Формат матча (bo3, bo1 и т.д.)
                        match_format_element = match.select_one('.match-meta')
                        match_data['format'] = match_format_element.get_text(strip=True) if match_format_element else 'N/A'

                        # Ссылка на матч
                        match_link_element = match.select_one('a.match-info') # или 'a.match-teams'
                        href = match_link_element.get('href') if match_link_element else None
                        match_data['match_url'] = f"https://www.hltv.org{href}" if href else "N/A"

                        upcoming_matches_today_data.append(match_data)
                else:
                    print(f"Предупреждение: Не удалось найти время или data-unix для матча в событии '{event_name}'.")

    return upcoming_matches_today_data

async def main():
    # --- Получение Live матчей ---
    html_content = await getting_html_with_cloudscraper_async(urlMatches)
    live_matches_data = []
    if html_content:
        live_matches_data = update_schedule(html_content) 

    if live_matches_data:
        print("\n--- Полученные данные Live матчей ---")
        for i, match_info in enumerate(live_matches_data):
            print(f"Матч {i+1}:")
            print(f"  Команды: {match_info['team1']} vs {match_info['team2']}")
            print(f"  Турнир: {match_info['event']}")
            print(f"  Общий счет (X:N): {match_info['combined_score']}")
            print(f"  Ссылка: {match_info['match_url']}")
            print("-" * 20)
        print(f"\nВсего найдено Live матчей: {len(live_matches_data)}")
    else:
        print("\nLive матчи не найдены или произошла ошибка парсинга.")

    print("\n" + "=" * 50 + "\n")

    # --- Получение предстоящих матчей на сегодня ---
    upcoming_matches_today = []
    if html_content:
        upcoming_matches_today = get_upcoming_matches_today(html_content)

    if upcoming_matches_today:
        print("\n--- Полученные данные Предстоящих матчей на сегодня ---")
        # Сортируем матчи по времени, чтобы имитировать сортировку "Time"
        def sort_by_time(match):
            time_str = match.get('time', '00:00') # Используем '00:00' как запасное значение, если время не найдено
            try:
                hours, minutes = map(int, time_str.split(':'))
                return hours * 60 + minutes
            except ValueError:
                return 9999 # Отправляем непарсящиеся значения в конец списка

        sorted_upcoming_matches = sorted(upcoming_matches_today, key=sort_by_time)

        for i, match_info in enumerate(sorted_upcoming_matches):
            print(f"Предстоящий матч {i+1}:")
            print(f"  Время: {match_info['time']}")
            print(f"  Команды: {match_info['team1']} vs {match_info['team2']}")
            print(f"  Турнир: {match_info['event']}")
            print(f"  Формат: {match_info['format']}")
            print(f"  Ссылка: {match_info['match_url']}")
            print("-" * 20)
        print(f"\nВсего найдено Предстоящих матчей на сегодня: {len(sorted_upcoming_matches)}")
    else:
        print("\nПредстоящие матчи на сегодня не найдены или произошла ошибка парсинга.")

if __name__ == "__main__":
    asyncio.run(main())