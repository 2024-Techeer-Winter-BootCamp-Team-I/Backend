import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# STATIC_ROOT 설정 추가
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-cry9d52cvx9a-iv&p=m-ogcom#5)+tnslpp1&t13owjvqjdr8o'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    'django.contrib.sites',  # 필수
    'allauth',  # allauth 앱
    'allauth.account',  # 계정 관리
    'allauth.socialaccount',  # 소셜 로그인 관리
    'allauth.socialaccount.providers.github',  # GitHub 소셜 로그인 제공자 추가
    'login.apps.LoginConfig',  # 로그인 앱
    'document',  # 문서 앱
    'repo.apps.RepoConfig',  # 레포지토리리 앱
    'django_celery_results',
    'rest_framework_simplejwt',  # JWT 토큰 라이브러리
    'social_django',  # 소셜 인증 라이브러리
    'Tech_Stack', # 기술 스택 관련 앱앱
    'rest_framework_simplejwt.token_blacklist',  # 토큰 블랙리스트 앱 추가
    'dind',
    'corsheaders'

]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
    "http://localhost",
    "http://localhost:5173",
    "http://django:8000"
]

CORS_ALLOW_HEADERS = [
    'authorization',
    'x-password',
    'content-type',
    'x-csrftoken',
    'accept',
    'origin',
    'user-agent',
    'access-control-allow-origin',
]

CORS_ALLOW_METHODS = [ 'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS',]

CORS_ALLOW_ALL_ORIGINS = True

SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware', 
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# .env 파일 로드
load_dotenv()

# DeepSeek API 설정
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')

RUNNING_IN_DOCKER = os.getenv('RUNNING_IN_DOCKER', 'false').lower() == 'true'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DATABASE_NAME'),
        'USER': os.getenv('DATABASE_USER'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD'),
        'HOST': os.getenv('DATABASE_HOST'),
        'PORT': os.getenv('DATABASE_PORT'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'ko-kr'

TIME_ZONE = 'Asia/Seoul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # 기본 백엔드
    'allauth.account.auth_backends.AuthenticationBackend',  # allauth 백엔드
)

SOCIALACCOUNT_PROVIDERS = {
    'github': {
        'APP': {
            'client_id': os.getenv('GITHUB_CLIENT_ID'),
            'secret': os.getenv('GITHUB_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': ['user', 'repo'],  # 필요한 권한 설정
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'login.authentication.CookieJWTAuthentication',  # 커스텀 인증 클래스
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # 필요 시 헤더 인증
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # 인증된 사용자만 허용
    ],
    # 기타 설정들...
}

AUTH_USER_MODEL = 'login.User'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Access Token 유효 기간
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),  # Refresh Token 유효 기간
    'ROTATE_REFRESH_TOKENS': False,  # Refresh Token 갱신 여부
    'BLACKLIST_AFTER_ROTATION': True,  # Refresh Token 갱신 후 이전 토큰 블랙리스트 추가
    'AUTH_HEADER_TYPES': ('Bearer',),  # 인증 헤더 타입
}


SOCIALACCOUNT_STORE_TOKENS = True


OPENAPI_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
        }
    }
}

# settings.py

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT 토큰을 입력하세요. 예: "Bearer {토큰}"',
        }
    },
    'USE_SESSION_AUTH': False,  # 세션 인증 비활성화 (JWT만 사용)
}

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # 클라이언트 도메인
]

SOCIAL_AUTH_GITHUB_KEY = os.getenv('GITHUB_CLIENT_ID')  # GitHub OAuth App의 Client ID
SOCIAL_AUTH_GITHUB_SECRET = os.getenv('GITHUB_CLIENT_SECRET')  # GitHub OAuth App의 Client Secret

#Celery 설정
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_ENABLE_UTC = False


ALLAUTH_MIGRATION_MODULES = {
    'account': 'login.migrations',  # allauth의 마이그레이션을 무시
}

#배포서버 호스트
ALLOWED_HOSTS = ['devsketch.site', 'www.devsketch.site', 'localhost', '127.0.0.1']

#deepseek 키
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL')

# 로컬 환경
BACKEND_DOMAIN = 'localhost:8000'

# 배포 환경에서는 아래
# BACKEND_DOMAIN = 'devsketch.site'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# 프로젝트 파일 저장 경로
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

if os.getenv('ENVIRONMENT') == 'prod':
    # HTTPS 인식 설정
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
else:
    SECURE_PROXY_SSL_HEADER = None
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False