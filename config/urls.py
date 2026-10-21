from django.urls import path, include

from core.api.views import HealthView, MetricsView, ReadinessView

urlpatterns = [
    path('api/', include('core.urls')),
    path('health', HealthView.as_view(), name='health'),
    path('health/ready', ReadinessView.as_view(), name='health-ready'),
    path('metrics', MetricsView.as_view(), name='metrics'),
]

handler400 = 'core.api.error_handlers.bad_request'
handler404 = 'core.api.error_handlers.page_not_found'
handler500 = 'core.api.error_handlers.server_error'
