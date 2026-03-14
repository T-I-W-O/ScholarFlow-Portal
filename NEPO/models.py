from django.db import models
from django.contrib.auth.models import User
import random
import string
from django.utils import timezone
from datetime import timedelta

class PasswordResetCode(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='reset_codes',null=True, blank=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        # Code expires after 15 minutes
        expiration_time = self.created_at + timedelta(minutes=15)
        return timezone.now() < expiration_time and not self.is_used

    def __str__(self):
        return f"Code for {self.student.email}: {self.code}"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    name = models.CharField(max_length=200)
    number = models.CharField(max_length=11)
    email = models.EmailField(max_length=100)
    university = models.CharField(max_length=200)
    course = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    paid = models.BooleanField(default=False)
    matric = models.CharField(max_length=20,null=True,blank=True)
    transaction_id = models.CharField(max_length=20,null=True,blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    def __str__(self):
        return f'{self.name}'


class Deadline(models.Model):
    date = models.DateField()

    def __str__(self):
        return str(self.date)

class SiteVisit(models.Model):
    date = models.DateField(auto_now_add=True)
    count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date} - {self.count} visits"