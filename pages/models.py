# pages/models.py

from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

def user_avatar_path(instance, filename):
    """
    Custom upload path for user avatars:
    MEDIA_ROOT/avatars/user_<id>/<filename>
    """
    return f"avatars/user_{instance.user.id}/{filename}"


class Track(models.Model):
    title       = models.CharField(max_length=200)
    artist      = models.CharField(max_length=200)
    audio_file  = models.FileField(upload_to='tracks/')
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    album       = models.CharField(max_length=200, null=True, blank=True)
    year        = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"

    class Meta:
        # Django automatically creates:
        #   add_track, change_track, delete_track, view_track
        # which we’ll use to give Curators full CRUD on Track
        # No extra custom perms needed here.
        ordering = ['artist', 'title']


class Playlist(models.Model):
    name   = models.CharField(max_length=200)
    user   = models.ForeignKey(User, on_delete=models.CASCADE)
    tracks = models.ManyToManyField(
        Track,
        through='PlaylistTrack',
        related_name='in_playlists'
    )
    public = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} (by {self.user.username})"

    class Meta:
        ordering = ['name']
        permissions = [
            # Listeners (and Curators) get these:
            ("manage_own_playlists", "Can create/edit/delete own playlists"),
            ("view_recommendations",  "Can view recommendations"),
        ]


class PlaylistTrack(models.Model):
    """
    Through‑model for Playlist ↔ Track, with explicit ordering.
    """
    playlist = models.ForeignKey(
        Playlist,
        on_delete=models.CASCADE,
        related_name='playlisttrack_set'
    )
    track    = models.ForeignKey(Track, on_delete=models.CASCADE)
    order    = models.PositiveIntegerField(db_index=True)

    class Meta:
        ordering = ['order']
        unique_together = [('playlist', 'track')]

    def __str__(self):
        return f"{self.playlist.name} [{self.order}] – {self.track.title}"


class Favourite(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'track')

    def __str__(self):
        return f"{self.user.username} – {self.track.title}"


class Recent(models.Model):
    user  = models.ForeignKey(User, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} recently played {self.track.title}"


class Profile(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    user   = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=user_avatar_path, null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')

    def get_avatar_url(self):
        """
        Return the URL of the uploaded avatar if present,
        otherwise fall back to a gendered static default.
        """
        if self.avatar:
            return self.avatar.url
        from django.templatetags.static import static
        default = (
            'rsc/moomusic_female_avatar_logo.png'
            if self.gender == 'F'
            else 'rsc/moomusic_male_avatar_logo.png'
        )
        return static(default)

    def __str__(self):
        return f"{self.user.username} Profile"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure a Profile exists for every User.
    """
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)




class Recommendation(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    track        = models.ForeignKey(Track, on_delete=models.CASCADE)
    score        = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-score']
        permissions = [
            # reuse the existing view_recommendations perm
        ]

    def __str__(self):
        return f"{self.user.username} → {self.track.title} ({self.score:.2f})"
