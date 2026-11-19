from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from usuario.models import Perfil

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Perfil)
