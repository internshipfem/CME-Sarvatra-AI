from django.apps import AppConfig
from django.db.models.signals import post_migrate


def ensure_default_superuser():
    """
    Automatically creates the default superuser (admin / admin)
    if not already present when the app is launched.
    """
    try:
        from django.db import connection
        table_names = connection.introspection.table_names()
        if 'auth_user' in table_names:
            from django.contrib.auth.models import User
            from chat.models import UserProfile

            if not User.objects.filter(username='admin').exists():
                admin = User.objects.create_superuser('admin', 'admin@localhost', 'admin')
                admin.first_name = 'Admin'
                admin.last_name = 'User'
                admin.save()
                profile, _ = UserProfile.objects.get_or_create(user=admin)
                profile.employee_id = 'EMP-001'
                profile.department = 'IT/Admin'
                profile.save()
                print("[Init] Default superuser 'admin' created with password 'admin' (EMP-001).")
    except Exception:
        # Ignore if migrations haven't run yet
        pass


def on_post_migrate(sender, **kwargs):
    ensure_default_superuser()


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        post_migrate.connect(on_post_migrate, sender=self)
        ensure_default_superuser()
