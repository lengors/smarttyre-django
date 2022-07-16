from django import forms
from typing import Any, Dict, Union
from captcha.fields import ReCaptchaField
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import UserCrawlerCredentials
from .validators import validate_import_file


class ImportUserCrawlerCredentialsForm(forms.Form):
    file = forms.FileField(validators=[validate_import_file])


class UserCrawlerCredentialsForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label=_('Confirm password'))

    class Meta:
        model = UserCrawlerCredentials
        fields = ('user', 'crawler', 'username', 'password')
        widgets = {
            'username': forms.TextInput(),
            'password': forms.PasswordInput(),
        }

    def clean(self) -> Union[Dict[str, Any], None]:

        # Get the cleaned data from the form.
        cleaned_data = super(UserCrawlerCredentialsForm, self).clean()

        # Get the two password entries.
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Check that the two password entries match.
        # If they don't match, raise an error.
        if password != confirm_password:
            raise forms.ValidationError(_('Passwords don\'t match.'))

        # Return the cleaned data.
        return cleaned_data


class UserRegisterForm(UserCreationForm):
    captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username',
                  'email', 'password1', 'password2')


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')


class UserRequestForm(forms.ModelForm):
    action = forms.ChoiceField(
        choices=(('accept', 'Accept'), ('reject', 'Reject')))

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        for field in UserRequestForm.Meta.fields:
            self.fields[field].disabled = True

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email')

        widgets = {
            'first_name': forms.TextInput(),
            'last_name': forms.TextInput(),
            'username': forms.TextInput(),
            'email': forms.EmailInput(),
        }
