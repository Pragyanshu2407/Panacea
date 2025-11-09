import os
import sys
from pathlib import Path
import django

# Ensure project root is on PYTHONPATH when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'college_management_system.settings')
django.setup()

from main_app.models import CustomUser


def provision_admin(email: str, password: str):
    try:
        user = CustomUser.objects.create_superuser(
            email=email,
            password=password,
            first_name='Admin',
            last_name='User',
            gender='M',
            address='Admin Address',
            profile_pic='blank-profile-picture-973460_640.webp',
            user_type='1',  # HOD
        )
        print('Created new admin user:', email)
        return
    except Exception as e:
        # Fallback: update if user exists
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            raise
        user.is_staff = True
        user.is_superuser = True
        user.user_type = '1'
        if not user.gender:
            user.gender = 'M'
        if not user.address:
            user.address = 'Admin Address'
        if not user.profile_pic:
            user.profile_pic = 'blank-profile-picture-973460_640.webp'
        user.set_password(password)
        user.save()
        print('Updated existing admin user:', email)


if __name__ == '__main__':
    import traceback
    try:
        provision_admin('admin@gmail.com', 'admin@123')
        with open('provision_admin.log', 'a') as f:
            f.write('SUCCESS: Provisioned admin user admin@gmail.com\n')
    except Exception as e:
        with open('provision_admin.log', 'a') as f:
            f.write('ERROR provisioning admin: ' + str(e) + '\n')
            f.write(traceback.format_exc() + '\n')