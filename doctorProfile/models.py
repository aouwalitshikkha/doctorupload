from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.text import slugify
from django.templatetags.static import static
from django.urls import reverse
from ckeditor.fields import RichTextField
import re

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    symptoms = models.TextField(blank=True, help_text="Enter symptoms separated by commas or new lines" )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_symptoms_list(self):
        if not self.symptoms:
            return []
        return [s.strip() for s in self.symptoms.replace(',', '\n').split('\n') if s.strip()]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1

            while Department.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)



class Location(models.Model):
    name = models.CharField(max_length=200, unique=True, db_index=True)
    slug = models.SlugField(unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Locations'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Specialty(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    department = models.ManyToManyField(Department, blank=True, related_name="specialties")

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Specialties'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Specialty.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

class Hospital(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(unique=True, max_length=255, blank=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    contact_numbers = models.TextField(
        blank=True, 
        null=True,
        help_text="Store multiple contact numbers separated by commas"
    )
    diagnosis = models.TextField(blank=True, null=True)
    facilities = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='records/images/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    about = models.TextField(blank=True, null=True)
    index_status = models.BooleanField(default=False, db_index=True, help_text="Allow search engines to index this page")

    class Meta:
        ordering = ['-updated_at']
        verbose_name_plural = 'Hospitals'

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)[:255]
            counter = 1
            while Hospital.objects.filter(slug=self.slug).exists():
                suffix = f'-{counter}'
                self.slug = slugify(self.name)[:255 - len(suffix)] + suffix
                counter += 1
        super().save(*args, **kwargs)

    def get_contact_numbers_list(self):
        if not self.contact_numbers:
            return []
        return [num.strip() for num in re.split(r"[;,]", self.contact_numbers) if num.strip()]
    
    def get_facilities_list(self):
        if not self.facilities:
            return []
        return [item.strip() for item in self.facilities.split("\n") if item.strip()]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('hospital_detail', kwargs={'slug': self.slug})


class Doctor(models.Model):
    name = models.CharField(max_length=100, db_index=True)
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='doctors/', null=True, blank=True)
    qualifications = models.CharField(max_length=255)
    experience_years = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    about = RichTextField(config_name='default')
    specialties = models.ManyToManyField(Specialty, blank=True)
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctors',)
    slug = models.SlugField(max_length=255, unique=True, blank=True, help_text="URL-friendly identifier for the doctor.")

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('doctor_profile', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new or not self.slug:
            self.slug = f"{slugify(self.name)}-{self.pk}"
            super(Doctor, self).save(update_fields=['slug'])
            
    def get_profile_picture_url(self):
        if self.profile_picture and hasattr(self.profile_picture, 'url'):
            return self.profile_picture.url
        return static('images/default_doctor.jpg')

class Experience(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='experiences', on_delete=models.CASCADE)
    position = models.CharField(max_length=100)
    hospital_name = models.CharField(max_length=200)
    start_year = models.PositiveIntegerField(null=True, blank=True)
    end_year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.position} at {self.hospital_name}"

class Review(models.Model):
    doctor = models.ForeignKey(Doctor, related_name='reviews', on_delete=models.CASCADE)
    patient_name = models.CharField(max_length=100)
    rating = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(5.0)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review for {self.doctor.name} by {self.patient_name}"
