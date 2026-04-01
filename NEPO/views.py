import json
import random

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from .models import * # Note: Generally better to list models explicitly
from .decorators import admin_only
import requests
#---------------------------------------
import requests
from django.http import JsonResponse

def get_universities(request):
    url = "http://universities.hipolabs.com/search?country=Nigeria" # Try http if https fails
    try:
        # Added a 5-second timeout so your server doesn't hang forever
        res = requests.get(url, timeout=5)
        res.raise_for_status() 
        return JsonResponse(res.json(), safe=False)
    except Exception as e:
        # Log the error and return an empty list so the frontend doesn't crash
        print(f"API Error: {e}")
        return JsonResponse([], safe=False)


def apply(request):
    if request.method == 'POST':
        # 1. Get data from the form
        name = request.POST.get('fullname')
        email = request.POST.get('email')
        raw_number = request.POST.get('phone')
        university = request.POST.get('university')
        course = request.POST.get('course')
        password = request.POST.get('password')

        # 2. CHECK IF EMAIL EXISTS BEFORE CREATING ANYTHING
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered. Please login or use a different email.")
            return render(request, 'apply.html')

        formatted_number = f"0{raw_number}"

        try:
            # 3. Create the Django User (Only happens if email check passed)
            user = User.objects.create_user(
                username=email, 
                email=email, 
                password=password,
                first_name=name
            )

            # 4. Assign to "Student" Group
            student_group, created = Group.objects.get_or_create(name='Student')
            user.groups.add(student_group)

            # 5. Create the Student Profile
            Student.objects.create(
                user=user,
                name=name,
                number=formatted_number,
                email=email,
                university=university,
                course=course
            )

            # --- EMAIL LOGIC ---
            subject = "Welcome to NepoScholarship!"
            login_url = request.build_absolute_uri('/login')
            context = {'name': name, 'login_url': login_url}
            
            html_content = render_to_string('emails/welcome_email.html', context)
            text_content = strip_tags(html_content)

            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False,
            )

            messages.success(request, "Registration successful! A welcome email has been sent.")
            return redirect('login')

        except Exception as e:
            # If anything fails here (like a DB connection issue), 
            # we catch the specific error message.
            
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'apply.html')

    return render(request, 'apply.html')

def schlarship(request):
    # Count unique visitor using session
    if not request.session.get('visited'):
        visit = SiteVisit.objects.first()

        if not visit:
            visit = SiteVisit.objects.create(count=1)
        else:
            visit.count += 1
            visit.save()

        request.session['visited'] = True

    # Fetch deadline
    deadline_obj = Deadline.objects.first()

    context = {
        'deadline': deadline_obj
    }

    return render(request, 'schlarship.html', context)

from django.contrib.auth.models import User

def login(request):
    # 1. USER ALREADY LOGGED IN
    if request.user.is_authenticated:

        # Check if user is Admin
        if request.user.groups.filter(name='Admin').exists():
            return redirect('admin')

        # Check if user is Student
        if request.user.groups.filter(name='Student').exists():
            try:
                student = request.user.customer

                if student.paid:
                    return redirect('success_page')

                return render(request, 'login.html', {
                    'show_modal': True,
                    'student': student,
                    'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY
                })

            except Student.DoesNotExist:
                return redirect('apply')

    # 2. LOGIN PROCESS
    if request.method == 'POST':

        email = request.POST.get('email')
        password = request.POST.get('password')

        # --- ADDED LOGIC (email -> username) ---
        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            username = None
        # --------------------------------------

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)

            # After login check group
            if user.groups.filter(name='Admin').exists():
                return redirect('admin')

            if user.groups.filter(name='Student').exists():
                return redirect('login')  # reload page so modal logic runs

        else:
            return render(request, 'login.html', {
                'error': 'Invalid email or password.',
                'email_val': email
            })

    # 3. SHOW LOGIN FORM
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def success(request):
    # Get the student profile for the currently logged-in user
    student = request.user.customer 
    return render(request, 'sucess.html', {'student': student})

from django.contrib.auth import get_user_model

User = get_user_model()  # use Django's user model

def forgot_password(request):
    if request.method == 'POST':
        email_input = request.POST.get('email')
        
        try:
            # Look for the user by email
            user = User.objects.get(email=email_input)
            
            # 1. Generate a 6-digit code (format: 123456)
            reset_code_raw = ''.join(random.choices('0123456789', k=6))
            
            # 2. Save code to database
            PasswordResetCode.objects.create(user=user, code=reset_code_raw)
            
            # 3. Prepare HTML Email
            display_code = f"{reset_code_raw[:3]}-{reset_code_raw[3:]}"
            
            subject = "Password Recovery Code - NepoScholarship"
            context = {
                'name': getattr(user, 'name', user.username),  # fallback if 'name' not on user
                'code': display_code,
            }
            
            html_message = render_to_string('emails/password_reset_email.html', context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email_input],
                html_message=html_message,
                fail_silently=False,
            )
            
            request.session['reset_email'] = email_input
            messages.success(request, "A recovery code has been sent to your email.")
            return redirect('verify') 

        except User.DoesNotExist:
            messages.error(request, "This email is not registered in our system.")
            
    return render(request, 'account_recovery.html')

def verify_code(request):
    # Get the email from the session (saved during the forgot_password view)
    email = request.session.get('reset_email')
    
    if not email:
        messages.error(request, "Session expired. Please start again.")
        return redirect('forget')

    if request.method == 'POST':
        # Get the 6 digits from the individual inputs or a single hidden field
        # In the HTML below, we'll combine them into a single 'otp' string
        user_code = request.POST.get('otp')
        
        try:
            student = Student.objects.get(email=email)
            # Find the most recent code for this student
            record = PasswordResetCode.objects.filter(student=student, is_used=False).latest('created_at')
            
            # 1. Check if code matches
            if record.code != user_code:
                messages.error(request, "The code you entered is incorrect.")
                return render(request, 'verify_code.html', {'error': True})
            
            # 2. Check if expired (using the model method we created earlier)
            if not record.is_valid():
                messages.error(request, "This code has expired (15-minute limit).")
                return render(request, 'verify_code.html', {'expired': True})
            
            # Success!
            record.is_used = True
            record.save()
            request.session['can_reset_password'] = True # Security gate for next page
            return redirect('password_completion')

        except (Student.DoesNotExist, PasswordResetCode.DoesNotExist):
            messages.error(request, "Invalid request. Please try again.")
            return redirect('forget')

    return render(request, 'verify_code.html')

def password_completion(request):
    # Security Check: Ensure they actually passed the verification step
    if not request.session.get('can_reset_password'):
        messages.error(request, "Unauthorized access. Please verify your code first.")
        return redirect('forget')

    email = request.session.get('reset_email')

    if request.method == 'POST':
        new_password = request.POST.get('password')
        
        try:
            # 1. Find the User associated with this email
            user = User.objects.get(email=email)
            
            # 2. Update the password (this handles the hashing/security)
            user.set_password(new_password)
            user.save()

            # 3. Clean up the session so they can't reuse the reset access
            del request.session['can_reset_password']
            del request.session['reset_email']

            messages.success(request, "Your password has been updated successfully! Please log in.")
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, "An error occurred. User not found.")
            return redirect('forget')

    return render(request, 'password.html')

def verify_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            matric = data.get('matric')
            # Use the reference sent from the frontend (the NEPO-XXXXX id)
            tx_id = data.get('reference') 
            
            student = request.user.customer
            
            # Update Student Model
            student.matric = matric
            student.paid = True
            student.transaction_id = tx_id # It now matches Paystack exactly
            student.paid_at = timezone.now()
            student.save()
            
            # Prepare Email Content
            subject = "Payment Successful - NepoScholarship"
            context = {
                'student': student,
                'transaction_id': tx_id,
                'payment_date': student.paid_at.strftime("%B %d, %Y"),
            }
            
            html_content = render_to_string('emails/payment_success.html', context)
            text_content = strip_tags(html_content)

            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[student.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@admin_only
def oversee(request):
    today = timezone.now().date()

    # --- Website Visits ---
    total_visits = SiteVisit.objects.aggregate(total=Sum('count'))['total'] or 0
    # Get today's visits (if the record exists)
    today_visit_record = SiteVisit.objects.filter(date=today).first()
    today_visits = today_visit_record.count if today_visit_record else 0

    # --- Applicants ---
    total_applicants = Student.objects.count()
    today_applicants = Student.objects.filter(created_at__date=today).count()

    # --- Payments ---
    total_paid = Student.objects.filter(paid=True).count()
    today_paid = Student.objects.filter(paid=True, paid_at__date=today).count()
    current_deadline = Deadline.objects.first()
    context = {
        'total_visits': total_visits,
        'today_visits': today_visits,
        'total_applicants': total_applicants,
        'today_applicants': today_applicants,
        'total_paid': total_paid,
        'today_paid': today_paid,
        'deadline_date': current_deadline.date.strftime('%Y-%m-%d') if current_deadline else "",
    }

    return render(request, 'admin.html', context)

@csrf_exempt # Use this for simplicity, or include the CSRF token in your JS header
def update_deadline(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        new_date = data.get('date')
        
        # Get the first existing deadline or create one if it doesn't exist
        deadline_obj, created = Deadline.objects.get_or_create(id=1)
        deadline_obj.date = new_date
        deadline_obj.save()
        
        return JsonResponse({'status': 'success', 'date': str(deadline_obj.date)})
    return JsonResponse({'status': 'failed'}, status=400)

def student_api(request):
    search_query = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    limit = 5
    start = (page - 1) * limit
    end = start + limit

    students_list = Student.objects.all().order_by('-created_at')

    # Advanced Search Logic
    if search_query:
        # Handle "paid/unpaid" specifically
        if search_query.lower() == 'paid':
            students_list = students_list.filter(paid=True)
        elif search_query.lower() == 'unpaid':
            students_list = students_list.filter(paid=False)
        else:
            students_list = students_list.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(university__icontains=search_query) |
                Q(course__icontains=search_query) |
                Q(number__icontains=search_query) |
                Q(matric__icontains=search_query) |
                Q(transaction_id__icontains=search_query)
            )

    total_count = students_list.count()
    # Slice for pagination
    paginated_students = students_list[start:end]

    data = []
    for s in paginated_students:
        data.append({
            "name": s.name,
            "email": s.email,
            "university": s.university,
            "matric": s.matric or "-",
            "course": s.course,
            "number": s.number,
            "paid": s.paid,
            "transaction_id": s.transaction_id or "-"
        })

    return JsonResponse({
        "students": data,
        "total_count": total_count,
        "page": page,
        "has_next": end < total_count,
        "has_prev": page > 1,
        "start_index": start + 1 if total_count > 0 else 0,
        "end_index": min(end, total_count)
    })

