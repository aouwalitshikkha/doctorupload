# from django.contrib import admin
# from django.urls import path, include
# from django.conf import settings
# from django.conf.urls.static import static


# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('doctorProfile.urls')),

# ]


# urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import index, sitemap
from django.views.generic.base import TemplateView
from .sitemaps import (
    StaticSitemap, DoctorSitemap, HospitalSitemap,
    DepartmentSitemap, TopDoctorLocationSitemap, TopHospitalLocationSitemap,
)

sitemaps = {
    'static': StaticSitemap,
    'doctors': DoctorSitemap,
    'hospitals': HospitalSitemap,
    'departments': DepartmentSitemap,
    'top-doctors': TopDoctorLocationSitemap,
    'top-hospitals': TopHospitalLocationSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('doctorProfile.urls')),
    path('sitemap.xml', index, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.index'),
    path('sitemap-<section>.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)