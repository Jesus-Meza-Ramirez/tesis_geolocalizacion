
import os
from pathlib import Path

# ==============================
# BASE
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================
# SECURITY
# ==============================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret-key")

# En producción debe ser False
DEBUG = True

# Modo seguro (para cuando tengas HTTPS). Por ahora déjalo en 0 en el servidor.
# Ejemplo: export DJANGO_SECURE=1  (cuando ya tengas SSL)
SECURE = os.environ.get("DJANGO_SECURE", "0") == "1"

# Hosts permitidos: usa IP pública del Droplet y/o dominio cuando lo tengas
# Puedes pasar hosts por env: DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,159.89.123.45"
allowed_hosts_env = os.environ.get("DJANGO_ALLOWED_HOSTS", "").strip()
if allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_env.split(",") if h.strip()]
else:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "IP_DEL_SERVIDOR",  # <- reemplaza por tu IP pública o usa DJANGO_ALLOWED_HOSTS
        # "tu_dominio.com",
        # "www.tu_dominio.com",
    ]

# Si estás detrás de Nginx (lo normal en DigitalOcean) esto ayuda cuando tengas HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ==============================
# APPS
# ==============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'reportes.apps.ReportesConfig',
    'sistema',
    'incidencias',
    'usuarios',
    'webui',
]

# ==============================
# MIDDLEWARE
# ==============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Si luego quieres usar WhiteNoise para estáticos sin depender tanto de Nginx, descomenta:
    # 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ==============================
# URLS / WSGI
# ==============================
ROOT_URLCONF = 'control_incidencias.urls'
WSGI_APPLICATION = 'control_incidencias.wsgi.application'

# ==============================
# TEMPLATES
# ==============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'webui', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ==============================
# DATABASE (MySQL / MariaDB)
# ==============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get("DB_NAME", "tesis_geolocalizacion"),
        'USER': os.environ.get("DB_USER", "root"),
        'PASSWORD': os.environ.get("DB_PASSWORD", ""),
        'HOST': os.environ.get("DB_HOST", "localhost"),
        'PORT': os.environ.get("DB_PORT", "3306"),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ==============================
# PASSWORDS
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==============================
# I18N / TIME
# ==============================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = False

# ==============================
# STATIC FILES
# ==============================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'webui', 'static'),
]

# Si activas WhiteNoise, esto ayuda en prod (déjalo comentado si no lo usas):
# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ==============================
# MEDIA FILES
# ==============================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ==============================
# DEFAULT PK
# ==============================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================
# SESSIONS
# ==============================
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ==============================
# SECURITY HARDENING (PROD)
# ==============================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 🔥 IMPORTANTE:
# SIN DOMINIO NI HTTPS todavía, debe quedar en False para que funcionen login/forms.
# Cuando tengas SSL, pon DJANGO_SECURE=1 y se activan automáticamente.
CSRF_COOKIE_SECURE = SECURE
SESSION_COOKIE_SECURE = SECURE

# ⚠️ Activar solo cuando tengas HTTPS (con DJANGO_SECURE=1)
SECURE_SSL_REDIRECT = SECURE

# Para HTTPS con dominio (cuando ya lo tengas), agrega por env:
# DJANGO_CSRF_TRUSTED_ORIGINS="https://tudominio.com,https://www.tudominio.com"
csrf_trusted = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").strip()
if csrf_trusted:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_trusted.split(",") if o.strip()]
    
    

# Límite máximo de subida: 50 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB
