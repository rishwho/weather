from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Home Page
    path('', views.index, name='index'),

    # Authentication URLs
    # By default, these look for templates in a 'registration/' folder
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),

    # Weather Features
    path('add-favorite/<str:city_name>/', views.add_favorite, name='add_favorite'),
    path('clear-history/', views.clear_history, name='clear_history'),
]