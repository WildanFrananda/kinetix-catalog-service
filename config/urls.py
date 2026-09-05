from django.contrib import admin
from django.urls import path, include

from core.api.views import HealthView, ReadinessView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
    path('health', HealthView.as_view(), name='health'),
    path('health/ready', ReadinessView.as_view(), name='health-ready'),
]
