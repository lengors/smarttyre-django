from django.urls import path
from django.contrib.auth.views import *

from .views import accounts, change, activate, home, management, profile, profile_delete, register, request

urlpatterns = [
    path('', home, name='home'),
    path('profile/', profile, name='profile'),
    path('accounts/', accounts, name='accounts'),
    path('register/', register, name='register'),
    path('management/', management, name='management'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/delete/', profile_delete, name='profile_delete'),
    path('request/<str:uidb64>/<str:token>/', request, name='request'),
    path('activate/<str:uidb64>/<str:token>', activate, name='activate'),
    path('login/', LoginView.as_view(template_name='login.html',
         redirect_authenticated_user=True), name='login'),
    path('password/reset/', PasswordResetView.as_view(
        template_name='password/reset.html'), name='password_reset'),
    path('password/change/', PasswordChangeView.as_view(
        template_name='password/change.html'), name='password_change'),
    path('password/reset/done/', PasswordResetDoneView.as_view(
        template_name='password/reset/done.html'), name='password_reset_done'),
    path('password/change/done/', change, name='password_change_done'),
    path('password/reset/confirm/<uidb64>/<token>', PasswordResetConfirmView.as_view(
        template_name='password/reset/confirm.html'), name='password_reset_confirm'),
    path('password/reset/complete/', PasswordResetCompleteView.as_view(
        template_name='password/reset/complete.html'), name='password_reset_complete'),
]
