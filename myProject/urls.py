from django.contrib import admin
from django.urls import path , include , re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny


schema_view = get_schema_view(
   openapi.Info(
      title="Amazone Syria API",
      default_version='v1',
      description="API documentation for your Amazone Syria",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="emadmador@gmail.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[AllowAny],
)


urlpatterns = [
   path('admin/', admin.site.urls),
   path('api/auth/' , include('apps.accounts.urls')),
   path('api/drivers/' , include('apps.drivers.urls')),
   path('api/offices/' , include('apps.office.urls')),
   path('api/passengers/' , include('apps.passengers.urls')),
   path('api/passenger/' , include('apps.trips.passenger_urls')),  # Passenger trip endpoints: /api/passenger/trips/
   path('api/driver/' , include('apps.trips.driver_urls')),  # Driver trip endpoints: /api/driver/trips/
   path('api/payments/' , include('apps.payments.urls')),
   path('api/trips/' , include('apps.trips.urls')),
   path('api/vehicle/' , include('apps.vehicle.urls')),
   path('api/complaints/', include('apps.complaints.urls')),
   path('api/admin-panel/' , include('apps.admin_panel.urls')),
   path('api/', include('apps.admin_panel.urls_public')),  # Public instruction files: /api/instruction-files/
   path('api/pricing/', include('apps.pricing.urls')),
   path('api/earnings/', include('apps.earnings.urls')),

   path('silk/', include('silk.urls', namespace='silk')),
   re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
   re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
