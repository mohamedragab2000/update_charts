from django.urls import path
from . import views

urlpatterns = [
    path('analysis/', views.run_analysis, name='run_analysis'),
]