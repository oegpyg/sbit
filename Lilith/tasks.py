from __future__ import absolute_import
from celery import shared_task

@shared_task(bind=True)
def imprimir_documento(self, *args, **kwargs):
    pass
