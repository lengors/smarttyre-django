import os
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
            if os.path.isfile(handler.baseFilename) and superuser is not None and settings.EMAIL_CONFIRMATION_ENABLE:

                # Initialize the log content
                content = None

                # Read the log
                with open(handler.baseFilename, 'r') as fin:

                    # Read the log content
                    content = fin.read()

                # Reset the log
                with open(handler.baseFilename, 'w') as fout:
                    fout.flush()

                # Check if the content is not empty
                if content is not None:

                    # Get today's date
                    day = day.strftime("%d-%m-%Y")

                    # Create mail subject
                    mail_subject = _(f'SmartTyre report {day}')

                    # Create mail body
                    mail_body = f'{mail_subject}.'

                    # Create mail
                    mail = EmailMessage(
                        mail_subject, mail_body, to=[superuser.email])

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
