# DoctorUpload

Django-based doctor profile and hospital listing platform.

## Setup

```bash
# Clone the repo
git clone https://github.com/aouwalitshikkha/doctorupload.git
cd doctorupload

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Start dev server
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.
