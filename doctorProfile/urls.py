from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    SpecialtyViewSet, HospitalViewSet, DoctorViewSet,
    ExperienceViewSet, ReviewViewSet,
    LocationViewSet, DepartmentViewSet
)


router = DefaultRouter()
router.register(r'specialties', SpecialtyViewSet, basename='api-specialty')
router.register(r'hospitals', HospitalViewSet, basename='api-hospital')
router.register(r'doctors', DoctorViewSet, basename='api-doctor')
router.register(r'experiences', ExperienceViewSet, basename='api-experience')
router.register(r'reviews', ReviewViewSet, basename='api-review')
router.register(r'locations', LocationViewSet, basename='api-location')
router.register(r'departments', DepartmentViewSet, basename='api-department')

urlpatterns = [
    path('', views.home_view, name='home'),
    path('doctors/', views.doctor_list_view, name='doctor_list'),
    path('hospitals/', views.hospital_list_view, name='hospital_list'),
    path('about/', views.AboutUsView.as_view(), name='about_us'),
    path('contact/', views.ContactView.as_view(), name='contact_us'),
    path('verification-policy/', views.VerificationPolicyView.as_view(), name='verification_policy'),
    path('editorial-policy/', views.EditorialPolicyView.as_view(), name='editorial_policy'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path("hospital/<slug:slug>/", views.HospitalDoctorListView.as_view(), name="hospital_detail"),
    path('top-<slug:department>-doctors-in-<slug:location>/', views.top_doctors_view, name='top_doctors_department_location'),
    path('top-hospitals-in-<slug:location>/', views.top_hospitals_view, name='top_hospitals_location'),
    path('departments/', views.department_list_view, name='department_list'),
    path('department/<slug:slug>/', views.department_detail_view, name='department_detail'),

    # API
    path('api/', include(router.urls)),
    path('api/auth/', obtain_auth_token, name='api_token_auth'),
    path('<slug:slug>/', views.doctor_profile_view, name='doctor_profile'),
]
