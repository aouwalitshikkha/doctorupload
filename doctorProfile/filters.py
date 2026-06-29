import django_filters
from .models import Doctor, Hospital, Department, Specialty, Location, Experience, Review


class DoctorFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    designation = django_filters.CharFilter(lookup_expr='icontains')
    qualifications = django_filters.CharFilter(lookup_expr='icontains')
    min_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    max_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='lte')
    min_rating = django_filters.NumberFilter(field_name='reviews__rating', lookup_expr='gte')
    location = django_filters.CharFilter(field_name='location__slug', lookup_expr='iexact')
    location_name = django_filters.CharFilter(field_name='location__name', lookup_expr='icontains')
    specialty = django_filters.CharFilter(field_name='specialties__slug', lookup_expr='iexact')
    department = django_filters.CharFilter(field_name='specialties__department__slug', lookup_expr='iexact')
    hospital = django_filters.CharFilter(field_name='hospital__slug', lookup_expr='iexact')
    hospital_name = django_filters.CharFilter(field_name='hospital__name', lookup_expr='icontains')

    class Meta:
        model = Doctor
        fields = {
            'id': ['exact'],
            'experience_years': ['exact', 'gte', 'lte'],
        }


class HospitalFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    location = django_filters.CharFilter(field_name='location__slug', lookup_expr='iexact')
    location_name = django_filters.CharFilter(field_name='location__name', lookup_expr='icontains')
    min_rating = django_filters.NumberFilter(field_name='doctors__reviews__rating', lookup_expr='gte')
    index_status = django_filters.BooleanFilter()

    class Meta:
        model = Hospital
        fields = {
            'id': ['exact'],
            'index_status': ['exact'],
        }


class DepartmentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Department
        fields = {
            'id': ['exact'],
            'name': ['exact', 'icontains'],
        }


class SpecialtyFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    department = django_filters.CharFilter(field_name='department__slug', lookup_expr='iexact')

    class Meta:
        model = Specialty
        fields = {
            'id': ['exact'],
            'name': ['exact', 'icontains'],
        }


class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Location
        fields = {
            'id': ['exact'],
            'name': ['exact', 'icontains'],
        }


class ExperienceFilter(django_filters.FilterSet):
    doctor = django_filters.CharFilter(field_name='doctor__slug', lookup_expr='iexact')
    min_start_year = django_filters.NumberFilter(field_name='start_year', lookup_expr='gte')
    max_end_year = django_filters.NumberFilter(field_name='end_year', lookup_expr='lte')

    class Meta:
        model = Experience
        fields = {
            'id': ['exact'],
            'doctor': ['exact'],
            'start_year': ['exact', 'gte', 'lte'],
            'end_year': ['exact', 'gte', 'lte'],
        }


class ReviewFilter(django_filters.FilterSet):
    doctor = django_filters.CharFilter(field_name='doctor__slug', lookup_expr='iexact')
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')

    class Meta:
        model = Review
        fields = {
            'id': ['exact'],
            'doctor': ['exact'],
            'rating': ['exact', 'gte', 'lte'],
        }
