from rest_framework import serializers
from .models import Department, Location, Specialty, Hospital, Doctor, Experience, Review


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'slug']


class LocationDetailSerializer(serializers.ModelSerializer):
    doctor_count = serializers.SerializerMethodField()
    hospital_count = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = ['id', 'name', 'slug', 'doctor_count', 'hospital_count']

    def get_doctor_count(self, obj):
        return Doctor.objects.filter(location=obj).count()

    def get_hospital_count(self, obj):
        return Hospital.objects.filter(location=obj).count()


class SpecialtySerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()

    class Meta:
        model = Specialty
        fields = ['id', 'name', 'slug', 'department']

    def get_department(self, obj):
        return [{'id': d.id, 'name': d.name, 'slug': d.slug} for d in obj.department.all()]


class SpecialtyDetailSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    doctor_count = serializers.SerializerMethodField()

    class Meta:
        model = Specialty
        fields = ['id', 'name', 'slug', 'department', 'doctor_count']

    def get_department(self, obj):
        return [{'id': d.id, 'name': d.name, 'slug': d.slug} for d in obj.department.all()]

    def get_doctor_count(self, obj):
        return Doctor.objects.filter(specialties=obj).count()


class DepartmentSerializer(serializers.ModelSerializer):
    doctor_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'slug', 'symptoms', 'doctor_count']


class DepartmentDetailSerializer(serializers.ModelSerializer):
    specialties = SpecialtySerializer(many=True, read_only=True)
    doctor_count = serializers.IntegerField(read_only=True)
    specialty_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'name', 'slug', 'symptoms', 'specialties', 'doctor_count', 'specialty_count']

    def get_specialty_count(self, obj):
        return obj.specialties.count()


class HospitalSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    contact_numbers = serializers.ListField(child=serializers.CharField(), source='get_contact_numbers_list', read_only=True)
    facilities = serializers.ListField(child=serializers.CharField(), source='get_facilities_list', read_only=True)

    class Meta:
        model = Hospital
        fields = ['id', 'name', 'slug', 'location', 'address', 'contact_numbers', 'diagnosis', 'facilities', 'image', 'updated_at', 'about', 'index_status']


class HospitalDetailSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    contact_numbers = serializers.ListField(child=serializers.CharField(), source='get_contact_numbers_list', read_only=True)
    facilities = serializers.ListField(child=serializers.CharField(), source='get_facilities_list', read_only=True)
    doctor_count = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()

    class Meta:
        model = Hospital
        fields = ['id', 'name', 'slug', 'location', 'address', 'contact_numbers', 'diagnosis', 'facilities', 'image', 'updated_at', 'about', 'index_status', 'doctor_count', 'avg_rating']

    def get_doctor_count(self, obj):
        return Doctor.objects.filter(hospital=obj).count()

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = Doctor.objects.filter(hospital=obj).aggregate(avg=Avg('reviews__rating'))
        return result['avg']


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['id', 'doctor', 'position', 'hospital_name', 'start_year', 'end_year', 'description']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'doctor', 'patient_name', 'rating', 'comment', 'created_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['doctor', 'patient_name', 'rating', 'comment']

    def validate_rating(self, value):
        if value < 1.0 or value > 5.0:
            raise serializers.ValidationError('Rating must be between 1.0 and 5.0')
        return value


class DoctorListSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='hospital.name', read_only=True, default=None)
    location_name = serializers.CharField(source='location.name', read_only=True, default=None)
    profile_picture_url = serializers.SerializerMethodField()
    avg_rating = serializers.FloatField(read_only=True, default=None)
    review_count = serializers.IntegerField(read_only=True, default=0)
    specialties_list = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'slug', 'designation', 'qualifications',
            'experience_years', 'profile_picture_url', 'avg_rating',
            'review_count', 'hospital_name', 'location_name',
            'specialties_list',
        ]

    def get_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()

    def get_specialties_list(self, obj):
        return [{'id': s.id, 'name': s.name, 'slug': s.slug} for s in obj.specialties.all()]


class DoctorSerializer(serializers.ModelSerializer):
    hospital = HospitalSerializer(read_only=True)
    hospital_id = serializers.PrimaryKeyRelatedField(
        queryset=Hospital.objects.all(),
        source='hospital',
        write_only=True,
        required=False,
        allow_null=True,
    )
    specialties = SpecialtySerializer(many=True, read_only=True)
    specialties_ids = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.all(),
        source='specialties',
        many=True,
        write_only=True,
        required=False,
    )
    location = LocationSerializer(read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    experiences = ExperienceSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'location', 'designation', 'profile_picture', 'profile_picture_url',
            'qualifications', 'experience_years', 'about', 'specialties', 'specialties_ids',
            'hospital', 'hospital_id', 'slug', 'experiences', 'reviews',
            'avg_rating', 'review_count',
        ]

    def get_profile_picture_url(self, obj):
        return obj.get_profile_picture_url()

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = obj.reviews.aggregate(avg=Avg('rating'))
        return result['avg']

    def get_review_count(self, obj):
        return obj.reviews.count()
