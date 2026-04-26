from django.urls import path
from .views import ChatSSEView, ConsentView

app_name = "ai"

urlpatterns = [
    path("chat/", ChatSSEView.as_view(), name="chat_sse"),
    path("chat/consent/<str:action>/", ConsentView.as_view(), name="chat_consent"),
    # chat/clear will be implemented later, but can add placeholder if requested
]
