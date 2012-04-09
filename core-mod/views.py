# -*- coding: utf-8 -*-
from django.utils import translation

__author__ = 'andres'

from django.http import HttpResponse
from django.utils.translation import ugettext as _

def test(request):
    t = """
    key: %(key)s
    lang: %(lang)s
    """ % {
        'key': _("PRUEBA"),
        'lang': translation.get_language()
    }

    return HttpResponse(t)


