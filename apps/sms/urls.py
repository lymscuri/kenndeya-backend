from django.urls import path
from . import views

urlpatterns = [
    path('reminders/', views.reminder_list_create, name='reminder_list_create'),
    path('reminders/<uuid:reminder_id>/', views.reminder_detail, name='reminder_detail'),
    path('send/', views.send_immediate_sms, name='send_immediate_sms'),
]
