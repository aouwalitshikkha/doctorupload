from django.shortcuts import render, get_object_or_404, redirect
from .models import Specialty, Hospital, Doctor, Experience, Review, Location, Department
from django.core.paginator import Paginator
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Avg, Count, F, Prefetch
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import (
    SpecialtySerializer, SpecialtyDetailSerializer,
    HospitalSerializer, HospitalDetailSerializer,
    DoctorSerializer, DoctorListSerializer,
    ExperienceSerializer, ReviewSerializer, ReviewCreateSerializer,
    LocationSerializer, LocationDetailSerializer,
    DepartmentSerializer, DepartmentDetailSerializer,
)
from .filters import (
    DoctorFilter, HospitalFilter, DepartmentFilter,
    SpecialtyFilter, LocationFilter, ExperienceFilter, ReviewFilter,
)
from django.views.generic import TemplateView, DetailView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.cache import cache
import re


CACHE_TTL = 60 * 60 * 6  # 6 hours


def home_view(request):
    doctor_name_query = request.GET.get('name', '')
    hospital_name_query = request.GET.get('hospital_name', '')
    location_query = request.GET.get('location', '')

    is_search = bool(doctor_name_query or hospital_name_query or location_query)
    doctor_search_results = Doctor.objects.none()
    hospital_search_results = Hospital.objects.none()

    if is_search:
        doctors_qs = Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties')
        hospitals_qs = Hospital.objects.select_related('location')

        if doctor_name_query:
            doctors_qs = doctors_qs.filter(name__icontains=doctor_name_query)
        if hospital_name_query:
            hospitals_qs = hospitals_qs.filter(name__icontains=hospital_name_query)
            if hospitals_qs.count() == 1:
                return redirect('hospital_detail', slug=hospitals_qs.first().slug)
        if location_query:
            if 'name' in request.GET:
                doctors_qs = doctors_qs.filter(location__slug=location_query)
            if 'hospital_name' in request.GET:
                hospitals_qs = hospitals_qs.filter(location__slug=location_query)

        doctor_search_results = doctors_qs.annotate(
            avg_rating=Avg('reviews__rating'), review_count=Count('reviews')
        ).order_by('-id')
        hospital_search_results = hospitals_qs.order_by('-updated_at')

    cache_key = 'home_page_data_v3'
    cached = cache.get(cache_key)
    if cached and not is_search:
        featured_doctors, featured_hospitals, featured_specialties, featured_departments, featured_departments_all, doctors_count, hospitals_count, locations_count, locs = cached
    else:
        locs = list(Location.objects.all().order_by('name'))

        count_cache = cache.get('home_counts')
        if count_cache:
            doctors_count, hospitals_count = count_cache
        else:
            doctors_count = Doctor.objects.count()
            hospitals_count = Hospital.objects.count()
            cache.set('home_counts', (doctors_count, hospitals_count), CACHE_TTL * 4)

        if is_search:
            featured_doctors = []
            featured_hospitals = []
            featured_specialties = []
            featured_departments = []
            featured_departments_all = []
            locations_count = len(locs)
        else:
            featured_doctors = list(Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties').annotate(
                avg_rating=Avg('reviews__rating'), review_count=Count('reviews')
            ).order_by('-id')[:6])

            featured_hospitals = list(Hospital.objects.select_related('location').annotate(
                avg_rating=Avg('doctors__reviews__rating'), review_count=Count('doctors__reviews', distinct=True)
            ).filter(index_status=True).order_by('-updated_at')[:6])

            featured_specialties = list(Specialty.objects.annotate(
                doctor_count=Count('doctor')
            ).order_by('-doctor_count')[:8])

            featured_departments_all = list(
                Department.objects.annotate(
                    doctor_count=Count('specialties__doctor', distinct=True)
                ).filter(doctor_count__gt=0).order_by('-doctor_count')[:12]
            )
            featured_departments = featured_departments_all[:5]
            locations_count = len(locs)

            cache.set(cache_key, (featured_doctors, featured_hospitals, featured_specialties, featured_departments, featured_departments_all,
                      doctors_count, hospitals_count, locations_count, locs), CACHE_TTL)

    context = {
        'specialties': featured_specialties,
        'locations': locs,
        'locations_for_search': locs,
        'doctors': featured_doctors,
        'hospitals': featured_hospitals,
        'doctor_search_results': doctor_search_results,
        'hospital_search_results': hospital_search_results,
        'featured_specialties': featured_specialties,
        'featured_departments': featured_departments,
        'featured_departments_all': featured_departments_all,
        'doctors_count': doctors_count,
        'hospitals_count': hospitals_count,
        'locations_count': locations_count,
        'doctor_name_value': doctor_name_query,
        'hospital_name_value': hospital_name_query,
        'location_value': location_query,
        'is_search': is_search,
    }
    return render(request, 'profiles/home.html', context)




def doctor_profile_view(request, slug):
    cache_key = f'doctor_profile_{slug}'
    cached = cache.get(cache_key)
    if cached:
        return render(request, 'profiles/doctor_profile.html', cached)

    doctor = get_object_or_404(
        Doctor.objects.select_related('hospital', 'location').annotate(
            review_count=Count('reviews')
        ).prefetch_related(
            Prefetch('specialties', queryset=Specialty.objects.prefetch_related('department'))
        ),
        slug=slug
    )

    related_doctors = []
    location_id = doctor.location_id
    specialty_ids = [s.id for s in doctor.specialties.all()]
    department_ids = list(set(
        d.id for s in doctor.specialties.all() for d in s.department.all()
    ))

    related_qs = Doctor.objects.select_related('hospital', 'location').prefetch_related(
        Prefetch('specialties', queryset=Specialty.objects.prefetch_related('department'))
    ).exclude(id=doctor.id).distinct()

    if location_id and specialty_ids:
        same_location_same_spec = related_qs.filter(
            location_id=location_id, specialties__in=specialty_ids
        )[:6]
    else:
        same_location_same_spec = Doctor.objects.none()

    if location_id and department_ids:
        same_location_same_dept = related_qs.filter(
            location_id=location_id, specialties__department__in=department_ids
        ).exclude(id__in=[d.id for d in same_location_same_spec if d.id])[:4]
    else:
        same_location_same_dept = Doctor.objects.none()

    other_location_same_spec = related_qs.filter(
        specialties__in=specialty_ids
    ).exclude(
        id__in=[d.id for d in same_location_same_spec if d.id]
    ).exclude(
        id__in=[d.id for d in same_location_same_dept if d.id]
    )[:4] if specialty_ids else Doctor.objects.none()

    seen = set()
    for doc in same_location_same_spec:
        if doc.id not in seen:
            related_doctors.append(doc)
            seen.add(doc.id)
    for doc in same_location_same_dept:
        if doc.id not in seen:
            related_doctors.append(doc)
            seen.add(doc.id)
    for doc in other_location_same_spec:
        if doc.id not in seen:
            related_doctors.append(doc)
            seen.add(doc.id)

    related_doctors = related_doctors[:4]

    context = {
        'doctor': doctor,
        'review_count': doctor.review_count,
        'related_doctors': related_doctors,
    }
    cache.set(cache_key, context, CACHE_TTL)
    return render(request, 'profiles/doctor_profile.html', context)




class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    filterset_class = SpecialtyFilter
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return SpecialtySerializer
        return SpecialtyDetailSerializer

    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        specialty = self.get_object()
        doctors = Doctor.objects.filter(specialties=specialty).select_related(
            'hospital', 'location'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        page = self.paginate_queryset(doctors)
        if page is not None:
            serializer = DoctorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)


class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.select_related('location')
    filterset_class = HospitalFilter
    search_fields = ['name', 'location__name']
    ordering_fields = ['name', 'updated_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return HospitalSerializer
        return HospitalDetailSerializer

    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        hospital = self.get_object()
        doctors = Doctor.objects.filter(hospital=hospital).select_related(
            'hospital', 'location'
        ).prefetch_related('specialties').annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        page = self.paginate_queryset(doctors)
        if page is not None:
            serializer = DoctorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        hospitals = self.get_queryset().annotate(
            avg_rating=Avg('doctors__reviews__rating'),
            doctor_count=Count('doctors', distinct=True),
            review_count=Count('doctors__reviews', distinct=True)
        ).filter(index_status=True).order_by('-avg_rating')[:10]
        serializer = HospitalDetailSerializer(hospitals, many=True)
        return Response(serializer.data)


class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties')
    filterset_class = DoctorFilter
    search_fields = ['name', 'designation', 'qualifications', 'hospital__name', 'specialties__name']
    ordering_fields = ['name', 'experience_years']
    ordering = ['-id']

    def get_serializer_class(self):
        if self.action == 'list':
            return DoctorListSerializer
        return DoctorSerializer

    def get_queryset(self):
        qs = Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties').annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        if self.action == 'list':
            return qs
        return qs.prefetch_related('experiences', 'reviews')

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        doctors = self.get_queryset().order_by('-avg_rating', '-review_count')[:10]
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        doctor = self.get_object()
        specialty_ids = list(doctor.specialties.values_list('id', flat=True))
        related = Doctor.objects.filter(
            Q(specialties__in=specialty_ids) |
            Q(hospital=doctor.hospital)
        ).exclude(id=doctor.id).select_related(
            'hospital', 'location'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).distinct()[:6]
        serializer = DoctorListSerializer(related, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def experiences(self, request, pk=None):
        doctor = self.get_object()
        exps = doctor.experiences.all().order_by('-start_year')
        serializer = ExperienceSerializer(exps, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        doctor = self.get_object()
        reviews = doctor.reviews.all().order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class ExperienceViewSet(viewsets.ModelViewSet):
    queryset = Experience.objects.select_related('doctor')
    filterset_class = ExperienceFilter
    search_fields = ['position', 'hospital_name', 'doctor__name']
    ordering_fields = ['start_year', 'end_year']
    ordering = ['-start_year']


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related('doctor')
    filterset_class = ReviewFilter
    search_fields = ['patient_name', 'comment', 'doctor__name']
    ordering_fields = ['rating', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    filterset_class = LocationFilter
    search_fields = ['name', 'slug']
    ordering_fields = ['name', 'slug']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return LocationSerializer
        return LocationDetailSerializer

    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        location = self.get_object()
        doctors = Doctor.objects.filter(location=location).select_related(
            'hospital', 'location'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        page = self.paginate_queryset(doctors)
        if page is not None:
            serializer = DoctorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def hospitals(self, request, pk=None):
        location = self.get_object()
        hospitals = Hospital.objects.filter(location=location).select_related('location')
        page = self.paginate_queryset(hospitals)
        if page is not None:
            serializer = HospitalSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = HospitalSerializer(hospitals, many=True)
        return Response(serializer.data)


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.annotate(
        doctor_count=Count('specialties__doctor', distinct=True)
    )
    filterset_class = DepartmentFilter
    search_fields = ['name', 'slug', 'symptoms']
    ordering_fields = ['name', 'doctor_count']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return DepartmentSerializer
        return DepartmentDetailSerializer

    @action(detail=True, methods=['get'])
    def specialties(self, request, pk=None):
        department = self.get_object()
        specs = department.specialties.all().annotate(
            doctor_count=Count('doctor')
        )
        serializer = SpecialtyDetailSerializer(specs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def doctors(self, request, pk=None):
        department = self.get_object()
        doctors = Doctor.objects.filter(
            specialties__department=department
        ).select_related('hospital', 'location').annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).distinct()
        page = self.paginate_queryset(doctors)
        if page is not None:
            serializer = DoctorListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DoctorListSerializer(doctors, many=True)
        return Response(serializer.data)
    

# Template views

@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache for 12 hours
class AboutUsView(TemplateView):
    template_name = 'profiles/about.html'



@method_decorator(cache_page(60 * 60 * 12), name='dispatch') 
class ContactView(TemplateView):
    template_name = 'profiles/contact.html'
    

@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache for 12 hours
class VerificationPolicyView(TemplateView):
    template_name = 'profiles/verification-policy.html'


@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache for 12 hours
class EditorialPolicyView(TemplateView):
    template_name = 'profiles/editorial-policy.html'
    
    
@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache for 12 hours
class PrivacyPolicyView(TemplateView):
    template_name = 'profiles/privacy.html'


@method_decorator(cache_page(60 * 60 * 12), name='dispatch')  # cache for 12 hours
class TermsOfServiceView(TemplateView):
    template_name = 'profiles/terms-of-service.html'
    
    

class HospitalDoctorListView(DetailView):
    model = Hospital
    template_name = "profiles/hospital_doctors.html"
    context_object_name = "hospital"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Hospital.objects.prefetch_related(
            Prefetch(
                "doctors",
                queryset=Doctor.objects.select_related("hospital")
                .prefetch_related("specialties", "reviews")
            )
        )

    def get_filtered_queryset(self):
        hospital = self.object
        specialty_slug = self.request.GET.get("specialty")
        sort = self.request.GET.get("sort")

        doctors = hospital.doctors.all().annotate(
            avg_rating=Avg("reviews__rating"),
            review_count=Count("reviews")
        )

        if specialty_slug:
            doctors = doctors.filter(specialties__slug=specialty_slug).distinct()
        if sort == "top":
            doctors = doctors.order_by("-avg_rating")
        elif sort == "new":
            doctors = doctors.order_by("-id")
        else:
            doctors = doctors.order_by("-id")

        return doctors

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        doctors = self.get_filtered_queryset()

        paginator = Paginator(doctors, 12)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            html = render_to_string(
                "profiles/partials/doctor_list.html",
                {"doctors": page_obj.object_list},
                request=request
            )
            return JsonResponse({"html": html, "url": request.get_full_path()})

        cache_key = f'hospital_specialties_{self.object.id}'
        hospital_specialties = cache.get(cache_key)
        if not hospital_specialties:
            hospital_specialties = list(Specialty.objects.filter(
                doctor__hospital=self.object
            ).distinct())
            cache.set(cache_key, hospital_specialties, CACHE_TTL)

        top_specialties = hospital_specialties[:3]

        context = {
            "hospital": self.object,
            "page_obj": page_obj,
            "doctors": page_obj.object_list,
            "specialties": hospital_specialties,
            "selected_specialty": request.GET.get("specialty"),
            "selected_sort": request.GET.get("sort"),
            "total_doctors": doctors.count(),
            "top_specialties": top_specialties,
        }
        return self.render_to_response(context)


def doctor_list_view(request):
    department_slug = request.GET.get('department', '')
    location_slug = request.GET.get('location', '')
    name_query = request.GET.get('name', '')
    sort = request.GET.get('sort', '')

    doctors = Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties').annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    order_map = {
        'rating': '-avg_rating',
        'experience': '-experience_years',
        'name': 'name',
    }
    doctors = doctors.order_by(order_map.get(sort, '-id'))

    if department_slug:
        doctors = doctors.filter(specialties__department__slug=department_slug).distinct()
    if location_slug:
        doctors = doctors.filter(location__slug=location_slug)
    if name_query:
        doctors = doctors.filter(name__icontains=name_query)

    paginator = Paginator(doctors, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_doctors = paginator.count

    cache_key = 'doctor_filter_dropdowns'
    filter_data = cache.get(cache_key)
    if not filter_data:
        filter_data = {
            'locations': list(Location.objects.all().order_by('name')),
            'departments': list(Department.objects.annotate(
                doctor_count=Count('specialties__doctor', distinct=True)
            ).filter(doctor_count__gt=0).order_by('name')),
        }
        cache.set(cache_key, filter_data, CACHE_TTL)

    # Top 6 department-location combos by doctor count
    cache_key = 'top_dept_locations'
    top_dept_locations = cache.get(cache_key)
    if not top_dept_locations:
        top_dept_locations = list(
            Doctor.objects.values(
                dept_slug=F('specialties__department__slug'),
                dept_name=F('specialties__department__name'),
                loc_slug=F('location__slug'),
                loc_name=F('location__name'),
            ).annotate(
                count=Count('id', distinct=True)
            ).filter(
                specialties__department__isnull=False,
                location__isnull=False
            ).order_by('-count')[:6]
        )
        cache.set(cache_key, top_dept_locations, CACHE_TTL)

    context = {
        'page_obj': page_obj,
        'doctors': page_obj.object_list,
        'locations': filter_data['locations'],
        'departments': filter_data['departments'],
        'top_dept_locations': top_dept_locations,
        'selected_department': department_slug,
        'selected_location': location_slug,
        'name_query': name_query,
        'sort': sort,
        'total_doctors': total_doctors,
    }
    return render(request, 'profiles/doctor_list.html', context)


def hospital_list_view(request):
    location_slug = request.GET.get('location', '')
    name_query = request.GET.get('name', '')
    sort = request.GET.get('sort', '')

    hospitals = Hospital.objects.select_related('location').annotate(
        avg_rating=Avg('doctors__reviews__rating'),
        review_count=Count('doctors__reviews', distinct=True),
        doctor_count=Count('doctors', distinct=True)
    )

    order_map = {
        'rating': '-avg_rating',
        'name': 'name',
    }
    hospitals = hospitals.order_by(order_map.get(sort, '-updated_at'))

    if location_slug:
        hospitals = hospitals.filter(location__slug=location_slug)
    if name_query:
        hospitals = hospitals.filter(name__icontains=name_query)

    paginator = Paginator(hospitals, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    total_hospitals = paginator.count

    cache_key = 'hospital_filter_locations'
    locations = cache.get(cache_key)
    if not locations:
        locations = list(Location.objects.all().order_by('name'))
        cache.set(cache_key, locations, CACHE_TTL)

    cache_key = 'hospital_top_locations'
    top_locations = cache.get(cache_key)
    if not top_locations:
        top_locations = list(Location.objects.annotate(
            hospital_count=Count('hospital')
        ).filter(hospital_count__gt=0).order_by('-hospital_count')[:6])
        cache.set(cache_key, top_locations, CACHE_TTL)

    context = {
        'page_obj': page_obj,
        'hospitals': page_obj.object_list,
        'locations': locations,
        'top_locations': top_locations,
        'selected_location': location_slug,
        'name_query': name_query,
        'sort': sort,
        'total_hospitals': total_hospitals,
    }
    return render(request, 'profiles/hospital_list.html', context)




LOCATION_NAMES = ['dhaka', 'chittagong', 'chattogram', 'barishal', 'barisal',
    'narayanganj', 'gazipur', 'cumilla', 'noakhali', 'bogura',
    'tangail', 'faridpur', 'brahmanbaria', 'savar', 'mirpur',
    'uttara', 'gulshan', 'banani', 'bashundhara', 'bangladesh']

SPECIALTY_NAMES = ['cancer', 'oncology', 'heart', 'cardiology', 'diabetes',
    'neuro', 'neurology', 'ortho', 'orthopedic', 'orthopedics',
    'eye', 'ophthalmology', 'ent', 'ear nose throat',
    'pediatric', 'pediatrics', 'child', 'children',
    'gyne', 'gynecology', 'pregnancy', 'obstetrics',
    'skin', 'dermatology', 'hair',
    'kidney', 'renal', 'nephrology',
    'liver', 'gastro', 'gastroenterology',
    'urology', 'psychiatry', 'mental', 'psychology',
    'surgery', 'general surgery', 'plastic', 'cosmetic',
    'medicine', 'internal medicine', 'physical',
    'rehabilitation', 'sports', 'spine', 'bone', 'joint']


def get_filter_dropdowns():
    cache_key = 'filter_dropdowns'
    data = cache.get(cache_key)
    if not data:
        data = {
            'locations': list(Location.objects.all().order_by('name')),
            'specialties': list(Specialty.objects.all().order_by('name')),
        }
        cache.set(cache_key, data, CACHE_TTL)
    return data


def top_doctors_view(request, department=None, location=None):
    department_slug = department or request.GET.get('department', '')
    # also support ?specialty= from query params (map to department)
    if not department_slug:
        department_slug = request.GET.get('specialty', '')
    location_slug = location or request.GET.get('location', '')
    query = request.GET.get('q', '')
    count = min(max(int(request.GET.get('count', 10)), 1), 50)

    if query:
        query_lower = query.lower()
        for loc in LOCATION_NAMES:
            if loc in query_lower:
                location_slug = loc
                break
        for spec in SPECIALTY_NAMES:
            if spec in query_lower:
                department_slug = spec
                break
        count_match = re.search(r'(top|best)\s*(\d+)', query_lower)
        if count_match:
            count = min(int(count_match.group(2)), 50)

    is_country_wide = location_slug.lower() in ['bangladesh', 'all', 'all-bangladesh', 'country-wide']

    doctors = Doctor.objects.select_related('hospital', 'location').prefetch_related('specialties').annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    if not is_country_wide and location_slug:
        doctors = doctors.filter(
            Q(location__slug__icontains=location_slug) |
            Q(location__name__icontains=location_slug)
        )
    if department_slug:
        doctors = doctors.filter(
            Q(specialties__department__slug__icontains=department_slug) |
            Q(specialties__department__name__icontains=department_slug)
        ).distinct()

    doctors = doctors.order_by('-avg_rating', '-review_count', '-id')
    paginator = Paginator(doctors, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    if paginator.count == 0:
        return redirect('doctor_list')

    location_display = "Bangladesh" if is_country_wide else "All Locations"
    department_display = None

    if location_slug and not is_country_wide:
        loc_obj = Location.objects.filter(
            Q(slug__iexact=location_slug) | Q(name__iexact=location_slug)
        ).first()
        location_display = loc_obj.name if loc_obj else location_slug.title()

    if department_slug:
        dept_obj = Department.objects.filter(
            Q(slug__iexact=department_slug) | Q(name__iexact=department_slug)
        ).first()
        department_display = dept_obj.name if dept_obj else department_slug.title().replace('-', ' ')

    dropdowns = get_filter_dropdowns()

    context = {
        'doctors': page_obj.object_list,
        'page_obj': page_obj,
        'location_slug': location_slug,
        'location_display': location_display,
        'department_slug': department_slug,
        'department_display': department_display,
        'count': count,
        'total_doctors': paginator.count,
        'is_country_wide': is_country_wide,
        'query': query,
        'all_locations': dropdowns['locations'][:20],
        'all_specialties': dropdowns['specialties'][:30],
    }
    return render(request, 'profiles/top_doctors.html', context)


HOSPITAL_LOCATION_NAMES = ['dhaka', 'chittagong', 'chattogram', 'barishal', 'barisal',
    'sylhet', 'khulna', 'rajshahi', 'rangpur', 'mymensingh',
    'narayanganj', 'gazipur', 'cumilla', 'noakhali', 'bogura',
    'tangail', 'faridpur', 'brahmanbaria', 'savar', 'mirpur',
    'uttara', 'gulshan', 'banani', 'bashundhara']

HOSPITAL_SPECIALTY_NAMES = ['cancer', 'heart', 'cardiology', 'diabetes', 'neuro',
    'neurology', 'ortho', 'orthopedic', 'eye', 'ent', 'pediatric',
    'child', 'gyne', 'gynecology', 'pregnancy', 'skin', 'dermatology',
    'kidney', 'renal', 'liver', 'gastro', 'gastroenterology',
    'urology', 'psychiatry', 'mental', 'oncology']


def top_hospitals_view(request, location=None):
    location_slug = location or request.GET.get('location', '')
    specialty_slug = request.GET.get('specialty', '')
    query = request.GET.get('q', '')
    count = min(max(int(request.GET.get('count', 10)), 1), 50)

    if query:
        query_lower = query.lower()
        for loc in HOSPITAL_LOCATION_NAMES:
            if loc in query_lower:
                location_slug = loc
                break
        for spec in HOSPITAL_SPECIALTY_NAMES:
            if spec in query_lower:
                specialty_slug = spec
                break
        count_match = re.search(r'top\s*(\d+)', query_lower)
        if count_match:
            count = min(int(count_match.group(1)), 50)
        if query and not location_slug and not specialty_slug:
            query = query.strip()

    is_country_wide = location_slug.lower() in ['bangladesh', 'all', 'all-bangladesh', 'country-wide']

    hospitals = Hospital.objects.select_related('location').annotate(
        avg_rating=Avg('doctors__reviews__rating'),
        doctor_count=Count('doctors', distinct=True),
        review_count=Count('doctors__reviews', distinct=True)
    )

    if not is_country_wide and location_slug:
        hospitals = hospitals.filter(
            Q(location__slug__icontains=location_slug) |
            Q(location__name__icontains=location_slug)
        )
    if specialty_slug:
        hospitals = hospitals.filter(
            Q(doctors__specialties__slug__icontains=specialty_slug) |
            Q(doctors__specialties__name__icontains=specialty_slug)
        ).distinct()
    if query and not location_slug and not specialty_slug:
        hospitals = hospitals.filter(name__icontains=query)

    hospitals = hospitals.order_by('-avg_rating', '-review_count', '-doctor_count')[:count]

    location_display = "Bangladesh" if is_country_wide else "All Locations"
    specialty_display = None

    if location_slug and not is_country_wide:
        loc_obj = Location.objects.filter(
            Q(slug__iexact=location_slug) | Q(name__iexact=location_slug)
        ).first()
        location_display = loc_obj.name if loc_obj else location_slug.title()

    if specialty_slug:
        spec_obj = Specialty.objects.filter(
            Q(slug__iexact=specialty_slug) | Q(name__iexact=specialty_slug)
        ).first()
        specialty_display = spec_obj.name if spec_obj else specialty_slug.title()

    dropdowns = get_filter_dropdowns()

    context = {
        'hospitals': hospitals,
        'location_slug': location_slug,
        'location_display': location_display,
        'specialty_slug': specialty_slug,
        'specialty_display': specialty_display,
        'count': count,
        'is_country_wide': is_country_wide,
        'query': query,
        'all_locations': dropdowns['locations'][:20],
    }
    return render(request, 'profiles/top_hospitals.html', context)


def department_list_view(request):
    """List all departments with doctor/specialty counts."""
    name_query = request.GET.get('name', '')
    sort = request.GET.get('sort', '')

    departments = Department.objects.annotate(
        doctor_count=Count('specialties__doctor', distinct=True),
        specialty_count=Count('specialties', distinct=True),
        avg_rating=Avg('specialties__doctor__reviews__rating'),
        review_count=Count('specialties__doctor__reviews', distinct=True),
    )

    order_map = {
        'rating': '-avg_rating',
        'name': 'name',
        'doctors': '-doctor_count',
    }
    departments = departments.order_by(order_map.get(sort, 'name'))

    if name_query:
        departments = departments.filter(name__icontains=name_query)

    total_departments = departments.count()

    # Top 6 departments by doctor count for featured cards
    cache_key = 'department_list_top_departments'
    top_departments = cache.get(cache_key)
    if not top_departments:
        top_departments = list(Department.objects.annotate(
            doctor_count=Count('specialties__doctor', distinct=True)
        ).filter(doctor_count__gt=0).order_by('-doctor_count')[:6])
        cache.set(cache_key, top_departments, CACHE_TTL)

    context = {
        'departments': departments,
        'top_departments': top_departments,
        'total_departments': total_departments,
        'name_query': name_query,
        'sort': sort,
    }
    return render(request, 'profiles/department_list.html', context)


def department_detail_view(request, slug):
    department = get_object_or_404(Department, slug=slug)
    specialties = Specialty.objects.filter(department=department).annotate(
        doctor_count=Count('doctor')
    )
    doctors = Doctor.objects.filter(specialties__department=department).select_related(
        'hospital', 'location'
    ).prefetch_related('specialties').annotate(
        avg_rating=Avg('reviews__rating'), review_count=Count('reviews')
    ).distinct().order_by('-avg_rating')

    context = {
        'department': department,
        'specialties': specialties,
        'doctors': doctors,
        'total_doctors': doctors.count(),
    }
    return render(request, 'profiles/department_detail.html', context)

