import sched
import logging

from typing import Union
from django.conf import settings
from datetime import datetime, timedelta
from django.core.mail import EmailMessage
from django.contrib.auth.models import User
from django.utils.translation import gettext as _


def next(date: Union[datetime, None] = None) -> float:

    # Check if the date is None
    if date is None:
        date = today()

    # Get tomorrow's date
    tomorrow = date + timedelta(days=1)
    return tomorrow.timestamp()


def report(scheduler: sched.scheduler) -> None:

    # Get today's date
    day = today()
    tomorrow = next(day)

    # Schedule the next day
    scheduler.enterabs(tomorrow, 0, report, (scheduler,))

    # Get logger
    logger = logging.getLogger()
    if len(logger.handlers) > 0:

        # Acquire the log handler
        handler = logger.handlers[0]
        handler.acquire()

        try:

            # Flush the log
            handler.flush()

            # Get superuser to send the log
            superuser = User.objects.filter(is_superuser=True).first()

            # Check if the log exists and the superuser exists
            if superuser is not None and settings.EMAIL_CONFIRMATION_ENABLE:

                # Seek initial position to the beginning of the file
                handler.stream.seek(0)

                # Read from stream
                content = handler.stream.read()

                # Reset log
                handler.stream.seek(0)
                handler.stream.truncate()

                # Get today's date
                day = day.strftime("%d-%m-%Y")

                # Create mail subject
                mail_subject = _(f'SmartTyre report {day}')

                # Create mail body
                mail_body = f'{mail_subject}.'

                # Create mail
                mail = EmailMessage(mail_subject, mail_body, to=[superuser.email])

                # Add log file as attachment
                mail.attach(f'report_{day}.log', content, 'text/plain')

                # Send mail
                mail.send()

        finally:

            # Release the log handler
            handler.release()


def today() -> float:

    # Get today's date
    today = datetime.today()
    return today.replace(hour=0, minute=0, second=0, microsecond=0)
