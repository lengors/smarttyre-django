import csv

from django.forms import ValidationError
from django.db.models.fields.files import FieldFile
from django.utils.translation import gettext_lazy as _

from .utils import load_crawler

# Create your validators here.


def validate_crawler_file(content: str) -> FieldFile:

    # Try to load crawlers
    try:
        crawlers = load_crawler(content)
    except Exception as e:
        raise ValidationError(_('The file is not a valid crawler.')) from e

    # Check if there is only one crawler
    if len(crawlers) > 1:
        raise ValidationError(
            _('The file is ambiguous. It contains more than one crawler.'))

    # Check if there is a crawler
    if len(crawlers) == 0:
        raise ValidationError(_('The crawler class is not defined.'))

    # Retrieve the crawler class
    return crawlers[0]


def validate_import_file(value: FieldFile) -> FieldFile:

    # Get lines
    lines = value.readlines()

    # Decode lines
    lines = (line.decode() for line in lines)

    # Create a csv reader
    reader = csv.DictReader(lines, fieldnames=(
        'website', 'username', 'password'))

    # Read file as CSV
    for entry in reader:
        if entry.get('website') is None or entry.get('username') is None or entry.get('password') is None:
            raise ValidationError(_('The file is not a valid CSV file.'))

    # Check if there are any remaining lines
    if reader.restkey is not None or reader.restval is not None:
        raise ValidationError(_('The file is not a valid CSV file.'))

    # Reset file
    value.seek(0)

    # Return the value
    return value
