from typing import Type
from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedTextField

# Make email unique
User._meta.get_field('email')._unique = True


# Create your models here.


class Crawler(models.Model):
    name = models.CharField(max_length=64, unique=True)
    source_code = models.TextField()

    def __str__(self) -> str:
        return self.name


class UserController(models.Model):
    CREATED = 0
    ACCEPTED = 1
    REJECTED = 2
    CHOICES = (
        (CREATED, 'Created'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    status = models.IntegerField(choices=CHOICES, default=CREATED)


class UserCrawlerCredentials(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    crawler = models.ForeignKey(Crawler, on_delete=models.CASCADE)
    username = models.TextField(_('Username'))
    password = EncryptedTextField(_('Password'))
    cookies = EncryptedTextField(blank=True, default='')

    class Meta:
        unique_together = ('user', 'crawler')


@receiver(models.signals.post_save, sender=User)
def auto_create_or_save_user_controller(sender: Type[User], instance: User, created: bool, **_) -> None:
    if created:
        UserController.objects.create(user=instance)
    else:
        instance.usercontroller.save()