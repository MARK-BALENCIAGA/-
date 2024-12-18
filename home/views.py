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
from psycopg2 import sql
from django.db import connection
import logging
from django.http import HttpResponse



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

def getUsername(request):
    username = ""
    data = request.POST
    if data.get('username') is not None:
        username =  data['username']
    return username 

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


class CustomUserLoginView(UserLoginView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Если аутентификация успешна, устанавливаем cookie
        if request.user.is_authenticated:
            username = request.user.username  # Получаем имя пользователя
            response.set_cookie("username", username)
        
        return response

def user_login_view(request):
    # Проверяем, находится ли пользователь в аутентифицированном состоянии
    if request.user.is_authenticated:
        return redirect('/home')
    
    # Если пользователь не аутентифицирован, обрабатываем запрос через CustomUserLoginView
    return CustomUserLoginView.as_view()(request)


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

# # search password 
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def search(request):
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    logged_in_user = request.user
    logged_in_user_pws = UserPassword.objects.filter(user=logged_in_user)
    if request.method == "POST":
        searched = request.POST.get("password_search", "")
        if searched == "":
            searched = "!@#&" 
        if searched == "*":
            searched = "" 
        users_pws = logged_in_user_pws.values()
        if users_pws.filter(Q(website_name=searched) | Q(application_name=searched) | Q(game_name=searched)):
            user_pw = UserPassword.objects.filter(
                Q(website_name=searched) | Q(application_name=searched) | Q(game_name=searched)).values()
            return render(request, "pages/search.html", {'passwords': user_pw})
        else:
            messages.error(request, "---YOUR SEARCH RESULT DOESN'T EXIST---")

    return render(request, "pages/search.html", {'pws': logged_in_user_pws})





def search_password(request):
    # Получаем password_id из параметров запроса
    password_id = request.GET.get('password_id')

    # Проверяем, что password_id передан и является корректным числом
    if password_id is None or not password_id.isdigit():
        return JsonResponse({'error': 'Invalid password_id provided.'}, status=400)
    print("!!!! password_id", password_id)

    # Пробуем получить объект UserPassword
    user_password_queryset  = UserPassword.objects.filter(id=password_id).values()
    print("!!!! user_password_queryset:", user_password_queryset)
    
     # Проверяем, есть ли результат
    if not user_password_queryset.exists():
        return JsonResponse({'error': 'Password not found.'}, status=404)

    # Извлекаем первый элемент из QuerySet
    user_password = user_password_queryset.first()

    print("!!!! user_password:", user_password)

    # Извлекаем зашифрованный пароль и расшифровываем его
    encrypted_password = user_password['password']
    decrypted_password = decrypt(encrypted_password)

    # Заменяем зашифрованный пароль на расшифрованный в словаре
    user_password['password'] = decrypted_password

    # Возвращаем JSON-ответ
    return JsonResponse(user_password)

# all passwords
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def manage_passwords(request):
   
    # Проверяем, аутентифицирован ли пользователь
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % ('/', request.path))
    
    sort_order = 'asc'
    logged_in_user = request.user

    # Проверяем наличие cookie username и его значение
    if request.COOKIES.get('username') == 'admin':
        user_passwords = UserPassword.objects.all()  # Если admin, берем все пароли
    else:
        user_passwords = UserPassword.objects.filter(user=logged_in_user)  # Фильтруем по пользователю

    # Обработка сортировки
    if request.GET.get('sort_order'):
        sort_order = request.GET.get('sort_order', 'desc')
        user_passwords = user_passwords.order_by('-date_created' if sort_order == 'desc' else 'date_created')

    # Проверка наличия паролей
    if not user_passwords:
        return render(request, 'pages/manage-passwords.html',
                      {'no_password': "No password available. Please add password."})
    
    # Отправляем данные в шаблон
    return render(request, 'pages/manage-passwords.html', {'all_passwords': user_passwords, 'sort_order': sort_order})

# generate random password
def generate_password(request):
    password = generate_random_password()
    return JsonResponse({'password': password})
