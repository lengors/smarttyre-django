import os
import csv

from typing import Union
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.contrib.sessions.models import Session
from django.template.loader import render_to_string
from django.forms import ValidationError, model_to_dict
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect, HttpResponseRedirect

from webapp.validators import validate_crawler_file


from .tokens import account_activation_token
from .models import Crawler, UserController, UserCrawlerCredentials
from .forms import ImportUserCrawlerCredentialsForm, UserCrawlerCredentialsForm, UserRegisterForm, UserRequestForm, UserUpdateForm

# Create your views here.


@login_required
def accounts(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Create list of crawler accounts
    accounts = request.user.usercrawlercredentials_set.all()

    # Get pks of all crawler accounts
    pks = [account.crawler.pk for account in accounts]

    # Convert models to forms
    accounts = {account.pk: UserCrawlerCredentialsForm({'confirm_password': account.password, **model_to_dict(
        account, fields=(UserCrawlerCredentialsForm.Meta.fields))}, instance=account) for account in accounts}

    # Reset form for each account
    for account in accounts.values():
        account.changed_data = list()

    # Get remaining crawler accounts
    available_crawlers = Crawler.objects.exclude(pk__in=pks)
    crawlers = Crawler.objects.filter(pk__in=pks)

    # Create add form
    form = UserCrawlerCredentialsForm()

    # Create file form
    file_form = ImportUserCrawlerCredentialsForm()

    # Check request method
    if request.method == 'POST':

        # Get method
        method = request.POST.get('_method').upper()

        # Check method
        if method == 'POST':

            # Create a form instance and populate it with data from the request
            form = UserCrawlerCredentialsForm(
                {'user': request.user, **request.POST.dict()})

            # Check if the form is valid
            if form.is_valid():

                # Save form
                form.save()

                # Return a message that the form was saved
                messages.success(request, _(
                    'New account was successfully added.'))

                # Redirect to the accounts page
                return redirect('accounts')

        # Otherwise
        elif method == 'PUT':

            # Get instance of account
            user_crawler_credentials = UserCrawlerCredentials.objects.filter(
                pk=request.POST.get('instance')).first()

            # Check if the instance exists
            if user_crawler_credentials is None:

                # Return a message that the instance does not exist
                messages.error(request, _('The account does not exist!'))

            # Create a form instance and populate it with data from the request
            account_form = UserCrawlerCredentialsForm(
                {**model_to_dict(user_crawler_credentials), **request.POST.dict()}, instance=user_crawler_credentials)

            # Override accounts
            accounts[user_crawler_credentials.pk] = account_form

            # Check if the form is valid
            if account_form.is_valid():

                # Save form
                account_form.save()

                # Return a message that the form was saved
                messages.success(request, _(
                    f'{str(user_crawler_credentials.crawler).capitalize()} account was successfully edited.'))

                # Redirect to the accounts page
                return redirect('accounts')

        # Otherwise
        elif method == 'DELETE':

            # Check if the instance doesn't exists
            if 'instance' not in request.POST:

                # Delete all accounts
                request.user.usercrawlercredentials_set.all().delete()

                # Return a message that all accounts were deleted
                messages.success(request, _(
                    'All accounts were successfully deleted.'))

            # Otherwise
            else:

                # Get instance of account
                user_crawler_credentials = UserCrawlerCredentials.objects.filter(
                    pk=request.POST.get('instance')).first()

                # Check if the instance exists
                if user_crawler_credentials is None:

                    # Return a message that the instance does not exist
                    messages.error(request, _('The account does not exist!'))

                # Otherwise
                else:

                    # Delete account
                    user_crawler_credentials.delete()

                    # Return a message that the account was deleted
                    messages.success(request, _(
                        f'{str(user_crawler_credentials.crawler).capitalize()} account was successfully deleted.'))

            # Redirect to the accounts page
            return redirect('accounts')

        # Otherwise
        elif method == 'FETCH':

            # Create a form instance and populate it with data from the request
            file_form = ImportUserCrawlerCredentialsForm(
                request.POST, request.FILES)

            # Check if the form is valid
            if file_form.is_valid():

                # Get lines
                lines = request.FILES['file'].readlines()

                # Decode lines
                lines = (line.decode() for line in lines)

                # Get available crawlers as dictionary
                all_crawlers = {str(crawler).lower(
                ): crawler for crawler in list(available_crawlers) + list(crawlers)}

                # Read file as CSV
                for entry in csv.DictReader(lines, fieldnames=('website', 'username', 'password')):

                    # Get data
                    website = entry['website']
                    username = entry['username']
                    password = entry['password']

                    # Check if entry is the header
                    if website != 'website' and username != 'username' and password != 'password':

                        # Get crawler
                        crawler = all_crawlers.get(website.lower())

                        # Check if crawler exists
                        if crawler is not None:

                            # Find instance if it exists
                            user_crawler_credentials = UserCrawlerCredentials.objects.filter(
                                user=request.user, crawler=crawler).first()

                            # Create a form instance and populate it with data from the request
                            form = UserCrawlerCredentialsForm({
                                'user': request.user,
                                'crawler': crawler,
                                'username': entry['username'],
                                'password': entry['password'],
                                'confirm_password': entry['password'],
                            }, instance=user_crawler_credentials)

                            # Validate form
                            if form.is_valid():

                                # Save form
                                form.save()

                # Return a message that the form was saved
                messages.success(request, _(
                    'Accounts were successfully imported.'))

                # Redirect to the accounts page
                return redirect('accounts')

    # Render the accounts page
    return render(request, 'accounts.html', {
        'accounts': accounts.values(),
        'available_crawlers': available_crawlers,
        'crawlers': crawlers,
        'file_form': file_form,
        'form': form,
    })


def activate(request: HttpRequest, uidb64: str, token: str) -> Union[HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Check if the user is already logged in
    if request.user.is_authenticated:

        # Return a message that the user is already logged in
        messages.error(request, _(
            f'You are already logged in!'))

        # Redirect to the home page
        return redirect('home')

    # Try to decode the uidb64 and get the user
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check if the user exists and the token is valid
    if user is None or not account_activation_token.check_token(user, token):

        # Return a message that the user could not be activated
        messages.error(request, _(
            f'The activation link is invalid! Please try again!'))

    # Otherwise
    elif user.usercontroller.status == UserController.REJECTED:

        # Return a message that the user has been rejected
        messages.error(request, _(
            f'Your account request has been rejected!'))

    # Otherwise
    elif user.usercontroller.status == UserController.CREATED:

        # Return a message that the user has not been accepted yet
        messages.error(request, _(
            f'Your account request has not been accepted yet!'))

    # Otherwise
    elif user.is_active:

        # Return a message that the user has been activated
        messages.warning(request, _(
            f'Your account has already been activated!'))

    # Otherwise
    else:

        # Return a message that the user has been activated
        messages.success(request, _(
            f'Your email address confirmation was a success! You can now login into your account!'))

        # Activate the user
        user.is_active = True
        user.save()

    # Redirect to the login page
    return redirect('login')


@login_required
def change(request: HttpRequest) -> Union[HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Return change successful message
    messages.success(request, _('Your password was successfully changed!'))

    # Return home
    return redirect('home')


@login_required
def home(request: HttpRequest) -> HttpResponse:

    # Render the home page
    return render(request, 'home.html')


@login_required
def management(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect]:
    # Check if the user is the superuser
    if not request.user.is_superuser:

        # Return a message that the user is not authorized
        messages.error(request, _(
            'You are not authorized to perform this action!'))

        # Redirect to the home page
        return redirect('home')

    # Check method
    if request.method == 'POST':

        # Get method
        method = request.POST.get('_method').upper()

        # Check if the method is DELETE
        if method == 'DELETE':

            # Check if the instance doesn't exists
            if 'instance' not in request.POST:

                # Delete all crawlers
                Crawler.objects.all().delete()

                # Return a message that all crawlers were deleted
                messages.success(request, _(
                    'All crawlers were successfully deleted.'))

            # Otherwise
            else:

                # Get instance of crawler
                crawler = Crawler.objects.filter(
                    pk=request.POST.get('instance')).first()

                # Check if the instance exists
                if crawler is None:

                    # Return a message that the instance does not exist
                    messages.error(request, _(
                        'The crawler does not exist!'))

                # Otherwise
                else:

                    # Delete crawler
                    crawler.delete()

                    # Return a message that the crawler was deleted
                    messages.success(request, _(
                        f'{str(crawler).capitalize()} crawler was successfully deleted.'))

            # Redirect to the management page
            return redirect('management')

        # Otherwise
        else:

            # Get files
            files = request.FILES.getlist('files')

            # Check if any files threw an error
            valids = list()

            # For each file
            for file in files:

                # Get file name
                name = os.path.split(file.name)[1]
                name = os.path.splitext(name)[0]

                # Get crawler if it exists
                instance = Crawler.objects.filter(name=name).first()

                # Read file
                data = file.read()
                data = data.decode()

                # Validate file content
                try:

                    # Validate file content
                    validate_crawler_file(data)

                    # Create crawler if it does not exist
                    if instance is None:
                        instance = Crawler.objects.create(name=name)

                    # Set crawler source
                    instance.source_code = data

                    # Save crawler
                    instance.save()

                except ValidationError as e:
                    # Return a message that the form is invalid
                    messages.error(request, _(
                        f'Error while uploading {file.name}: {e.message}'))

            # Check if the files are valid
            if len(valids) == len(files):

                # Return a message that the files were uploaded successfully
                messages.success(request, _(
                    'All files were uploaded successfully!'))

            # Otherwise
            elif len(valids) > 0:

                # Create message of which files were uploaded successfully
                message = ', '.join(f'{file.name}' for file in valids)

                # Return a message of which files were uploaded successfully
                messages.success(request, _(
                    f'Files uploaded successfully: {message}'))

            # Redirect to the management page
            return redirect('management')

    # Render the management page
    return render(request, 'management.html', {
        'crawlers': Crawler.objects.all(),
    })


@login_required
def profile(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Check method
    if request.method == 'POST':

        # Get user email
        email = request.user.email

        # Create user update form
        form = UserUpdateForm(request.POST, instance=request.user)

        # Check if the form is valid
        if form.is_valid():

            # Check if the email is changed
            if form.cleaned_data.get('email') != email and settings.EMAIL_CONFIRMATION_ENABLE:

                # Logout the user it
                for session in Session.objects.all():
                    if str(session.get_decoded().get('_auth_user_id')) == str(request.user.id):
                        session.delete()

                # Deactivate the user
                request.user.is_active = False

                # Save user
                form.save()

                # Send email to the user
                mail_subject = _('SmartTyre account email change.')
                message = render_to_string('mails/inform.html', {
                    'user': request.user,
                })

                # Get user email and send activation email
                email = EmailMessage(mail_subject, message, to=[email])
                email.send()

                # Send email to the user
                current_site = get_current_site(request)
                mail_subject = _('Confirm your SmartTyre account new email.')
                message = render_to_string('mails/change.html', {
                    'user': request.user,
                    'scheme': request.scheme,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(request.user.pk)),
                    'token': account_activation_token.make_token(request.user),
                })

                # Get user email and send activation email
                email = EmailMessage(mail_subject, message,
                                     to=[request.user.email])
                email.send()

                # Display a message that the email has been changed
                messages.success(request, _(
                    'Your email address has been changed! Please confirm your new email address. Once you confirm your new email address, you will be able to log in.'))

                # Redirect to login
                return redirect('login')

            # Otherwise save changes
            else:

                # Save form
                form.save()

                # Display a message that the user has been updated
                messages.success(request, _('Your profile has been updated!'))

                # Redirect to the profile page
                return redirect('profile')

    # Otherwise
    else:

        # Create user update form
        form = UserUpdateForm(instance=request.user)

    # Render the profile page
    return render(request, 'profile.html', {
        'form': form,
    })


@login_required
def profile_delete(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Check method
    if request.method == 'POST':

        # Delete user
        request.user.delete()

    # Redirect to login
    return redirect('login')


def register(request: HttpRequest) -> Union[HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Check if the user is already logged in
    if request.user.is_authenticated:

        # Return a message that the user is already logged in
        messages.error(request, _(
            f'You are already logged in!'))

        # Redirect to the home page
        return redirect('home')

    # Verify if the request is a POST request
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request
        form = UserRegisterForm(request.POST)

        # Check if the form is valid
        if form.is_valid():

            # Get superuser
            superuser = User.objects.filter(is_superuser=True).first()

            # Verify if activation email is enabled
            if settings.EMAIL_CONFIRMATION_ENABLE and superuser is not None:

                # Create a new user object but avoid saving it yet
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                # Generate an activation email
                current_site = get_current_site(request)
                mail_subject = _('New SmartTyre account request')
                message = render_to_string('mails/report.html', {
                    'user': user,
                    'scheme': request.scheme,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })

                # Get user email and send acceptance to superuser
                email = EmailMessage(mail_subject, message,
                                     to=[superuser.email])
                email.send()

                # Return a message that the activation email has been sent
                messages.success(request, _(
                    f'Your account has been created! Wait for our administration to either accept or reject your request. Once that\'s done you will either receive an email with a link to activate your account or an email informing you that your request has been rejected. Please wait!'))

            # Otherwise
            elif settings.EMAIL_CONFIRMATION_ENABLE:

                # Create a new user object but avoid saving it yet
                user = form.save(commit=False)
                user.is_active = False
                user.save()

                # Accept the user
                user.usercontroller.status = UserController.ACCEPTED
                user.save()

                # Send email to the user
                current_site = get_current_site(request)
                mail_subject = _('Activate your SmartTyre account.')
                message = render_to_string('mails/accept.html', {
                    'user': user,
                    'scheme': request.scheme,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })

                # Get user email and send activation email
                email = EmailMessage(
                    mail_subject, message, to=[user.email])
                email.send()

                # Display message
                messages.success(request, _(
                    'Your account has been created! Please confirm your email address to complete the registration.'))

            # Otherwise, save the user
            else:

                # Simply create the user
                user = form.save()

                # Return a message that the user has been created
                messages.success(request, _(
                    f'Your account has been created! You can now login into your account!'))

            # Redirect to the login page
            return redirect('login')

    # Otherwise
    else:

        # Create a new form instance
        form = UserRegisterForm()

    # Render the registration page
    return render(request, 'register.html', {
        'form': form,
    })


@login_required
def request(request: HttpRequest, uidb64: str, token: str) -> Union[HttpResponseRedirect, HttpResponsePermanentRedirect]:

    # Check if the user is the superuser
    if not request.user.is_superuser:

        # Return a message that the user is not authorized
        messages.error(request, _(
            'You are not authorized to perform this action!'))

        # Redirect to the home page
        return redirect('home')

    # Try to decode the uidb64 and get the user
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Check if the user exists and the token is valid
    if user is None or not account_activation_token.check_token(user, token):

        # Return a message that the user request could not be processedyy
        messages.error(request, _(
            'The account request link is invalid! Please try again!'))

        # Redirect to the home page
        return redirect('home')

    # Otherwise
    elif user.usercontroller.status != UserController.CREATED:

        # Return a message that the user could not be activated
        messages.error(request, _(
            'The account has already been accepted or rejected!'))

        # Redirect to the home page
        return redirect('home')

    # Check method
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request
        form = UserRequestForm(request.POST, instance=user)

        # Check if the form is valid
        if form.is_valid():

            # Check action
            if form.cleaned_data.get('action') == 'accept':

                # Get user controller
                user.usercontroller.status = UserController.ACCEPTED

                # Set user status to active if email is disabled
                if settings.EMAIL_CONFIRMATION_ENABLE:

                    # Send email to the user
                    current_site = get_current_site(request)
                    mail_subject = _('Activate your SmartTyre account.')
                    message = render_to_string('mails/accept.html', {
                        'user': user,
                        'scheme': request.scheme,
                        'domain': current_site.domain,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'token': account_activation_token.make_token(user),
                    })

                    # Get user email and send activation email
                    email = EmailMessage(
                        mail_subject, message, to=[user.email])
                    email.send()

                    # Display message
                    messages.success(request, _(
                        'The account request has been accepted!'))

                # Otherwise
                else:

                    # Set user status to active
                    user.is_active = True

                    # Return a message that the user has been created
                    messages.success(request, _(
                        'The account has been created!'))

                # Save user
                user.save()

            # Otherwise
            elif settings.EMAIL_CONFIRMATION_ENABLE:
                # Send email to the user
                mail_subject = _('SmartTyre account request rejected.')
                message = render_to_string('mails/reject.html', {
                    'user': user,
                })

                # Get user email and send activation email
                email = EmailMessage(mail_subject, message, to=[user.email])
                email.send()

                # Change user status to rejected
                user.usercontroller.status = UserController.REJECTED
                user.save()

                # Delete the user
                user.delete()

                # Display message
                messages.success(request, _(
                    'The account request has been rejected!'))

            # Redirect to the home page
            return redirect('home')

    # Otherwise
    else:

        # Create a new form instance
        form = UserRequestForm(instance=user)

    # Render the account request page
    return render(request, 'request.html', {
        'form': form,
    })
