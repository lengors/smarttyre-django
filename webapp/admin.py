from django.contrib import admin
from django.contrib.auth.admin import User, Group

# Unregister models.
admin.site.unregister([User, Group])
