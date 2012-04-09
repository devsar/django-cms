# -*- coding: utf-8 -*-
from django.conf import settings

def subdomain(request):
    """
        Agrega datos para generar url en los templates
    """
    return {
        'CORE': {
            'DOMAIN':settings.DOMAIN,
            'PORT':settings.PORT,
            #dominio con puerto incluido
            'DOMWPORT':DOMWPORT,
            #mirar en setting para entender que significan
            'SUBDOM_ASSOC': settings.SUBDOM_ASSOC,
            'SUBDOM_ASSOC_INV': settings.SUBDOM_ASSOC_INV,
        }
    }
