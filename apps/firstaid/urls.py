"""
Routes publiques des protocoles de premiers secours (montées sous /api/v1/firstaid/).

GET /protocols/?lang=fr|en          liste des protocoles publiables
GET /protocols/<id>/?lang=fr|en     protocole complet dans une langue
GET /meta/?lang=fr|en               numéro d'urgence, langues, nombre de protocoles
POST /classify/  {text, lang?}      reconnaît un scénario (id de protocole publiable) ou null
POST /answer/    {text, lang?, options}  convertit une réponse libre en clé d'option ou null
POST /clarify/   {text, lang?, turn}     une question de clarification (modèle, garde-fous) ou null
POST /intent/    {text, lang?, protocol_id, phase, question_options}  intention parmi des options fixes
"""

from django.urls import path

from . import views

app_name = 'firstaid'

urlpatterns = [
    path('protocols/', views.protocol_list, name='protocol_list'),
    path('protocols/<slug:protocol_id>/', views.protocol_detail, name='protocol_detail'),
    path('meta/', views.meta, name='meta'),
    path('classify/', views.classify, name='classify'),
    path('answer/', views.answer, name='answer'),
    path('clarify/', views.clarify, name='clarify'),
    path('intent/', views.intent, name='intent'),
]
