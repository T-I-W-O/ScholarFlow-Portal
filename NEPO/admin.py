from django.contrib import admin

# Register your models here.
from .models import *
REGISTER = {Deadline,Student}
admin.site.register(REGISTER)