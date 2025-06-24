# authentication/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate

class AuthenticationConfig(AppConfig):
    name = 'authentication'

    def ready(self):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType
        from pages.models import Playlist, Track

        def create_groups(sender, **kwargs):
            # ── Playlist perms ──
            p_ct = ContentType.objects.get_for_model(Playlist)
            manage_own = Permission.objects.get(
                content_type=p_ct, codename='manage_own_playlists')
            view_recs   = Permission.objects.get(
                content_type=p_ct, codename='view_recommendations')

            # ── Track perms (built‑in) ──
            t_ct         = ContentType.objects.get_for_model(Track)
            add_track    = Permission.objects.get(
                content_type=t_ct, codename='add_track')
            change_track = Permission.objects.get(
                content_type=t_ct, codename='change_track')
            delete_track = Permission.objects.get(
                content_type=t_ct, codename='delete_track')

            # ── Listener group ──
            listener, _ = Group.objects.get_or_create(name='Listener')
            listener.permissions.set([manage_own, view_recs])

            # ── Curator group ──
            curator, _ = Group.objects.get_or_create(name='Curator')
            curator.permissions.set(
                [manage_own, view_recs, add_track, change_track, delete_track]
            )

        post_migrate.connect(create_groups, sender=self)
