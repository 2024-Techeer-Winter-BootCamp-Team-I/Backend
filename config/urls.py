from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf.urls.static import static
from django.conf import settings

# Schema view 설정
schema_view = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
        description="API description",
        contact=openapi.Contact(email="contact@myapi.com"),
        license=openapi.License(name="BSD License"),
        # Bearer 인증을 위한 security 설정 추가
        security=[{'Bearer': []}],
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=[],  # 인증 클래스 비워두기 (Swagger에만 적용)
)


urlpatterns = [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path("api/v1/", include([
        path("documents/", include('document.urls')),  # 문서 관련 URL
        path("login/", include('login.urls')),  # 로그인 관련 URL
        path('accounts/', include('allauth.urls')),  # allauth URL 추가
        path("repos/", include('repo.urls')),  # 레포지토리 관련 URL
        path('directories/', include('directory.urls')),
        path('tech-stack/', include('Tech_Stack.urls')),  # Tech_Stack 앱 URL 추가
    ])),
    
]


urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)