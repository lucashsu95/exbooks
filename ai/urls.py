from django.urls import path
from .views import ChatSSEView, ConsentView, ClearHistoryView

app_name = "ai"

urlpatterns = [
    path("chat/", ChatSSEView.as_view(), name="chat_sse"),
    path("chat/consent/<str:action>/", ConsentView.as_view(), name="chat_consent"),
    path("chat/clear/", ClearHistoryView.as_view(), name="chat_clear"),
]
