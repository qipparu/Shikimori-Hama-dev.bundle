### TheMovieDb ###  Does movies but also series, for which i call it tsdb in metadata id ##
# TMDB_SEARCH_BY_IMDBID       = "https://api.TheMovieDb.org/3/find/tt0412142?api_key=7f4a0bd0bd3315bb832e17feda70b5cd&external_source=imdb_id"

### Imports ###
# Python Modules #
import os
import time # ИЗМЕНЕНИЕ: Добавлен импорт для cache buster
# HAMA Modules #
import common
from common import Log, DictString, Dict, SaveDict # Direct import of heavily used functions

### Variables ###
TMDB_API_KEY                = '7f4a0bd0bd3315bb832e17feda70b5cd'
ARM_API_URL_TEMPLATE        = "https://arm.haglund.dev/api/v2/ids?source=anidb&include=themoviedb&id={id}"
TMDB_MOVIE_SEARCH           = 'https://api.tmdb.org/3/search/movie?api_key=%s&query={query}&year=&language=en&include_adult=true' % TMDB_API_KEY
TMDB_DETAILS_URL            = 'https://api.themoviedb.org/3/{mode}/{id}?api_key=%s&append_to_response=credits,external_ids&language=ru' % TMDB_API_KEY
TMDB_SERIE_SEARCH_BY_TVDBID = "https://api.TheMovieDb.org/3/find/{id}?api_key=%s&external_source=tvdb_id&append_to_response=releases,credits,trailers,external_ids&language=en" % TMDB_API_KEY
TMDB_CONFIG_URL             = 'https://api.tmdb.org/3/configuration?api_key=%s' % TMDB_API_KEY
TMDB_IMAGES_URL             = 'https://api.tmdb.org/3/{mode}/{id}/images?api_key=%s' % TMDB_API_KEY


### ###
def GetMetadata(media, movie, AniDBid, TVDBid, TMDbid, IMDbid, mappingList):
  Log.Info("=== TheMovieDb.GetMetadata() ===".ljust(157, '='))
  TheMovieDb_dict = {}
  TSDbid          = ""
  tmdb_id_final   = ""
  mode            = "tv" if not movie else "movie"

  Log.Info("Provided IDs -> AniDBid: '{}', TVDBid: '{}', TMDbid: '{}', IMDbid: '{}'".format(AniDBid, TVDBid, TMDbid, IMDbid))

  # --- НОВЫЙ БЛОК: Получение TMDB ID через ARM API (самый высокий приоритет) ---
  if AniDBid and AniDBid.isdigit():
      Log.Info("Attempting to fetch TMDB ID from ARM API using AniDBid: " + AniDBid)
      arm_url = ARM_API_URL_TEMPLATE.format(id=AniDBid)
      arm_data = common.LoadFile(
          filename=str(AniDBid) + '_arm_tmdb.json',
          relativeDirectory=os.path.join('TheMovieDb', 'json', 'arm'),
          url=arm_url,
          cache=CACHE_1WEEK
      )
      tmdb_id_from_arm = Dict(arm_data, 'themoviedb')
      if tmdb_id_from_arm:
          Log.Info("Success! Found TMDB ID via ARM: " + str(tmdb_id_from_arm))
          tmdb_id_final = str(tmdb_id_from_arm)
          if not movie: TSDbid = tmdb_id_final # Если это сериал, то это tsdbid
          else: TMDbid = tmdb_id_final # Если фильм, то это tmdbid

  # --- Старая логика как fallback ---
  if not tmdb_id_final:
      Log.Info("ARM lookup failed or not applicable. Falling back to provided IDs.")
      if TMDbid:
          tmdb_id_final = TMDbid
      elif not movie and TVDBid.isdigit():
          find_url = TMDB_SERIE_SEARCH_BY_TVDBID.format(id=TVDBid)
          find_json = common.LoadFile(filename="TVDB-"+TVDBid+"_find.json", relativeDirectory=os.path.join('TheMovieDb', 'json'), url=find_url)
          if find_json and Dict(find_json, 'tv_results'):
              tmdb_id_final = str(Dict(find_json, 'tv_results')[0]['id'])
              TSDbid = tmdb_id_final
              Log.Info("Found TSDbid via TVDBid: " + TSDbid)

  if not tmdb_id_final:
      Log.Info("No usable TMDB ID found. Skipping TheMovieDb.")
      return TheMovieDb_dict, TSDbid, TMDbid, IMDbid

  Log.Info("Final TMDB ID for lookup: {}. Mode: {}".format(tmdb_id_final, mode))
  
  # --- Получение основных деталей ---
  Log.Info(("--- %s details ---" % mode).ljust(157, '-'))
  details_url = TMDB_DETAILS_URL.format(id=tmdb_id_final, mode=mode)
  json = common.LoadFile(filename="TMDB-{}-{}.json".format(mode, tmdb_id_final), relativeDirectory=os.path.join('TheMovieDb', 'json'), url=details_url)
  config_dict = common.LoadFile(filename="TMDB_CONFIG_URL.json", relativeDirectory="TheMovieDb", url=TMDB_CONFIG_URL, cache=CACHE_1MONTH)
  image_base_url = Dict(config_dict, 'images', 'secure_base_url')

  if not json:
      Log.Error("Failed to get details from TMDB for ID: " + tmdb_id_final)
  else:
    Log.Info("[ ] title: {}"                  .format(SaveDict( Dict(json, 'title') or Dict(json, 'name'),                  TheMovieDb_dict, 'title'                  )))
    Log.Info("[ ] rating: {}"                 .format(SaveDict( Dict(json, 'vote_average'),                                 TheMovieDb_dict, 'rating'                 )))
    Log.Info("[ ] tagline: {}"                .format(SaveDict( Dict(json, 'tagline'),                                      TheMovieDb_dict, 'tagline'                )))
    Log.Info("[ ] summary: {}"                .format(SaveDict( Dict(json, 'overview'),                                     TheMovieDb_dict, 'summary'                )))
    Log.Info("[ ] originally_available_at: {}".format(SaveDict( Dict(json, 'first_air_date') or Dict(json, 'release_date'), TheMovieDb_dict, 'originally_available_at')))
    if Dict(json, 'belongs_to_collection', 'name'):  Log.Info("[ ] collections: {}".format(SaveDict( [ Dict(json, 'belongs_to_collection', 'name')], TheMovieDb_dict, 'collections')))
    if Dict(json, 'genres'):                         Log.Info("[ ] genres: {}"     .format(SaveDict( sorted([ Dict(genre, 'name') for genre in Dict(json, 'genres', default=[]) ]), TheMovieDb_dict, 'genres')))
    
    if not IMDbid and Dict(json, 'external_ids', 'imdb_id'):
        IMDbid = Dict(json, 'external_ids', 'imdb_id')
        Log.Info("[ ] Found IMDB ID via TMDB: " + IMDbid)

    for studio in Dict(json, 'production_companies', default=[]):
      if studio['id'] <= json['production_companies'][0]['id']:
        Log.Info("[ ] studio: {}".format(SaveDict( studio['name'].strip(), TheMovieDb_dict, 'studio')))

  # --- Получение изображений ---
  Log.Info("--- Fetching images ---".ljust(157, '-'))
  
  poster_langs_pref = Prefs['TMDbPosterLanguages'].strip()
  # ИЗМЕНЕНИЕ: Добавлена логика cache buster
  if poster_langs_pref.lower() == 'all' or not poster_langs_pref:
      lang_query_param = ""
      Log.Info("TMDb poster languages set to 'all', fetching for all languages.")
  else:
      cache_buster = str(int(time.time()))
      langs_with_buster = poster_langs_pref + "," + cache_buster
      lang_query_param = "&include_image_language=" + langs_with_buster
      Log.Info("Using TMDb poster language filter with API cache buster: " + langs_with_buster)

  force_refresh = Prefs['force_tmdb_poster_refresh']
  image_list_cache_time = 0 if force_refresh else CACHE_1WEEK
  if force_refresh:
      Log.Info("Force refreshing TMDB poster list (agent cache disabled).")
  
  images_url = TMDB_IMAGES_URL.format(id=tmdb_id_final, mode=mode) + lang_query_param
  
  images_json = common.LoadFile(
      filename="TMDB-images-{}-{}.json".format(mode, tmdb_id_final),
      relativeDirectory=os.path.join('TheMovieDb', 'json'),
      url=images_url,
      cache=image_list_cache_time
  )
  
  if images_json and image_base_url:
    
    lang_priority = [lang.strip() for lang in Prefs['PosterLanguagePriority'].split(',')]
    Log.Info("Using language priority for sorting: {}".format(lang_priority))

    def sort_key(item):
        lang = item.get('iso_639_1') or 'xx'
        rating = item.get('vote_average', 0)
        height = item.get('height', 0)
        width = item.get('width', 0)
        resolution = height * width
        
        try:
            priority = lang_priority.index(lang)
        except ValueError:
            priority = len(lang_priority)

        return (priority, -resolution, -rating)
    
    def get_rank(image_type, lang, adjustment, priority_boost=0):
        source = 'TheMovieDb'
        source_priority_list = [s.strip() for s in Prefs[image_type].split(',')]
        try:
            source_rank = source_priority_list.index(source)
        except ValueError:
            source_rank = len(source_priority_list)
        
        try:
            lang_rank = lang_priority.index(lang)
        except ValueError:
            lang_rank = len(lang_priority)

        final_rank = (source_rank * 20) + (lang_rank * 5) + adjustment + 1 - priority_boost
        return min(final_rank, 100)

    sorted_posters = sorted(Dict(images_json, 'posters', default=[]), key=sort_key)
    for i, poster in enumerate(sorted_posters):
        lang = poster.get('iso_639_1') or 'xx'
        rank = get_rank('posters', lang, i)
        poster_url = image_base_url + 'original' + poster.get('file_path')
        Log.Info("[ ] Poster (lang: {}, rank: {}, res: {}x{}, rating: {}): {}".format(lang, rank, poster.get('width'), poster.get('height'), poster.get('vote_average'), poster_url))
        SaveDict(
            (os.path.join('TheMovieDb', 'poster', poster.get('file_path').lstrip('/')), rank, None),
            TheMovieDb_dict, 'posters', poster_url
        )

    sorted_backdrops = sorted(Dict(images_json, 'backdrops', default=[]), key=sort_key)
    for i, backdrop in enumerate(sorted_backdrops):
        lang = backdrop.get('iso_639_1') or 'xx'
        rank = get_rank('art', lang, i)
        art_url = image_base_url + 'original' + backdrop.get('file_path')
        Log.Info("[ ] Art (lang: {}, rank: {}, res: {}x{}, rating: {}): {}".format(lang, rank, backdrop.get('width'), backdrop.get('height'), backdrop.get('vote_average'), art_url))
        SaveDict(
            (os.path.join('TheMovieDb', 'artwork', backdrop.get('file_path').lstrip('/')), rank, image_base_url + 'w300' + backdrop.get('file_path')),
            TheMovieDb_dict, 'art', art_url
        )

    if not movie and media and hasattr(media, 'seasons'):
        Log.Info("--- Fetching TMDB season images ---".ljust(157, '-'))
        TMDB_SEASON_IMAGES_URL_TEMPLATE = 'https://api.themoviedb.org/3/tv/{id}/season/{season_number}/images?api_key=%s' % TMDB_API_KEY
        
        prioritize_season_posters = Prefs['prioritize_season_poster'] and len(media.seasons) == 1

        for local_season_num_str in media.seasons:
            if not str(local_season_num_str).isdigit():
                continue
            
            season_to_fetch = local_season_num_str
            if len(media.seasons) == 1 and local_season_num_str == '1':
                default_season = Dict(mappingList, 'defaulttvdbseason')
                if default_season and default_season.isdigit():
                    season_to_fetch = default_season
            
            Log.Info("Processing TMDB images for local season {} (fetching as remote season {})".format(local_season_num_str, season_to_fetch))
            
            season_images_url = TMDB_SEASON_IMAGES_URL_TEMPLATE.format(id=tmdb_id_final, season_number=season_to_fetch) + lang_query_param
            
            season_images_json = common.LoadFile(
                filename="TMDB-season-images-{}-{}.json".format(tmdb_id_final, season_to_fetch),
                relativeDirectory=os.path.join('TheMovieDb', 'json', 'seasons'),
                url=season_images_url,
                cache=image_list_cache_time
            )
            
            if season_images_json and Dict(season_images_json, 'posters'):
                sorted_season_posters = sorted(Dict(season_images_json, 'posters', default=[]), key=sort_key)
                
                for i, poster in enumerate(sorted_season_posters):
                    lang = poster.get('iso_639_1') or 'xx'
                    poster_url = image_base_url + 'original' + poster.get('file_path')
                    poster_filename = poster.get('file_path').lstrip('/')
                    cache_path = os.path.join('TheMovieDb', 'poster', 'seasons', tmdb_id_final, poster_filename)

                    rank = get_rank('posters', lang, i)
                    Log.Info("[ ] Season {} Poster (lang: {}, rank: {}, res: {}x{}): {}".format(local_season_num_str, lang, rank, poster.get('width'), poster.get('height'), poster_url))
                    SaveDict(
                        (cache_path, rank, None),
                        TheMovieDb_dict, 'seasons', str(local_season_num_str), 'posters', poster_url
                    )

                    if prioritize_season_posters:
                        priority_rank = get_rank('posters', lang, i, priority_boost=20)
                        Log.Info("    -> Prioritizing as series poster with rank {}".format(priority_rank))
                        SaveDict(
                            (cache_path, priority_rank, None),
                            TheMovieDb_dict, 'posters', poster_url
                        )

  Log.Info("--- return ---".ljust(157, '-'))
  Log.Info("TheMovieDb_dict: {}".format(DictString(TheMovieDb_dict, 4)))
  return TheMovieDb_dict, TSDbid, TMDbid, IMDbid

### TMDB movie search ###
def Search(results, media, lang, manual, movie):
  Log.Info("=== TheMovieDb.Search() ===".ljust(157, '='))
  orig_title = String.Quote(media.name if manual and movie else media.title if movie else media.show)
  maxi = 0
  
  Log.Info("TMDB  - url: " + TMDB_MOVIE_SEARCH.format(query=orig_title))
  try:
    json = JSON.ObjectFromURL(TMDB_MOVIE_SEARCH.format(query=orig_title), sleep=2.0, headers=common.COMMON_HEADERS, cacheTime=CACHE_1WEEK * 2)
  except Exception as e:
    Log.Error("get_json - Error fetching JSON page '%s', Exception: '%s'" %( TMDB_MOVIE_SEARCH.format(query=orig_title), e))
  else:
    if isinstance(json, dict) and 'results' in json:
      for movie_item in json['results']:
        a, b  = orig_title, movie_item['title'].encode('utf-8')
        score = 100 - 100*Util.LevenshteinDistance(a,b) / max(len(a),len(b)) if a!=b else 100
        if maxi<score:  maxi = score
        Log.Info("TMDB  - score: '%3d', id: '%6s', title: '%s'" % (score, movie_item['id'],  movie_item['title']) )
        results.Append(MetadataSearchResult(id="tmdb-"+str(movie_item['id']), name="{} [{}-{}]".format(movie_item['title'], "tmdb", movie_item['id']), year=None, lang=lang, score=score) )
  return maxi