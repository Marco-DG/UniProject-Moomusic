from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
from .models import Track, Playlist, Favourite, Recent, Profile, PlaylistTrack, Recommendation
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView


# Utility: sidebar context
def _get_sidebar_data(user):
    recent_songs = []
    favourites = []
    playlists = []

    if user.is_authenticated:
        recent_ids = (
            Recent.objects
                  .filter(user=user)
                  .order_by('-id')
                  .values_list('track_id', flat=True)[:5]
        )
        seen = set()
        for tid in recent_ids:
            if tid not in seen:
                seen.add(tid)
                recent_songs.append(Track.objects.get(pk=tid))

        favourites = Track.objects.filter(favourite__user=user).distinct()
        playlists = user.playlist_set.all()

    return recent_songs, favourites, playlists


# Home
def home(request):
    tracks = Track.objects.all()
    recent_songs, favourites, playlists = _get_sidebar_data(request.user)

    # Build recommendations if user may view them
    recs = []
    if request.user.is_authenticated and request.user.has_perm('pages.view_recommendations'):
        # Simple scoring: count how many times you've fav'd or played same artist
        artist_counts = {}
        for t in favourites:
            artist_counts[t.artist] = artist_counts.get(t.artist, 0) + 5
        for r in recent_songs:
            artist_counts[r.artist] = artist_counts.get(r.artist, 0) + 1

        # score each track not already in your favourites
        rec_objs = []
        for t in tracks.exclude(pk__in=[f.pk for f in favourites]):
            score = artist_counts.get(t.artist, 0)
            rec_obj, _ = Recommendation.objects.update_or_create(
                user=request.user, track=t,
                defaults={'score': score}
            )
            if score > 0:
                rec_objs.append(rec_obj)
        # take top 10
        recs = sorted(rec_objs, key=lambda r: r.score, reverse=True)[:10]
    else:
        recs = None


    return render(request, 'pages/home.html', {
        'tracks': tracks,
        'recent_songs': recent_songs,
        'favourites': favourites,
        'playlists': playlists,
        'recommendations': recs,
    })


def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)

    if playlist.user != request.user:
        return HttpResponseForbidden()

    if request.method == 'POST':
        playlist.public = 'public' in request.POST
        playlist.save()
        messages.success(request, "Playlist settings updated.")
        return redirect('playlist_detail', pk=pk)

    recent_songs, favourites, playlists = _get_sidebar_data(request.user)
    return render(request, 'pages/playlist.html', {
        'playlist': playlist,
        'recent_songs': recent_songs,
        'favourites': favourites,
        'playlists': playlists,
        'public_url': request.build_absolute_uri(
            reverse('playlist_public', args=[playlist.pk])
        )
    })



def public_playlist_view(request, pk):
    playlist = get_object_or_404(Playlist, pk=pk)

    if not playlist.public:
        # Pass a flag indicating the playlist is private
        return render(request, 'pages/public_playlist.html', {
            'playlist': playlist,
            'is_private': True,
        })

    return render(request, 'pages/public_playlist.html', {
        'playlist': playlist,
        'is_private': False,
    })



# Favourites
@login_required
def my_favourites(request):
    fav_tracks = Track.objects.filter(favourite__user=request.user).distinct()
    recent_songs, favourites, playlists = _get_sidebar_data(request.user)
    return render(request, 'pages/favourites.html', {
        'tracks': fav_tracks,
        'recent_songs': recent_songs,
        'favourites': favourites,
        'playlists': playlists,
    })


# Toggle favourite
@login_required
def toggle_favourite(request, pk):
    if request.method != 'POST':
        return redirect('track', pk=pk)

    track = get_object_or_404(Track, pk=pk)
    fav_qs = Favourite.objects.filter(user=request.user, track=track)

    if fav_qs.exists():
        fav_qs.delete()
        messages.success(request, f'“{track.title}” removed from your favourites.')
    else:
        Favourite.objects.create(user=request.user, track=track)
        messages.success(request, f'“{track.title}” added to your favourites.')

    return redirect('track', pk=pk)


# Track detail
def track(request, pk):
    track = get_object_or_404(Track, pk=pk)

    if request.user.is_authenticated:
        Recent.objects.filter(user=request.user, track=track).delete()
        Recent.objects.create(user=request.user, track=track)

    all_tracks = list(Track.objects.order_by('id'))
    ids = [t.id for t in all_tracks]
    idx = ids.index(track.id)
    prev_track = all_tracks[idx - 1] if idx > 0 else None
    next_track = all_tracks[idx + 1] if idx < len(all_tracks) - 1 else None

    is_fav = (
        request.user.is_authenticated and
        Favourite.objects.filter(user=request.user, track=track).exists()
    )

    recent_songs, favourites, playlists = _get_sidebar_data(request.user)

    return render(request, 'pages/track.html', {
        'track': track,
        'previous_track': prev_track,
        'next_track': next_track,
        'is_fav': is_fav,
        'recent_songs': recent_songs,
        'favourites': favourites,
        'playlists': playlists,
    })


# Add to playlist
@login_required
def add_to_playlist(request, pk):
    if request.method != 'POST':
        return redirect('track', pk=pk)

    track = get_object_or_404(Track, pk=pk)
    ids = request.POST.getlist('playlist_ids')
    new_name = request.POST.get('new_playlist_name', '').strip()

    if new_name:
        pl = Playlist.objects.create(name=new_name, user=request.user)
        ids.append(str(pl.pk))

    for pid in ids:
        playlist = get_object_or_404(Playlist, pk=pid, user=request.user)
        last_pt = PlaylistTrack.objects.filter(playlist=playlist).order_by('-order').first()
        next_order = last_pt.order + 1 if last_pt else 1
        PlaylistTrack.objects.get_or_create(
            playlist=playlist,
            track=track,
            defaults={'order': next_order}
        )

    messages.success(request, f'“{track.title}” saved to {len(ids)} playlist(s).')
    return redirect('track', pk=pk)




@login_required
def profile_settings(request):
    recent_songs, favourites, playlists = _get_sidebar_data(request.user)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # Avatar POST handling…
    if request.method == 'POST':
        choice = request.POST.get('avatar_choice')
        if choice in dict(Profile.GENDER_CHOICES):
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.gender = choice
            profile.save()
            messages.success(request, 'Avatar updated!')
            return redirect('profile_settings')

    # Determine role
    is_curator = request.user.groups.filter(name='Curator').exists()

    # If they are a curator, give them all tracks to manage
    curator_tracks = Track.objects.all() if is_curator else None

    return render(request, 'pages/profile_settings.html', {
        'recent_songs':    recent_songs,
        'favourites':      favourites,
        'playlists':       playlists,
        'profile':         profile,
        'is_curator':      is_curator,
        'curator_tracks':  curator_tracks,
    })



# Move track in playlist
@login_required
@require_POST
def move_track(request, pk, track_pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    pt = get_object_or_404(PlaylistTrack, playlist=playlist, track_id=track_pk)

    action = request.POST.get('action')
    if action == 'up':
        neighbour = PlaylistTrack.objects.filter(
            playlist=playlist, order__lt=pt.order
        ).order_by('-order').first()
    elif action == 'down':
        neighbour = PlaylistTrack.objects.filter(
            playlist=playlist, order__gt=pt.order
        ).order_by('order').first()
    else:
        neighbour = None

    if neighbour:
        pt.order, neighbour.order = neighbour.order, pt.order
        pt.save()
        neighbour.save()

    return redirect('playlist_detail', pk=playlist.pk)


# Remove track from playlist
@login_required
@require_POST
def remove_track(request, pk, track_pk):
    playlist = get_object_or_404(Playlist, pk=pk, user=request.user)
    PlaylistTrack.objects.filter(playlist=playlist, track_id=track_pk).delete()

    for idx, pt in enumerate(playlist.playlisttrack_set.all(), start=1):
        if pt.order != idx:
            pt.order = idx
            pt.save()

    return redirect('playlist_detail', pk=playlist.pk)


# --- AJAX Live Search ---
from django.http import JsonResponse
from django.db.models import Q

def search_suggestions(request):
    query = request.GET.get('q', '')
    year_from = request.GET.get('year_from')
    year_to = request.GET.get('year_to')

    filters = Q()
    if query:
        filters &= Q(title__icontains=query) | Q(artist__icontains=query)

    if year_from and year_from.isdigit():
        filters &= Q(year__gte=int(year_from))

    if year_to and year_to.isdigit():
        filters &= Q(year__lte=int(year_to))

    tracks = Track.objects.filter(filters).distinct()[:10]

    results = [{
        'id': t.id,
        'title': t.title,
        'artist': t.artist,
        'cover_image': t.cover_image.url if t.cover_image else None,
    } for t in tracks]

    return JsonResponse({'results': results})

# --- Advanced Search Panel Page ---
import datetime

def advanced_search(request):
    query = request.GET.get('q', '')
    year_from = request.GET.get('year_from')
    year_to = request.GET.get('year_to')
    album = request.GET.get('album', '')
    favourites = request.GET.get('favourites')

    filters = Q()
    if query:
        filters &= Q(title__icontains=query) | Q(artist__icontains=query)
    if year_from and year_from.isdigit():
        filters &= Q(year__gte=int(year_from))
    if year_to and year_to.isdigit():
        filters &= Q(year__lte=int(year_to))
    if album:
        filters &= Q(album__icontains=album)
    if favourites and request.user.is_authenticated:
        filters &= Q(favourite__user=request.user)

    tracks = Track.objects.filter(filters).distinct()

    recent_songs, favs, playlists = _get_sidebar_data(request.user)

    current_year = datetime.datetime.now().year
    year_range_from = list(range(current_year, 1899, -1))  # descending (e.g., 2025 to 1900)
    year_range_to = list(range(1900, current_year + 1))    # ascending (e.g., 1900 to 2025)

    return render(request, 'pages/advanced_search.html', {
        'tracks': tracks,
        'recent_songs': recent_songs,
        'favourites': favs,
        'playlists': playlists,
        'year_range_from': year_range_from,
        'year_range_to': year_range_to,
        'query': query,
        'year_from': year_from,
        'year_to': year_to,
        'album': album,
        'favourites_checked': favourites,
    })





class TrackCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Track
    fields = ['title', 'artist', 'audio_file', 'cover_image', 'album', 'year']
    template_name = 'tracks/track_form.html'
    permission_required = 'pages.add_track'
    raise_exception = True
    success_url = reverse_lazy('home')  # or 'track-list' if you have one

class TrackUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Track
    fields = ['title', 'artist', 'audio_file', 'cover_image', 'album', 'year']
    template_name = 'tracks/track_form.html'
    permission_required = 'pages.change_track'
    raise_exception = True
    success_url = reverse_lazy('home')

class TrackDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Track
    template_name = 'tracks/track_confirm_delete.html'
    permission_required = 'pages.delete_track'
    raise_exception = True
    success_url = reverse_lazy('home')
