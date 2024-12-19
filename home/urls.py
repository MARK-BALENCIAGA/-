from django.urls import path

from . import views
from .views import generate_password
from .views import search_password



urlpatterns = [
    # данные аккаунта пользователя
    path('', views.user_login_view, name='index'),
    path('register/', views.register_page, name='register-page'),
    path('home/', views.home_page, name='home'),
    path('logout/', views.logout_view, name="logout"),

    #  управление паролями
    path('add-password/', views.add_new_password, name="add-password"),
    path('manage-passwords/', views.manage_passwords, name="manage-passwords"),
    path('edit-password/<str:pk>/', views.edit_password, name="edit-password"),
    path('search/', views.search, name='search'),

    # функция генерации пароля
    path('generate-password/', generate_password, name='generate-password'),

    # функция получения данных о пароле по его id в БД
    path('search_password/', search_password, name='search_password'),

]
