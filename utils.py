import os
import re
import base64
import requests
from dotenv import load_dotenv
from telethon import events, Button
import logging
from database import check_user_privacy_accepted, add_user
from config import PRIVACY_POLICY_MESSAGE, BUTTON_ACCEPT
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

LANGUAGE_MAP = {
    "hi": "Hindi", "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ta": "Tamil", "te": "Telugu"
}

def convert_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.2f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"

def normalize_query(query):
    query = re.sub(r'\s+', ' ', query).strip().lower()
    query = re.sub(r'season\s+(\d+)', lambda m: f"s{int(m.group(1)):02d}", query)
    query = re.sub(r'episode\s+(\d+)', lambda m: f"e{int(m.group(1)):02d}", query)
    query = re.sub(r'(s)(\d{1})\b', lambda m: f"{m.group(1)}{int(m.group(2)):02d}", query)
    query = re.sub(r'(e)(\d{1})\b', lambda m: f"{m.group(1)}{int(m.group(2)):02d}", query)
    return query

def fetch_tmdb_details(query):
    original_query = query
    query = re.sub(r'\s+', ' ', query).strip().lower()
    season_match = re.search(r'(?:season\s+|s)(\d{1,2})\b', query)
    episode_match = re.search(r'(?:episode\s+|e)(\d{1,2})\b', query)
    season_num = int(season_match.group(1)) if season_match else None
    episode_num = int(episode_match.group(1)) if episode_match else None
    base_title = re.sub(r'(season\s+\d+|s\d{2}|episode\s+\d+|e\d{2}|s\d{2}e\d{2})', '', query).strip()

    search_url = f"{TMDB_BASE_URL}/search/multi?api_key={TMDB_API_KEY}&query={base_title}"
    response = requests.get(search_url)
    if response.status_code != 200 or not response.json().get("results"):
        return None
    result = response.json()["results"][0]
    media_type = result["media_type"]
    name = result.get("title") or result.get("name", base_title)
    poster_path = result.get("poster_path")
    poster_url = f"{TMDB_IMAGE_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/150"
    details = {"type": "Movie" if media_type == "movie" else "Series", "name": name, "poster_url": poster_url}

    release_date = result.get("release_date") or result.get("first_air_date")
    if release_date:
        details["release_line"] = f"Release Date :- {release_date} IN\n"
    vote_average = result.get("vote_average")
    if vote_average:
        details["rating_line"] = f"Rating :- {round(vote_average, 1)}\n"

    if media_type == "movie":
        movie_details_url = f"{TMDB_BASE_URL}/movie/{result['id']}?api_key={TMDB_API_KEY}&append_to_response=release_dates"
        movie_response = requests.get(movie_details_url).json()
        runtime = movie_response.get("runtime")
        if runtime:
            hours, minutes = divmod(runtime, 60)
            details["duration_line"] = f"Duration :- {hours}h {minutes}m\n"
    elif media_type == "tv":
        series_details_url = f"{TMDB_BASE_URL}/tv/{result['id']}?api_key={TMDB_API_KEY}"
        series_response = requests.get(series_details_url).json()
        seasons = series_response.get("number_of_seasons")
        if seasons:
            details["season_line"] = f"Total Season :- {seasons}\n"
        episode_run_time = series_response.get("episode_run_time")
        if episode_run_time and episode_run_time[0]:
            details["duration_line"] = f"Avg Episode Duration :- {episode_run_time[0]}m\n"
        
        if season_num:
            season_url = f"{TMDB_BASE_URL}/tv/{result['id']}/season/{season_num}?api_key={TMDB_API_KEY}"
            season_response = requests.get(season_url)
            if season_response.status_code == 200:
                season_data = season_response.json()
                details["type"] = f"Series - Season {season_num}"
                details["season_line"] = f"Season {season_num} Episodes :- {len(season_data.get('episodes', []))}\n"
                if season_data.get("poster_path"):
                    details["poster_url"] = f"{TMDB_IMAGE_BASE_URL}{season_data['poster_path']}"
                if episode_num:
                    episode = next((ep for ep in season_data.get("episodes", []) if ep["episode_number"] == episode_num), None)
                    if episode:
                        details["type"] = f"Series - Season {season_num} Episode {episode_num}"
                        details["name"] = f"{name} - {episode['name']}"
                        details["release_line"] = f"Air Date :- {episode.get('air_date', '')} IN\n" if episode.get("air_date") else ""
                        details["duration_line"] = f"Duration :- {episode.get('runtime', episode_run_time[0] if episode_run_time else 0)}m\n"
                        if episode.get("vote_average"):
                            details["rating_line"] = f"Rating :- {round(episode['vote_average'], 1)}\n"

    language = result.get("original_language")
    if language:
        details["audio_line"] = f"Original Audio :- {LANGUAGE_MAP.get(language, language.upper())}\n"
    genres = [g["name"] for g in requests.get(f"{TMDB_BASE_URL}/{media_type}/{result['id']}?api_key={TMDB_API_KEY}").json().get("genres", [])]
    if genres:
        details["genre_line"] = f"Genre :- {' '.join(f'#{g.lower()}' for g in genres)}\n"
    video_url = f"{TMDB_BASE_URL}/{media_type}/{result['id']}/videos?api_key={TMDB_API_KEY}"
    video_response = requests.get(video_url).json()
    trailer_key = next((v["key"] for v in video_response.get("results", []) if v["type"] == "Trailer" and v["site"] == "YouTube"), None)
    if trailer_key:
        details["trailer_line"] = f"Trailer :- <a href='https://www.youtube.com/watch?v={trailer_key}'>Click Here</a>\n"
    providers = requests.get(f"{TMDB_BASE_URL}/{media_type}/{result['id']}/watch/providers?api_key={TMDB_API_KEY}").json().get("results", {}).get("IN", {}).get("flatrate", [])
    if providers:
        provider_names = ", ".join(p["provider_name"] for p in providers)
        details["platforms_line"] = f"Platforms :- {provider_names}\n"
    for key in ["release_line", "rating_line", "duration_line", "season_line", "audio_line", "genre_line", "trailer_line", "platforms_line"]:
        details.setdefault(key, "")
    return details

def generate_deep_link(bot_username: str, query: str) -> str:
    encoded_query = base64.urlsafe_b64encode(query.encode('utf-8')).decode('utf-8').rstrip('=')
    return f"https://t.me/{bot_username}?start={encoded_query}"

def decode_deep_link(encoded_query: str) -> str:
    padded_query = encoded_query + '=' * (4 - len(encoded_query) % 4)
    return base64.urlsafe_b64decode(padded_query.encode('utf-8')).decode('utf-8')

async def check_privacy_policy(client, event, users_collection, callback=None):
    user_id = event.sender_id
    logger.info(f"Checking privacy for user {user_id} in event {event.__class__.__name__}")
    if not check_user_privacy_accepted(users_collection, user_id):
        logger.info(f"User {user_id} not accepted, sending privacy policy")
        add_user(users_collection, user_id)
        msg = await event.reply(
            PRIVACY_POLICY_MESSAGE,
            buttons=[Button.inline(BUTTON_ACCEPT, data=f"accept_privacy:{user_id}")]
        )
        return False, msg
    logger.info(f"User {user_id} already accepted privacy policy")
    return True, None

def get_current_datetime():
    return datetime.now()