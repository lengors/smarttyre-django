import os
import time
import sched
import threading

from django.conf import settings
from django.apps import AppConfig


class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp'
    thread = None

    def ready(self) -> None:

        # Check if not running main
        if os.environ.get('RUN_MAIN') != 'true':

            # Import reporter
            from . import reporter

            # Call the ready() function of the parent class
            super().ready()

            # Prepare scheduler
            scheduler = sched.scheduler(time.time)
            scheduler.enterabs(reporter.next(), 0,
                               reporter.report, (scheduler,))

            # Create a thread to run the scheduler
            self.thread = threading.Thread(
                target=scheduler.run, daemon=True)

            # Start the thread
            self.thread.start()

        elif not settings.DEBUG:

            # Import user
            from django.contrib.auth.models import User

            # Get superuser
            superuser = User.objects.filter(is_superuser=True).first()

            # Verify if superuser exists if not create it and in production mode
            if superuser is None:

                # Throw error
                raise RuntimeError('Superuser not found')
