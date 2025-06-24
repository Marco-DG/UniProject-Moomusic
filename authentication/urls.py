from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# Add URLConf
urlpatterns = [
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='authentication/login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),
    path('signup/', views.signup_request, name='signup'),
    path('logout/', views.logout_request, name='logout'),
]