# --- START OF FILE Shikimori.py (ВЕРСИЯ С ИСПОЛЬЗОВАНИЕМ GRAPHQL API) ---

import os
import re
import common
from common import Log, DictString, Dict, SaveDict

# URL для ARM API, чтобы получить Shikimori ID (бывший MAL ID) по AniDB ID
ARM_API_URL_TEMPLATE = "https://arm.haglund.dev/api/v2/ids?source=anidb&include=myanimelist&id={id}"

# URL для нового GraphQL API Shikimori
SHIKIMORI_GRAPHQL_URL = "https://shikimori.one/api/graphql"

# GraphQL-запрос для получения нужных нам данных (название, описание, жанры)
SHIKIMORI_ANIME_QUERY = """
query getAnimeData($id: String!) {
  animes(ids: $id) {
    id
    russian
    description
    genres {
      russian
    }
  }
}
""".strip()

def GetMetadata(anidb_id=None):
    """
    Получает метаданные с Shikimori как отдельный источник, используя GraphQL.
    1. Находит Shikimori ID по AniDB ID через ARM API.
    2. Запрашивает данные с Shikimori GraphQL API.
    3. Возвращает собственный словарь с названием, описанием и жанрами.
    """
    Log.Info("=== Shikimori.GetMetadata() [GraphQL] ===".ljust(157, '='))
    shikimori_dict = {}

    if not anidb_id or not anidb_id.isdigit():
        Log.Info("No valid AniDB ID provided. Shikimori source skipped.")
        return shikimori_dict

    # --- 1. Получение Shikimori ID (он же MAL ID) через ARM API ---
    arm_url = ARM_API_URL_TEMPLATE.format(id=anidb_id)
    Log.Info("Attempting to fetch Shikimori ID from ARM API: {url}".format(url=arm_url))

    arm_data = common.LoadFile(filename=str(anidb_id) + '_arm.json',
                               relativeDirectory=os.path.join('Shikimori', 'json', 'arm'),
                               url=arm_url,
                               cache=CACHE_1WEEK)

    # В контексте нового API, MAL ID - это и есть ID на Shikimori
    shikimori_id = Dict(arm_data, 'myanimelist')

    if not shikimori_id:
        Log.Info("Failed to get Shikimori ID from ARM for AniDB ID {id}.".format(id=anidb_id))
        return shikimori_dict

    Log.Info("Successfully fetched Shikimori ID: {shikimori_id} for AniDB ID: {anidb_id}".format(shikimori_id=shikimori_id, anidb_id=anidb_id))

    # --- 2. Получение данных с Shikimori через GraphQL ---
    Log.Info("Attempting to fetch Shikimori data via GraphQL API...")
    
    # Формируем тело POST-запроса для GraphQL
    variables = {"id": str(shikimori_id)}
    graphql_payload = JSON.StringFromObject({"query": SHIKIMORI_ANIME_QUERY, "variables": variables})

    # Выполняем запрос
    graphql_response = common.LoadFile(
        filename=str(shikimori_id) + '_graphql.json', # Новый файл кэша, чтобы не было конфликтов
        relativeDirectory=os.path.join('Shikimori', 'json', 'graphql'),
        url=SHIKIMORI_GRAPHQL_URL,
        data=graphql_payload, # `data` указывает common.LoadFile на то, что это POST-запрос
        cache=CACHE_1WEEK
    )

    if not graphql_response or 'errors' in graphql_response:
        Log.Error("Failed to get data from Shikimori GraphQL API for ID {id}. Response: {resp}".format(id=shikimori_id, resp=graphql_response))
        return shikimori_dict

    # GraphQL возвращает массив, даже если запрошен один ID. Берем первый элемент.
    anime_list = Dict(graphql_response, 'data', 'animes', default=[])
    if not anime_list:
        Log.Info("Shikimori GraphQL API returned no anime data for ID {id}.".format(id=shikimori_id))
        return shikimori_dict
    
    anime_data = anime_list[0]

    # --- 3. Формирование словаря с данными ---

    # --- Название на русском ---
    russian_title = Dict(anime_data, 'russian')
    if russian_title:
        Log.Info("[Shikimori GraphQL] Found title: '{}'".format(russian_title))
        SaveDict(russian_title, shikimori_dict, 'title')
        SaveDict(common.SortTitle(russian_title, 'ru'), shikimori_dict, 'title_sort')
        SaveDict(-1, shikimori_dict, 'language_rank') # Приоритет для русского языка

    # --- Описание ---
    description = Dict(anime_data, 'description')
    if description:
        clean_summary = re.sub(r'\[.*?\]|<.*?>', '', description).strip()
        Log.Info("[Shikimori GraphQL] Found summary.")
        SaveDict(clean_summary, shikimori_dict, 'summary')

    # --- Жанры ---
    shikimori_genres = Dict(anime_data, 'genres')
    if shikimori_genres and isinstance(shikimori_genres, list):
        genre_list = [Dict(g, 'russian') for g in shikimori_genres if Dict(g, 'russian')]
        if genre_list:
            Log.Info("[Shikimori GraphQL] Found genres: {}".format(genre_list))
            SaveDict(sorted(genre_list), shikimori_dict, 'genres')

    Log.Info("--- return ---".ljust(157, '-'))
    Log.Info("Shikimori_dict: {}".format(DictString(shikimori_dict, 1)))
    return shikimori_dict