from typing import Any
from django import template

# Create register
register = template.Library()


@register.filter
def quote(value: Any) -> str:
    return str(value).strip()
