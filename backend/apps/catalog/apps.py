from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.apps.catalog"
    verbose_name = "商品目录"

    def ready(self):
        from django.contrib.auth.signals import user_logged_in

        def on_user_logged_in(sender, request, user, **kwargs):
            if getattr(user, "is_staff", False) and getattr(user, "pk", None):
                from backend.apps.catalog.login_tracking import record_staff_login

                record_staff_login(request, user.pk)

        user_logged_in.connect(on_user_logged_in, dispatch_uid="catalog_touch_staff_last_login")