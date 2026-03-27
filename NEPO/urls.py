from django.urls import path
from . import views
from django.contrib.auth import views as auth_view

urlpatterns = [
    path('', views.schlarship, name='schlarship'),
    path('apply/', views.apply, name='apply'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_completion/', views.password_completion, name='password_completion'),
    path('forgot_password/', views.forgot_password, name='forget'),
    path('verify/', views.verify_code, name='verify'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('success/', views.success, name='success_page'),
    path('oversee/', views.oversee, name='admin'),
    path('update-deadline/', views.update_deadline, name='update_deadline'),
path('api/universities/', views.get_universities),
    path('student-api/', views.student_api, name='student_api'),
]