"""
URL configuration for RTR project.

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
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

def home(request):
    return HttpResponse("API is running successfully on Render!")

urlpatterns = [
     path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('usuario.urls')),
    path('api/', include('producto.urls')),
    path('api/', include('ventas.urls')),
    path('api/', include('sucursales.urls')),
    path('api/', include('inventario.urls')),
    path('api/', include('clientes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
