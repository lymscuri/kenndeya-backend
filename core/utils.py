"""
Fonctions utilitaires partagées pour Kendeya Backend.
"""

import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import uuid
from datetime import datetime, timedelta


def generate_qr_code(data):
    """
    Génère un QR code à partir de données textuelles.

    Args:
        data (str): Les données à encoder dans le QR code

    Returns:
        ContentFile: Fichier image du QR code prêt à être sauvegardé
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convertir l'image en fichier
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return ContentFile(buffer.read(), name=f'qr_{uuid.uuid4().hex[:8]}.png')


def generate_unique_code(prefix='KEN', length=8):
    """
    Génère un code unique avec un préfixe.

    Args:
        prefix (str): Préfixe du code (par défaut: 'KEN')
        length (int): Longueur de la partie aléatoire (par défaut: 8)

    Returns:
        str: Code unique (ex: KEN-A1B2C3D4)
    """
    random_part = uuid.uuid4().hex[:length].upper()
    return f"{prefix}-{random_part}"


def calculate_age(birth_date):
    """
    Calcule l'âge en années à partir d'une date de naissance.

    Args:
        birth_date (date): Date de naissance

    Returns:
        int: Âge en années
    """
    today = datetime.now().date()
    age = today.year - birth_date.year

    # Ajuster si l'anniversaire n'est pas encore passé cette année
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1

    return age


def calculate_pregnancy_week(last_period_date):
    """
    Calcule la semaine de grossesse actuelle à partir de la date des dernières règles.

    Args:
        last_period_date (date): Date des dernières règles

    Returns:
        int: Semaine de grossesse (0-42)
    """
    today = datetime.now().date()
    days_pregnant = (today - last_period_date).days
    weeks_pregnant = days_pregnant // 7

    return max(0, min(weeks_pregnant, 42))


def calculate_due_date(last_period_date):
    """
    Calcule la date prévue d'accouchement (280 jours après les dernières règles).

    Args:
        last_period_date (date): Date des dernières règles

    Returns:
        date: Date prévue d'accouchement
    """
    return last_period_date + timedelta(days=280)


def format_phone_number(phone):
    """
    Formate un numéro de téléphone guinéen au format international.

    Args:
        phone (str): Numéro de téléphone

    Returns:
        str: Numéro formaté au format +224XXXXXXXXX
    """
    # Retirer tous les caractères non numériques
    phone = ''.join(filter(str.isdigit, phone))

    # Si le numéro commence par 224, ajouter le +
    if phone.startswith('224'):
        return f'+{phone}'

    # Si le numéro commence par 6 ou 7 (format local), ajouter +224
    if phone.startswith(('6', '7')) and len(phone) == 9:
        return f'+224{phone}'

    # Sinon, retourner tel quel
    return phone
