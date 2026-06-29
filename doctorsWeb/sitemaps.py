from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.db.models import Count, F
from doctorProfile.models import Doctor, Hospital, Department, Location


class StaticSitemap(Sitemap):
    """Homepage, listing pages, and static info pages."""
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return [
            ('home', 1.0),
            ('doctor_list', 0.8),
            ('hospital_list', 0.8),
            ('department_list', 0.8),
            ('about_us', 0.6),
            ('contact_us', 0.6),
            ('verification_policy', 0.4),
            ('editorial_policy', 0.4),
            ('privacy_policy', 0.4),
            ('terms_of_service', 0.4),
        ]

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]


class DoctorSitemap(Sitemap):
    """Individual doctor profile pages."""
    changefreq = 'weekly'
    priority = 0.7

    def items(self):
        return Doctor.objects.all().order_by('-id')

    def location(self, obj):
        return reverse('doctor_profile', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return getattr(obj, 'updated_at', None)


class HospitalSitemap(Sitemap):
    """Individual hospital detail pages."""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Hospital.objects.filter(index_status=True).order_by('-updated_at')

    def location(self, obj):
        return reverse('hospital_detail', kwargs={'slug': obj.slug})

    def lastmod(self, obj):
        return obj.updated_at


class DepartmentSitemap(Sitemap):
    """Individual department detail pages (e.g. /department/cardiology/)."""
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Department.objects.all().order_by('name')

    def location(self, obj):
        return reverse('department_detail', kwargs={'slug': obj.slug})


class TopDoctorLocationSitemap(Sitemap):
    """Top doctors by department + location combos (e.g. /top-cardiology-doctors-in-dhaka/)."""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return (
            Doctor.objects
            .values(
                dept_slug=F('specialties__department__slug'),
                loc_slug=F('location__slug'),
            )
            .annotate(dc=Count('id'))
            .filter(
                dc__gt=0,
                specialties__department__isnull=False,
                location__isnull=False,
            )
            .order_by('-dc')
        )

    def location(self, item):
        return reverse('top_doctors_department_location', kwargs={
            'department': item['dept_slug'],
            'location': item['loc_slug'],
        })

    def lastmod(self, item):
        return None


class TopHospitalLocationSitemap(Sitemap):
    """Top hospitals by location (e.g. /top-hospitals-in-dhaka/)."""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return (
            Location.objects
            .annotate(hc=Count('hospital'))
            .filter(hc__gt=0)
            .order_by('-hc')
            .values('slug')
        )

    def location(self, item):
        return reverse('top_hospitals_location', kwargs={
            'location': item['slug'],
        })

    def lastmod(self, item):
        return None
