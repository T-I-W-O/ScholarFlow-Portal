# customer/signals.py
import datetime
import sys
import os
from decouple import config
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.dispatch import receiver
from django.db.models.signals import  post_migrate
from django.urls import reverse




from .models import *

def debug(msg):
    print(f"🐞 [DEBUG] {msg}")

@receiver(post_migrate)
def setup_roles(sender, **kwargs):
    # Only run once, when your app is migrated
    if sender.name != 'NEPO': 
        return

    debug("🚀 Starting Superuser & Group setup...")
    User = get_user_model()

    # 1. Ensure Groups exist
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    student_group, _ = Group.objects.get_or_create(name='Student')
    debug("Groups ensured: admin and student")

    # Give all permissions to admin group (optional)
    if not admin_group.permissions.exists():
        admin_group.permissions.set(Permission.objects.all())
        debug("Permissions bound to admin group.")

    # 2. Get Superuser credentials from env
    username = config("DJANGO_SU_USERNAME", default=None)
    email = config("DJANGO_SU_EMAIL", default=None)
    password = config("DJANGO_SU_PASSWORD", default=None)

    if not all([username, email, password]):
        debug("❌ Skipping: Missing DJANGO_SU env variables.")
        return

    # 3. Create or update Superuser
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_staff': True, 'is_superuser': True, 'is_active': True}
    )

    if created:
        user.set_password(password)
        user.save()
        debug(f"✅ Created NEW superuser: {username}")
    else:
        # Sync flags and password if changed
        needs_save = False
        if not (user.is_staff and user.is_superuser and user.is_active):
            user.is_staff = user.is_superuser = user.is_active = True
            needs_save = True
        if not user.check_password(password):
            user.set_password(password)
            needs_save = True
        if needs_save:
            user.save()
            debug(f"✅ Updated existing superuser: {username}")

    # 4. Assign admin group to superuser only
    if not user.groups.filter(name='admin').exists():
        user.groups.add(admin_group)
        debug(f"✅ Superuser added to admin group")

    debug("✅ Admin-Student profile sync complete.")