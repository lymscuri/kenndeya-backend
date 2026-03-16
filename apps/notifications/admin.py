# apps/notifications/admin.py

from django.contrib import admin
from .models import PushToken


@admin.register(PushToken)
class PushTokenAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les tokens push.
    """
    list_display = ['user', 'role', 'token_preview', 'created_at', 'updated_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'token']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-created_at']

    fieldsets = (
        ('Utilisateur', {
            'fields': ('user', 'role')
        }),
        ('Token', {
            'fields': ('token',)
        }),
        ('Métadonnées', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def token_preview(self, obj):
        """
        Affiche un aperçu tronqué du token.
        """
        if len(obj.token) > 30:
            return f"{obj.token[:30]}..."
        return obj.token
    token_preview.short_description = 'Token (aperçu)'
