from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from logger import logger

class ParserError(Exception):
    def __str__(self):
        return 'HTML content not found'

async def getting_html_with_playwright(url: str) -> str | None:
    browser = None
    logger.info(f"get page {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            await page.goto(url, timeout=60000, wait_until="networkidle")

            html_content = await page.content()
            logger.info(f"page loaded successfully {url}")
            return html_content
    except Exception as e:
        logger.error(f'Error download page {url}\n{e}')
        return None
    finally:
        if browser:
            await browser.close()


def get_live_matches(html_content: str) -> list[dict]:
    if not html_content:
        raise ParserError

    soup = BeautifulSoup(html_content, 'lxml')
    live_matches_data = []

    live_matches_container = soup.find('div', class_='matches-list-column').find('div', class_='liveMatches')

    if live_matches_container:
        live_matches = live_matches_container.find_all('div', class_='match-wrapper live-match-container')

        for j, match in enumerate(live_matches):
            live_matches_data.append(dict())
            live_matches_data[j]['url'] = match.find('a').get('href')
            live_matches_data[j]['event'] = match.find('div', class_='match-event text-ellipsis') \
                .find('div', class_='text-ellipsis').text
            live_matches_data[j]['format'] = match.find('div', class_='match-meta').text
            team_in_live = match.find_all('div', class_='match-teamname text-ellipsis')
            for i, team in enumerate(team_in_live):
                live_matches_data[j][f'team{i + 1}'] = team.text

    return live_matches_data


def get_all_upcoming_matches(html_content: str) -> list[dict]:
    if not html_content:
        raise ParserError

    soup = BeautifulSoup(html_content, 'lxml')
    match_data = []

    matches = soup.find_all('div', class_='match-zone-wrapper')

    remove_elems = 0
    for j, match in enumerate(matches):
        try:
            match_data.append(dict())
            match_data[j - remove_elems]['url'] = match.find('div', class_='match').find('a').get('href')
            match_data[j - remove_elems]['team1'] = match.find('div', class_='match-team team1') \
                .find('div', class_='text-ellipsis').text
            match_data[j - remove_elems]['team2'] = match.find('div', class_='match-team team2') \
                .find('div', class_='text-ellipsis').text
            match_data[j - remove_elems]['format'] = match.find('div', class_='match-meta').text
            match_data[j - remove_elems]['event'] = match.find('div', class_='match-event').get('data-event-headline')
            match_data[j - remove_elems]['start_time'] = int(match.get('data-zonedgrouping-entry-unix'))
        except BaseException as e:
            match_data.pop()
            remove_elems += 1
        if not match_data[-1]:
            remove_elems += 1
            match_data.pop()

    return match_data


def get_teams(html_content: str) -> list[str]:
    if not html_content:
        raise ParserError

    soup = BeautifulSoup(html_content, 'lxml')
    teams = []

    teams_box = soup.find("div", class_="ranking").find_all("div", class_="ranked-team standard-box")

    for box in teams_box:
        teams.append(box.find("span", class_="name").text)

    return teams


def get_stream_urls(html_content: str) -> dict[str]:
    if not html_content:
        raise ParserError

    soup = BeautifulSoup(html_content, 'lxml')
    urls = {}

    streams = soup.find("div", class_="streams").find_all("div", class_="stream-box")

    for stream in streams:
        box = stream.find("div", class_="stream-box-embed")
        if not box:
            continue
        urls[box.text] = box.get("data-stream-embed")

    return urls

def get_all_events(html_content: str) -> list[dict]:
    if not html_content:
        raise ParserError

    soup = BeautifulSoup(html_content, 'lxml')
    all_events = []

    live_events = soup.find_all('a', class_='a-reset ongoing-event')
    i = -1
    for event in live_events:
        try:
            all_events.append(dict())
            i += 1
            all_events[i]['name'] = event.find('div', class_='text-ellipsis').text
            all_events[i]['start_date'] = int(event.find('span', class_='col-desc').find('span').find('span')\
                .get('data-unix'))
            all_events[i]['end_date'] = int(event.find('span', class_='col-desc').find('span').find_all('span')[1]\
                                            .find('span').get('data-unix'))
        except BaseException as e:
            i -= 1
            all_events.pop()

    big_events = soup.find_all('div', class_='big-event-info')
    for event in big_events:
        try:
            all_events.append(dict())
            i += 1
            all_events[i]['name'] = event.find('div', class_='big-event-name').text
            all_events[i]['start_date'] = int(event.find('td', class_='col-value col-date').find('span')\
                                              .get('data-unix'))
            all_events[i]['end_date'] = int(event.find('td', class_='col-value col-date').find_all('span')[1]\
                                            .find('span').get('data-unix'))
        except BaseException as e:
            i -= 1
            all_events.pop()

    small_events = soup.find_all('a', class_='a-reset small-event standard-box')
    for event in small_events:
        try:
            all_events.append(dict())
            i += 1
            all_events[i]['name'] = event.find('div', class_='text-ellipsis').text
            all_events[i]['start_date'] = int(event.find('tr', class_='eventDetails')\
                                              .find_all('span', class_='col-desc')[1].find('span').find('span')\
                                              .get('data-unix'))
            all_events[i]['end_date'] = int(event.find_all('span', class_='col-desc')[1].find('span').find_all('span')[1]\
                                            .find('span').get('data-unix'))
        except BaseException as e:
            i -= 1
            all_events.pop()

    return all_events