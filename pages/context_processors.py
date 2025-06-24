from .views import _get_sidebar_data

def sidebar_data(request):
    if request.user.is_authenticated:
        recent_songs, favourites, playlists = _get_sidebar_data(request.user)
        return {
            'recent_songs': recent_songs,
            'favourites':   favourites,
            'playlists':    playlists,
        }
    return {}
