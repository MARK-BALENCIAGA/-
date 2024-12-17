from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_control

from home.encrypt_util import encrypt, decrypt
from home.forms import RegistrationForm, LoginForm, UpdatePasswordForm
from home.models import UserPassword
from home.utils import generate_random_password
from .models import UserPassword  
import psycopg2
import sqlite3
import mysql.connector
from mysql.connector import Error
from psycopg2 import sql
from django.db import connection
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename = "mylog.log"
)
    
def isAdmin(request):
    print("!!!!!!!! request.POST:", request.POST)
    data = request.POST
    isAdmin = False
    # Проверяем наличие поля 'username' и его значение
    if data.get('username') is not None:
        if data['username'] == 'admin':  
            print("ADMIN")
            isAdmin = True

    return isAdmin
# home page
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def home_page(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    return render(request, 'pages/home.html')


# user login
class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = 'pages/index.html'




def user_login_view(request):
    if (request.user.is_authenticated):
        return redirect('/home')
    return UserLoginView.as_view()(request)


# register new user
def register_page(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account registered successfully. Please log in to your account.")
        else:
            print("Registration failed!")
    else:
        form = RegistrationForm()

    context = {'form': form}
    return render(request, 'pages/register.html', context)


# logout
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def logout_view(request):
    if not request.user.is_authenticated:
        return redirect('/')
    logout(request)
    return redirect('/')


# add new password
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def add_new_password(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    if request.method == 'POST':
        try:
            username = request.POST['username']
            password = encrypt(request.POST['password'])
            application_type = request.POST['application_type']
            if application_type == 'Website':
                website_name = request.POST['website_name']
                website_url = request.POST['website_url']
                UserPassword.objects.create(username=username, password=password, application_type=application_type,
                                            website_name=website_name, website_url=website_url, user=request.user)
                messages.success(request, f"New password added for {website_name}")
            elif application_type == 'Desktop application':
                application_name = request.POST['application_name']
                UserPassword.objects.create(username=username, password=password, application_type=application_type,
                                            application_name=application_name, user=request.user)
                messages.success(request, f"New password added for {application_name}.")
            elif application_type == 'Game':
                game_name = request.POST['game_name']
                game_developer = request.POST['game_developer']
                # create user home_userpassword
                UserPassword.objects.create(username=username, password=password, application_type=application_type,
                                            game_name=game_name, game_developer=game_developer, user=request.user)
                messages.success(request, f"New password added for {game_name}.")
            return HttpResponseRedirect("/add-password")
        except Exception as error:
            print("Error: ", error)

    return render(request, 'pages/add-password.html')


# edit password
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def edit_password(request, pk):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    user_password = UserPassword.objects.get(id=pk)
    user_password.password = decrypt(user_password.password)
    form = UpdatePasswordForm(instance=user_password)

    if request.method == 'POST':
        if 'delete' in request.POST:
            # delete password
            user_password.delete()
            return redirect('/manage-passwords')
        form = UpdatePasswordForm(request.POST, instance=user_password)

        if form.is_valid():
            try:
                user_password.password = encrypt(user_password.password)
                form.save()
                messages.success(request, "Password updated.")
                user_password.password = decrypt(user_password.password)
                return HttpResponseRedirect(request.path)
            except ValidationError as e:
                form.add_error(None, e)

    context = {'form': form}
    return render(request, 'pages/edit-password.html', context)

## NEW

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def search(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    
    logged_in_user = request.user
    logged_in_user_pws = UserPassword.objects.filter(user=logged_in_user)
    
    if request.method == "POST":
        searched = request.POST.get("password_search", "")
        passwords = []

        config = {
            'host': '127.0.0.1',         # Укажите адрес хоста
            'port': '5432',
            'database': 'database',    # Укажите имя базы данных
            'user': 'postgres',        # Укажите имя пользователя
            'password': 'password',    # Укажите пароль
        }

        # hostname = '127.0.0.1'  # Например, 'localhost' или IP-адрес
        # port = '5432'      # Обычно 5432 для PostgreSQL
        # database = 'database'  # Имя вашей базы данных
        # username = 'postgres'  # Имя пользователя
        # password = 'password'  # Пароль
        try:
            # Подключение к базе данных
            # connection = psycopg2.connect(
            #     host=hostname,
            #     port=port,
            #     database=database,
            #     user=username,
            #     password=password
            # )
            connection = mysql.connector.connect(**config)
            # Создание курсора для выполнения операций с базой данных
            cursor = connection.cursor()
            # Формируем небезопасный запрос
            query = f"SELECT * FROM home_userpassword WHERE (website_name = '{searched}' OR application_name = '{searched}' OR game_name = '{searched}') and user_id = {logged_in_user.id}"
            print("!!!!! query: ", query)
            cursor.executescript(query)
            results = cursor.fetchall()

            # Преобразуем результат в список словарей
            for row in results:
                password_entry = {
                    'id': row[0],
                    'username': row[1],
                    'password': row[2],
                    'application_type': row[3],
                    'website_name': row[4],
                    'website_url': row[5],
                    'application_name': row[6],
                    'game_name': row[7],
                    'game_developer': row[8],
                    'date_created': row[9],
                    'date_last_updated': row[10],
                    'user_id': row[11],
                }
                passwords.append(password_entry)

        except Exception as error:
            print(f"Ошибка при подключении к PostgreSQL: {error}")
        finally:
            # Закрытие курсора и соединения
            if cursor is not None:
                cursor.close()
            if connection is not None:
                connection.close()
                print("Соединение с PostgreSQL закрыто.")
                print("!!!! passwords ", passwords)


        return render(request, "pages/search.html", {'passwords': passwords})

    return render(request, "pages/search.html", {'passwords': logged_in_user_pws})

### OLD
# # search password 
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# def search(request):
#     if not request.user.is_authenticated:
#         return redirect('%s?next=%s' % ('/', request.path))
#     logged_in_user = request.user
#     logged_in_user_pws = UserPassword.objects.filter(user=logged_in_user)
#     if request.method == "POST":
#         searched = request.POST.get("password_search", "")
#         users_pws = logged_in_user_pws.values()
#         if users_pws.filter(Q(website_name=searched) | Q(application_name=searched) | Q(game_name=searched)):
#             user_pw = UserPassword.objects.filter(
#                 Q(website_name=searched) | Q(application_name=searched) | Q(game_name=searched)).values()
#             print("!!!!!! user_pw", user_pw)
#             return render(request, "pages/search.html", {'passwords': user_pw})
#         else:
#             messages.error(request, "---YOUR SEARCH RESULT DOESN'T EXIST---")


#     return render(request, "pages/search.html", {'pws': logged_in_user_pws})

# all passwords
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def manage_passwords(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    sort_order = 'asc'
    logged_in_user = request.user
    user_passwords = UserPassword.objects.filter(user=logged_in_user)
    if request.GET.get('sort_order'):
        sort_order = request.GET.get('sort_order', 'desc')
        user_passwords = user_passwords.order_by('-date_created' if sort_order == 'desc' else 'date_created')
    if not user_passwords:
        return render(request, 'pages/manage-passwords.html',
                      {'no_password': "No password available. Please add password."})
    return render(request, 'pages/manage-passwords.html', {'all_passwords': user_passwords, 'sort_order': sort_order})


# generate random password
def generate_password(request):
    password = generate_random_password()
    return JsonResponse({'password': password})
