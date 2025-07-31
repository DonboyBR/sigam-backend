# Arquivo: sigam_config/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Esta linha é a mais importante. Ela diz:
    # "Qualquer URL que comece com 'api/' deve ser gerenciada pelo arquivo 'urls.py' da nossa app 'api'."
    path('api/', include('api.urls')),
]