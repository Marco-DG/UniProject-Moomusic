from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import Group
from .forms import UserLoginForm, RegistrationForm

def login_request(request):
    title = "Login"
    form = UserLoginForm(request.POST or None)
    if form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user:
            login(request, user)
            return redirect('home')
    # if not POST or not valid, fall through and re‑render
    return render(request, 'authentication/login.html', {
        'form':  form,
        'title': title,
    })

def signup_request(request):
    title = "Create Account"
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # 1️⃣ Save the new user
            user = form.save()
            # 2️⃣ Add them into the Listener group
            try:
                listener = Group.objects.get(name='Listener')
                user.groups.add(listener)
            except Group.DoesNotExist:
                # In case your groups haven’t been created yet:
                # you might log this or handle it gracefully
                pass
            # 3️⃣ Redirect to login (or log them in immediately if you prefer)
            return redirect('login')
        else:
            print("Signup form invalid:", form.errors)
    else:
        form = RegistrationForm()

    return render(request, 'authentication/signup.html', {
        'form':  form,
        'title': title,
    })

def logout_request(request):
    logout(request)
    return redirect('home')
