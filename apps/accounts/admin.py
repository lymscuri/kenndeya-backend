"""
Configuration de l'admin Django pour l'application accounts.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms

from .models import User


class UserCreationForm(forms.ModelForm):
    """Formulaire pour créer un nouvel utilisateur dans l'admin."""

    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label='Confirmation du mot de passe',
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')

    def clean_password2(self):
        """Vérifie que les deux mots de passe correspondent."""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Les mots de passe ne correspondent pas")
        return password2

    def save(self, commit=True):
        """Sauvegarde l'utilisateur avec le mot de passe hashé."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Formulaire pour modifier un utilisateur dans l'admin."""

    password = ReadOnlyPasswordHashField(
        label='Mot de passe',
        help_text=(
            "Les mots de passe ne sont pas stockés en clair. "
            '<a href="../password/">Modifier le mot de passe</a>.'
        )
    )

    class Meta:
        model = User
        fields = (
            'email', 'password', 'first_name', 'last_name', 'phone',
            'role', 'is_active', 'is_staff', 'is_superuser'
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Configuration de l'admin pour le modèle User."""

    form = UserChangeForm
    add_form = UserCreationForm

    # Liste des utilisateurs
    list_display = (
        'email', 'get_full_name', 'role', 'is_active',
        'is_staff', 'created_at'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)

    # Détails d'un utilisateur
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'phone', 'role')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )

    # Formulaire d'ajout d'utilisateur
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'phone', 'role',
                'password1', 'password2', 'is_active', 'is_staff', 'is_superuser'
            )
        }),
    )

    # Champs en lecture seule
    readonly_fields = ('created_at', 'updated_at', 'last_login')

    # Nombre d'éléments par page
    list_per_page = 25

    def get_full_name(self, obj):
        """Affiche le nom complet dans la liste."""
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'
