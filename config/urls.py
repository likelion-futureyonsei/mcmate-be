"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# 명세: Base URL 은 /api/v1. 각 앱이 자기 주소를 소유한다.
API_PREFIX = 'api/v1/'

urlpatterns = [
    path('admin/', admin.site.urls),
    path(API_PREFIX, include('apps.accounts.urls')),
    path(API_PREFIX, include('apps.products.urls')),
    path(API_PREFIX, include('apps.memories.urls')),
]

if settings.DEBUG:
    # 개발 중 업로드된 사진을 브라우저로 확인할 수 있게 한다 (배포에서는 웹서버가 담당)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
