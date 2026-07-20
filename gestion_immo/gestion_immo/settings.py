"""
Django settings for gestion_immo project.

Configuration compatible avec :
- le développement local;
- Render;
- SQLite en local;
- PostgreSQL sur Render avec DATABASE_URL;
- WhiteNoise pour les fichiers statiques.
"""

import os
from pathlib import Path

import dj_database_url


# =========================================================
# CHEMINS DU PROJET
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SÉCURITÉ
# =========================================================

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-cle-locale-temporaire-a-remplacer"
)


DEBUG = os.environ.get(
    "DEBUG",
    "True"
).lower() == "true"


# =========================================================
# DOMAINES AUTORISÉS
# =========================================================

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    ".onrender.com",
]


RENDER_EXTERNAL_HOSTNAME = os.environ.get(
    "RENDER_EXTERNAL_HOSTNAME"
)


if RENDER_EXTERNAL_HOSTNAME:

    ALLOWED_HOSTS.append(
        RENDER_EXTERNAL_HOSTNAME
    )


CSRF_TRUSTED_ORIGINS = [
    "https://*.onrender.com",
]


if RENDER_EXTERNAL_HOSTNAME:

    CSRF_TRUSTED_ORIGINS.append(
        f"https://{RENDER_EXTERNAL_HOSTNAME}"
    )


# Render utilise un proxy HTTPS.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# Cookies sécurisés uniquement en production.
if not DEBUG:

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True


# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "immo",
]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise doit être placé immédiatement
    # après SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =========================================================
# URLS ET WSGI
# =========================================================

ROOT_URLCONF = "gestion_immo.urls"


WSGI_APPLICATION = "gestion_immo.wsgi.application"


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django."
            "DjangoTemplates"
        ),

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "debug"
                ),

                (
                    "django.template.context_processors."
                    "request"
                ),

                (
                    "django.contrib.auth.context_processors."
                    "auth"
                ),

                (
                    "django.contrib.messages.context_processors."
                    "messages"
                ),
            ],
        },
    },
]


# =========================================================
# BASE DE DONNÉES
# =========================================================
#
# En local :
# Django utilise automatiquement db.sqlite3.
#
# Sur Render :
# si la variable DATABASE_URL existe, Django utilise
# automatiquement PostgreSQL.
# =========================================================

DATABASES = {
    "default": dj_database_url.config(

        default=(
            f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
        ),

        conn_max_age=600,

        conn_health_checks=True,
    )
}


# =========================================================
# VALIDATION DES MOTS DE PASSE
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },

    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# =========================================================
# LANGUE ET FUSEAU HORAIRE
# =========================================================

LANGUAGE_CODE = "fr-ca"


TIME_ZONE = "America/Montreal"


USE_I18N = True


USE_TZ = True


# =========================================================
# FICHIERS STATIQUES
# =========================================================

STATIC_URL = "/static/"


STATIC_ROOT = BASE_DIR / "staticfiles"


STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedStaticFilesStorage"
        ),
    },
}


# =========================================================
# FICHIERS MÉDIA
# =========================================================

MEDIA_URL = "/media/"


MEDIA_ROOT = BASE_DIR / "media"


# =========================================================
# CLÉ PRIMAIRE PAR DÉFAUT
# =========================================================

DEFAULT_AUTO_FIELD = (
    "django.db.models.BigAutoField"
)


# =========================================================
# AUTHENTIFICATION
# =========================================================

LOGIN_URL = "/login/"


LOGIN_REDIRECT_URL = "/"


LOGOUT_REDIRECT_URL = "/login/"