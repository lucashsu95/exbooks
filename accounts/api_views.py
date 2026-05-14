from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import UserProfile
from accounts.serializers import UserProfileSerializer

class UserProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update the current authenticated user's profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def get_query_set(self):
        return UserProfile.objects.filter(user=self.request.user)
