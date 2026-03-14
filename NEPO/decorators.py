from django.shortcuts import redirect


def admin_only(view_func):
    def wrapper_func(request, *args, **kwargs):
        group = 'admin'  # Set the desired group name
        user_groups = request.user.groups.all()

        for user_group in user_groups:
            if user_group.name == 'Customer':
                return redirect('login')
            if user_group.name == 'Admin':
                return view_func(request, *args, **kwargs)

        # If the user doesn't belong to any group or none of the groups match
        return redirect('login')

    return wrapper_func