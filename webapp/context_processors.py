import os

from typing import Any, Mapping
from django.conf import settings
from django.http import HttpRequest
from django.utils.translation import get_language


def language(_: HttpRequest) -> Mapping[str, Any]:

    # Get angular path
    angular_path = os.path.join(settings.STATIC_ROOT, 'angular')

    # Get language
    language = get_language()

    # Angular language
    angular_language = None

    # List all folders in angular path
    for folder in os.listdir(angular_path):

        # Get folder path
        folder_path = os.path.join(angular_path, folder)

        # Check if folder is a directory
        if os.path.isdir(folder_path):

            # Get lower language and lower folder
            llanguage = language.lower()
            lfolder = folder.lower()

            # Verify if language matches folder
            if llanguage.startswith(lfolder) or lfolder.startswith(llanguage):

                # Check if folder is larger than the current language
                if angular_language is None or len(folder) > len(angular_language):

                    # Set angular language
                    angular_language = folder

    # Check if angular language is set
    if angular_language is None:
        angular_language = 'en'

    # Return language
    return {
        'ANGULAR_LANGUAGE': angular_language,
    }
