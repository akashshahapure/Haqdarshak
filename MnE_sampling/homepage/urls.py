from django.urls import path

from . import views

urlpatterns = [
    #path("", views.index, name="index"),
    path("", views.sampling_data, name='upload')
]