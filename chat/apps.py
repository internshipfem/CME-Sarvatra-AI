from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db.backends.signals import connection_created


def ensure_default_superuser():
    """
    Automatically creates the default superuser (admin / admin)
    if not already present when migrations complete.
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
        pass


def on_post_migrate(sender, **kwargs):
    ensure_default_superuser()


def on_connection_created(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        try:
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA journal_mode=WAL;')
        except Exception:
            pass


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        post_migrate.connect(on_post_migrate, sender=self)
        connection_created.connect(on_connection_created)
