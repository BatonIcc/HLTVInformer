import datetime
from bs4 import BeautifulSoup
import asyncio
import pytz

# ИМПОРТЫ ДЛЯ PLAYWRIGHT
from playwright.async_api import async_playwright

# Константы URL
urlMatches = 'https://www.hltv.org/matches'
urlEvents = 'https://www.hltv.org/calendar'

# Определяем Московский часовой пояс
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ HTML С ИСПОЛЬЗОВАНИЕМ PLAYWRIGHT
async def getting_html_with_playwright(url: str) -> str | None:
    """
    Асинхронно получает HTML-содержимое страницы по заданному URL,
    используя Playwright для автоматизации браузера.

    Args:
        url (str): URL страницы для получения.

    Returns:
        str | None: HTML-содержимое страницы, если успешно, иначе None.
    """
    print(f'Начинает сбор инфы с {url} используя Playwright (асинхронно)...')
    browser = None # Инициализируем browser вне try, чтобы он был доступен в finally

    try:
        async with async_playwright() as p:
            # Запускаем Chromium браузер.
            # headless=True: браузер запускается в фоновом режиме без графического интерфейса.
            # Для отладки headless=False, чтобы видеть окно браузера.
            browser = await p.chromium.launch(headless=True)
            
            # Создаем новую страницу браузера с пользовательским User-Agent.
            # Помогает имитировать обычный браузер.
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            # Переходим на URL. timeout установлен в 60 секунд (60000 миллисекунд),
            # wait_until="networkidle" ожидает, пока не будет 0 сетевых запросов в течение 500мс.
            # Это позволяет дождаться загрузки динамического контента.
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
# def update_schedule(html_content: str) -> list[dict]:
    """
    Парсит HTML-контент для извлечения информации о текущих (live) матчах.

    Args:
        html_content (str): HTML-содержимое страницы HLTV /matches.

    Returns:
        list[dict]: Список словарей, где каждый словарь содержит данные о live-матче.
    """
    if not html_content:
        print("Не могу парсить live-матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    all_live_matches_data = []

    # Находим контейнер, содержащий все live-матчи
    live_matches_container = soup.select_one('.liveMatches')

    if live_matches_container:
        # Ищем каждый отдельный live-матч внутри контейнера
        live_matches = live_matches_container.select('.match-wrapper.live-match-container')

        for match in live_matches:
            match_data = {}

            # Извлекаем названия команд
            team_names = match.select('.match-teamname')
            match_data['team1'] = team_names[0].get_text(strip=True) if len(team_names) >= 1 else 'N/A'
            match_data['team2'] = team_names[1].get_text(strip=True) if len(team_names) >= 2 else 'N/A'

            # Извлекаем название события/турнира
            event_name_element = match.select_one('.match-event .text-ellipsis')
            match_data['event'] = event_name_element.get_text(strip=True) if event_name_element else 'N/A'

            # Извлекаем текущий счет матча
            score_elements = match.select('.current-map-score')
            if len(score_elements) >= 2:
                match_data['combined_score'] = f'{score_elements[0].get_text(strip=True)}:{score_elements[1].get_text(strip=True)}'
            else:
                match_data['combined_score'] = 'N/A Score'

            # Извлекаем ссылку на матч
            match_link_element = match.select_one('a.match-top')
            href = match_link_element.get('href') if match_link_element else None
            match_data['match_url'] = f"https://www.hltv.org{href}" if href else "N/A"

            all_live_matches_data.append(match_data)

    return all_live_matches_data

# Функция для парсинга предстоящих матчей на сегодня с учетом Московского часового пояса
def get_upcoming_matches_today(html_content: str) -> list[dict]:
    """
    Парсит HTML-содержимое для извлечения информации о предстоящих матчах,
    запланированных на сегодня, с учетом Московского часового пояса.

    Args:
        html_content (str): HTML-содержимое страницы HLTV /matches.

    Returns:
        list[dict]: Список словарей, где каждый словарь содержит данные о предстоящем матче.
    """
    if not html_content:
        print("Не могу парсить предстоящие матчи: HTML-контент отсутствует.")
        return []

    soup = BeautifulSoup(html_content, 'lxml')
    upcoming_matches_today_data = []
    
    # Получаем текущую дату в Московском часовом поясе
    today_in_moscow = datetime.datetime.now(MOSCOW_TZ).date()
    today_str_for_headline = today_in_moscow.strftime("%Y-%m-%d")
    print(f"Ищем раздел матчей на сегодня ({today_str_for_headline}) в Московском часовом поясе...")

    # Находим все заголовки дневных разделов
    daily_headlines = soup.select('.matches-list-headline')

    found_today_section = False
    for headline in daily_headlines:
        headline_text = headline.get_text(strip=True)
        
        # Проверяем, содержит ли заголовок дату в ожидаемом формате
        if ' - ' in headline_text:
            try:
                # Извлекаем часть с датой
                headline_date_str = headline_text.split(' - ')[1]
                
                # Сравниваем дату из заголовка с сегодняшней датой
                if headline_date_str == today_str_for_headline:
                    print(f"Найден раздел для сегодняшней даты: {headline_text}")
                    found_today_section = True
                    
                    # Находим контейнер со списком матчей, который следует за этим заголовком дня
                    matches_list_container = headline.find_next_sibling('.matches-list')

                    if matches_list_container:
                        # Теперь ищем все отдельные матчи внутри этого дневного списка
                        match_elements = matches_list_container.select('.match-wrapper')

                        for match in match_elements:
                            match_data = {}
                            
                            # Убеждаемся, что это не live матч (атрибут live="false")
                            if match.get('live') == 'false':
                                # Время матча
                                time_element = match.select_one('.match-time')
                                if time_element and 'data-unix' in time_element.attrs:
                                    unix_timestamp_ms = int(time_element['data-unix'])
                                    # Конвертируем Unix timestamp (который обычно в UTC) в datetime в UTC
                                    utc_datetime = datetime.datetime.fromtimestamp(unix_timestamp_ms / 1000, tz=pytz.utc)
                                    # Конвертируем в Московский часовой пояс
                                    moscow_match_datetime = utc_datetime.astimezone(MOSCOW_TZ)
                                    
                                    # Сверяем дату матча (в Московском часовом поясе) с сегодняшней датой (в Московском часовом поясе)
                                    if moscow_match_datetime.date() == today_in_moscow:
                                        match_data['time'] = moscow_match_datetime.strftime("%H:%M")
                                    else:
                                        # Если дата матча (в МСК) не совпадает с сегодняшней датой (в МСК), пропускаем его
                                        continue 
                                else:
                                    match_data['time'] = 'N/A Time'
                                    print("Предупреждение: Не удалось найти время или data-unix для матча.")
                                    continue # Пропускаем матч, если не удалось найти время для проверки

                                # Названия команд
                                team_names = match.select('.match-teamname')
                                match_data['team1'] = team_names[0].get_text(strip=True) if len(team_names) >= 1 else 'N/A'
                                match_data['team2'] = team_names[1].get_text(strip=True) if len(team_names) >= 2 else 'N/A'

                                # Название турнира/события
                                event_name_element = match.select_one('.match-event .text-ellipsis')
                                match_data['event'] = event_name_element.get_text(strip=True) if event_name_element else 'N/A Event'

                                # Формат матча (bo1, bo3 и т.д.)
                                match_format_element = match.select_one('.match-meta')
                                match_data['format'] = match_format_element.get_text(strip=True) if match_format_element else 'N/A'

                                # Ссылка на матч
                                match_link_element = match.select_one('a.match-info')
                                href = match_link_element.get('href') if match_link_element else None
                                match_data['match_url'] = f"https://www.hltv.org{href}" if href else "N/A"

                                upcoming_matches_today_data.append(match_data)
                        
                        # Если мы нашли и обработали сегодняшнюю секцию, можно выйти из цикла
                        break 
                    else:
                        print(f"Предупреждение: Не найден контейнер matches-list для раздела '{headline_text}'.")
                        continue # Если контейнер не найден, переходим к следующему заголовку дня
            except IndexError:
                print(f"Предупреждение: Некорректный формат заголовка даты: '{headline_text}'")
                continue
            except Exception as e:
                print(f"Ошибка при парсинге заголовка или матчей в секции '{headline_text}': {e}")
                continue
    
    if not found_today_section:
        print(f"Не найдена секция с матчами на сегодня ({today_str_for_headline}) на странице.")

    return upcoming_matches_today_data

async def main():
    html_content = await getting_html_with_playwright(urlMatches)
    
    # --- Получение Live матчей ---
    # live_matches_data = []
    # if html_content:
    #     live_matches_data = update_schedule(html_content) 

    # if live_matches_data:
    #     print("\n--- Полученные данные Live матчей ---")
    #     for i, match_info in enumerate(live_matches_data):
    #         print(f"Матч {i+1}:")
    #         print(f"   Команды: {match_info['team1']} vs {match_info['team2']}")
    #         print(f"   Турнир: {match_info['event']}")
    #         print(f"   Общий счет (X:N): {match_info['combined_score']}")
    #         print(f"   Ссылка: {match_info['match_url']}")
    #         print("-" * 20)
    #     print(f"\nВсего найдено Live матчей: {len(live_matches_data)}")
    # else:
    #     print("\nLive матчи не найдены или произошла ошибка парсинга.")

    # print("\n" + "=" * 50 + "\n")

    # --- Получение предстоящих матчей на сегодня ---
    upcoming_matches_today = []
    if html_content:
        upcoming_matches_today = get_upcoming_matches_today(html_content)

    if upcoming_matches_today:
        print("\n--- Полученные данные Предстоящих матчей на сегодня ---")
        # Сортируем матчи по времени
        def sort_by_time(match):
            time_str = match.get('time', '00:00') 
            try:
                hours, minutes = map(int, time_str.split(':'))
                return hours * 60 + minutes
            except ValueError:
                return 9999 # Если время не может быть преобразовано, ставим его в конец

        sorted_upcoming_matches = sorted(upcoming_matches_today, key=sort_by_time)

        for i, match_info in enumerate(sorted_upcoming_matches):
            print(f"Предстоящий матч {i+1}:")
            print(f"   Время: {match_info['time']}")
            print(f"   Команды: {match_info['team1']} vs {match_info['team2']}")
            print(f"   Турнир: {match_info['event']}")
            print(f"   Формат: {match_info['format']}")
            print(f"   Ссылка: {match_info['match_url']}")
            print("-" * 20)
        print(f"\nВсего найдено Предстоящих матчей на сегодня: {len(sorted_upcoming_matches)}")
    else:
        print("\nПредстоящие матчи на сегодня не найдены или произошла ошибка парсинга.")

if __name__ == "__main__":
    # Запускаем основную асинхронную функцию.
    asyncio.run(main())