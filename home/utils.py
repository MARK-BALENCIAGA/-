from django.contrib.auth.base_user import BaseUserManager

# функция генерации рандомного пароля
def generate_random_password():
    print("here")
    return BaseUserManager().make_random_password()
