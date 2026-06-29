from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import Location, Department, Specialty, Hospital, Doctor, Experience, Review


class ModelTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(name='Dhaka', slug='dhaka')
        self.department = Department.objects.create(name='Cardiology', slug='cardiology')
        self.specialty = Specialty.objects.create(name='Cardiology', slug='cardiology')
        self.specialty.department.add(self.department)
        self.hospital = Hospital.objects.create(
            name='Test Hospital', slug='test-hospital',
            location=self.location, address='123 Test St',
            contact_numbers='+880-2-1234567', index_status=True
        )
        self.doctor = Doctor.objects.create(
            name='Dr. Test', slug='dr-test-1', location=self.location,
            designation='Cardiologist', qualifications='MBBS, FCPS',
            experience_years=10, hospital=self.hospital,
            about='Test doctor about text.'
        )
        self.doctor.specialties.add(self.specialty)

    def test_location_str(self):
        self.assertEqual(str(self.location), 'Dhaka')

    def test_department_str(self):
        self.assertEqual(str(self.department), 'Cardiology')

    def test_specialty_str(self):
        self.assertEqual(str(self.specialty), 'Cardiology')

    def test_hospital_str(self):
        self.assertEqual(str(self.hospital), 'Test Hospital')

    def test_hospital_get_contact_numbers_list(self):
        self.assertEqual(self.hospital.get_contact_numbers_list(), ['+880-2-1234567'])

    def test_doctor_str(self):
        self.assertEqual(str(self.doctor), 'Dr. Test')

    def test_doctor_get_absolute_url(self):
        expected = reverse('doctor_profile', kwargs={'slug': self.doctor.slug})
        self.assertEqual(self.doctor.get_absolute_url(), expected)

    def test_hospital_get_absolute_url(self):
        expected = reverse('hospital_detail', kwargs={'slug': self.hospital.slug})
        self.assertEqual(self.hospital.get_absolute_url(), expected)

    def test_doctor_profile_picture_default(self):
        url = self.doctor.get_profile_picture_url()
        self.assertIn('default_doctor.jpg', url)

    def test_department_get_symptoms_list(self):
        dept = Department.objects.create(name='Test', slug='test', symptoms='fever, cough\nheadache')
        self.assertEqual(dept.get_symptoms_list(), ['fever', 'cough', 'headache'])

    def test_hospital_facilities_list(self):
        self.hospital.facilities = 'Parking\nCafeteria'
        self.hospital.save()
        self.assertEqual(self.hospital.get_facilities_list(), ['Parking', 'Cafeteria'])

    def test_experience_creation(self):
        exp = Experience.objects.create(
            doctor=self.doctor, position='Junior Consultant',
            hospital_name='City Hospital', start_year=2020, end_year=2023,
            description='Worked as junior consultant.'
        )
        self.assertEqual(str(exp), 'Junior Consultant at City Hospital')

    def test_review_creation(self):
        review = Review.objects.create(
            doctor=self.doctor, patient_name='John Doe',
            rating=4.5, comment='Great doctor!'
        )
        self.assertEqual(str(review), 'Review for Dr. Test by John Doe')
        self.assertEqual(review.rating, 4.5)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.location = Location.objects.create(name='Dhaka', slug='dhaka')
        self.department = Department.objects.create(name='Cardiology', slug='cardiology')
        self.specialty = Specialty.objects.create(name='Cardiology', slug='cardiology')
        self.specialty.department.add(self.department)
        self.hospital = Hospital.objects.create(
            name='Test Hospital', slug='test-hospital',
            location=self.location, index_status=True
        )
        self.doctor = Doctor.objects.create(
            name='Dr. Test', slug='dr-test-1', location=self.location,
            designation='Cardiologist', qualifications='MBBS',
            hospital=self.hospital, about='Test.'
        )
        self.doctor.specialties.add(self.specialty)

    def test_home_view(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Hospital')
        self.assertContains(response, 'Dr. Test')

    def test_home_view_search_doctor(self):
        response = self.client.get('/', {'name': 'Dr. Test'})
        self.assertEqual(response.status_code, 200)

    def test_home_view_search_hospital(self):
        response = self.client.get('/', {'hospital_name': 'Test Hospital'})
        self.assertIn(response.status_code, [200, 302])

    def test_doctor_list_view(self):
        response = self.client.get(reverse('doctor_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dr. Test')

    def test_doctor_list_view_filtered(self):
        response = self.client.get(reverse('doctor_list'), {'department': 'cardiology', 'location': 'dhaka'})
        self.assertEqual(response.status_code, 200)

    def test_doctor_profile_view(self):
        response = self.client.get(reverse('doctor_profile', kwargs={'slug': self.doctor.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dr. Test')

    def test_doctor_profile_view_not_found(self):
        response = self.client.get('/nonexistent-doctor/')
        self.assertEqual(response.status_code, 404)

    def test_hospital_list_view(self):
        response = self.client.get(reverse('hospital_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Hospital')

    def test_hospital_detail_view(self):
        response = self.client.get(reverse('hospital_detail', kwargs={'slug': self.hospital.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Hospital')

    def test_hospital_detail_view_ajax(self):
        response = self.client.get(
            reverse('hospital_detail', kwargs={'slug': self.hospital.slug}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('html', data)
        self.assertIn('url', data)

    def test_department_list_view(self):
        response = self.client.get(reverse('department_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cardiology')

    def test_department_detail_view(self):
        response = self.client.get(reverse('department_detail', kwargs={'slug': 'cardiology'}))
        self.assertEqual(response.status_code, 200)

    def test_about_view(self):
        response = self.client.get(reverse('about_us'))
        self.assertEqual(response.status_code, 200)

    def test_contact_view(self):
        response = self.client.get(reverse('contact_us'))
        self.assertEqual(response.status_code, 200)

    def test_verification_policy_view(self):
        response = self.client.get(reverse('verification_policy'))
        self.assertEqual(response.status_code, 200)

    def test_editorial_policy_view(self):
        response = self.client.get(reverse('editorial_policy'))
        self.assertEqual(response.status_code, 200)

    def test_privacy_policy_view(self):
        response = self.client.get(reverse('privacy_policy'))
        self.assertEqual(response.status_code, 200)

    def test_terms_of_service_view(self):
        response = self.client.get(reverse('terms_of_service'))
        self.assertEqual(response.status_code, 200)


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser('apiadmin', 'api@example.com', 'admin123')
        self.client.force_authenticate(user=self.admin)
        self.location = Location.objects.create(name='Dhaka', slug='dhaka')
        self.hospital = Hospital.objects.create(name='Test Hospital', slug='test-hospital', location=self.location)
        self.specialty = Specialty.objects.create(name='Cardiology', slug='cardiology')
        self.doctor = Doctor.objects.create(name='Dr. Test', slug='dr-test-1', location=self.location, hospital=self.hospital, about='Test.')

    def test_list_locations(self):
        response = self.client.get('/api/locations/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_doctors(self):
        response = self.client.get('/api/doctors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_doctors(self):
        response = self.client.get('/api/doctors/', {'search': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_list_hospitals(self):
        response = self.client.get('/api/hospitals/')
        self.assertEqual(response.status_code, 200)

    def test_list_specialties(self):
        response = self.client.get('/api/specialties/')
        self.assertEqual(response.status_code, 200)

    def test_list_departments(self):
        response = self.client.get('/api/departments/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)

    def test_non_admin_cannot_access_api(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/doctors/')
        self.assertEqual(response.status_code, 403)

    def test_doctor_detail(self):
        response = self.client.get(f'/api/doctors/{self.doctor.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Dr. Test')

    def test_doctor_top_rated(self):
        response = self.client.get('/api/doctors/top_rated/')
        self.assertEqual(response.status_code, 200)

    def test_doctor_filter_by_location(self):
        response = self.client.get('/api/doctors/', {'location': 'dhaka'})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_hospital_detail(self):
        response = self.client.get(f'/api/hospitals/{self.hospital.id}/')
        self.assertEqual(response.status_code, 200)

    def test_hospital_top_rated(self):
        response = self.client.get('/api/hospitals/top_rated/')
        self.assertEqual(response.status_code, 200)

    def test_location_detail(self):
        response = self.client.get(f'/api/locations/{self.location.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('doctor_count', response.data)

    def test_create_review_via_api(self):
        response = self.client.post('/api/reviews/', {
            'doctor': self.doctor.id,
            'patient_name': 'Test Patient',
            'rating': 4.5,
            'comment': 'Great doctor',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['rating'], 4.5)

    def test_api_schema_endpoint_accessible(self):
        response = self.client.get('/api/')
        self.assertEqual(response.status_code, 200)
