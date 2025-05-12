from Bot import bot, dp, db_manager, mailing
from parser import *
import asyncio
from datetime import datetime, timezone, timedelta

CHECK_INTERVAL = 60 * 60 * 24
last_update = 0
base_url = 'https://www.hltv.org'
events_url = 'https://www.hltv.org/events#tab-ALL'
teams_url = 'https://www.hltv.org/ranking/teams/'
matches_url = 'https://www.hltv.org/matches/'

async def get_stream_links(match_url: str) -> dict:
    while 1:
        try:
            response = await getting_html_with_playwright(match_url)
            urls = get_stream_urls(response)
            if urls:
                return urls
        except BaseException as err:
            logger.error(f"Error in get_stream_links {err}")

async def update_matches():
    global CHECK_INTERVAL
    while 1:
        try:
            response = await getting_html_with_playwright(matches_url)
            matches = get_all_upcoming_matches(response)
            live_matches = get_live_matches(response)
            if matches:
                break
        except BaseException as err:
            logger.error(f"Error in update_matches {err}")

    start_times = []
    matches_url_list = []
    for match in matches:
        ongoing = match['start_time'] / 1000 - datetime.now(timezone.utc).timestamp() < timedelta(minutes=15).seconds
        db_manager.update_match(event_name=match['event'],
                                start_time=datetime.fromtimestamp(match['start_time'] / 1000, tz=timezone.utc),
                                ongoing=ongoing,
                                team_names=[match['team1'], match['team2']], url=base_url+match['url'], format=match['format'])
        matches_url_list.append(base_url+match['url'])

        start_times.append(int(match['start_time'] / 1000))

    CHECK_INTERVAL = -1
    for i in range(len(start_times)):
        CHECK_INTERVAL = min(start_times[i:]) - datetime.now(timezone.utc).timestamp() - timedelta(minutes=10).seconds
        if CHECK_INTERVAL > 0:
            break

    for match in live_matches:
        db_manager.update_match(event_name=match['event'], ongoing=True, format=match['format'],
                                team_names=[match['team1'], match['team2']], url=base_url+match['url'])
        match_streams = await get_stream_links(base_url+match['url'])
        for stream_name in match_streams.keys():
            db_manager.add_stream_to_match(match_url=base_url+match['url'], stream_name=stream_name,
                                           stream_link=match_streams[stream_name])

        matches_url_list.append(base_url + match['url'])

    db_manager.delete_matches_not_in_list(matches_url_list)

async def update_teams_events():
    while 1:
        try:
            response = await getting_html_with_playwright(teams_url)
            teams = get_teams(response)
            if teams:
                break
        except BaseException as err:
            logger.error(f"Error in update_teams {err}")

    while 1:
        try:
            response = await getting_html_with_playwright(events_url)
            events = get_all_events(response)
            if events:
                break
        except BaseException as err:
            logger.error(f"Error in update_events {err}")

    for team in teams:
        db_manager.create_team(team)

    for event in events:
        db_manager.update_event(name=event['name'],
                                start_date=datetime.fromtimestamp(event['start_date'] / 1000, tz=timezone.utc),
                                end_date=datetime.fromtimestamp(event['end_date'] / 1000, tz=timezone.utc))

    db_manager.delete_ended_events()

async def update_data():
    logger.info('start update')
    global last_update
    if datetime.now(timezone.utc).timestamp() - last_update >= 60 * 60 * 24:
        await update_teams_events()
        last_update = datetime.now(timezone.utc).timestamp()
    await update_matches()
    await mailing()

async def schedule_event_checker():
    while True:
        try:
            await update_data()
        except Exception as err:
            logger.error(f"Error in schedule_event_checker {err}")
        await asyncio.sleep(CHECK_INTERVAL)

async def main():
    asyncio.create_task(schedule_event_checker())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())