# -*- coding: utf-8 -*-
__author__ = 'andres'

from django import template
from django.conf import settings


register = template.Library()


@register.filter
def preview_link_with_domain(path, language):
    subdomain=settings.SUBDOM_ASSOC_INV.get(language,settings.CMS_LANG_DEFAULT)
    return subdomain+'.'+settings.DOMAIN+path
