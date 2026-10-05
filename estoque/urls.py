from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    path('', views.inicio, name='inicio'),
]
