# pages/urls.py

from django.urls import path
from . import views
from .views import TrackCreateView, TrackUpdateView, TrackDeleteView


urlpatterns = [
    path("", views.home, name="home"),

    # Track detail + actions
    path("track/<int:pk>/", views.track, name="track"),
    path("track/<int:pk>/fav/", views.toggle_favourite, name="toggle_favourite"),
    path("track/<int:pk>/add-to-playlist/", views.add_to_playlist, name="add_to_playlist"),

    # Playlist views
    path("playlist/<int:pk>/", views.playlist_detail, name="playlist_detail"),
    # Move a track up/down within a playlist
    path(
        "playlist/<int:pk>/track/<int:track_pk>/move/",
        views.move_track,
        name="playlist_move_track"
    ),
    # Remove a track from a playlist
    path(
        "playlist/<int:pk>/track/<int:track_pk>/remove/",
        views.remove_track,
        name="playlist_remove_track"
    ),

    # Public playlist view
    path("playlist/<int:pk>/view/", views.public_playlist_view, name="playlist_public"),


    # User favourites
    path("favourites/", views.my_favourites, name="my_favourites"),

    # Profile settings
    path("profile/settings/", views.profile_settings, name="profile_settings"),

    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),


    # Track CRUD for Curators
    path('tracks/add/', TrackCreateView.as_view(), name='track-add'),
    path('tracks/<int:pk>/edit/', TrackUpdateView.as_view(), name='track-edit'),
    path('tracks/<int:pk>/delete/', TrackDeleteView.as_view(), name='track-delete'),

]
