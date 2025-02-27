"""
API endpoint to manipulate contributor ratings
"""

from django.shortcuts import get_object_or_404
from django.db.models import Count, F, Q
from rest_framework import generics, exceptions
from rest_framework.response import Response
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view

from ..models import ContributorRating
from ..serializers import (
    ContributorRatingSerializer,
    ContributorRatingCreateSerializer,
    ContributorRatingUpdateAllSerializer,
)


RatingsWithAnnotations = ContributorRating.objects.annotate(
    n_comparisons=Count(
        "user__comparisons",
        filter=(
            Q(user__comparisons__video_1=F("video"))
            | Q(user__comparisons__video_2=F("video"))
        ),
    )
).order_by("-pk")


@extend_schema_view(
    get=extend_schema(
        description="Retrieve the logged-in user's ratings for a specific video "
        "(computed automatically from the user's comparisons)"
    ),
    put=extend_schema(
        description="Update public / private status of the logged-in user ratings "
        "for a specific video."
    ),
    patch=extend_schema(
        description="Update public / private status of the logged-in user ratings "
        "for a specific video."
    ),
)
class ContributorRatingDetail(generics.RetrieveUpdateAPIView):
    serializer_class = ContributorRatingSerializer

    def get_object(self):
        return get_object_or_404(
            RatingsWithAnnotations,
            video__video_id=self.kwargs["video_id"],
            user=self.request.user,
        )


@extend_schema_view(
    get=extend_schema(
        description="Retrieve the logged in user's ratings per video "
        "(computed automatically from the user's comparisons).",
        parameters=[
            OpenApiParameter("is_public", OpenApiTypes.BOOL, OpenApiParameter.QUERY)
        ],
    ),
    post=extend_schema(
        description="Initialize the rating object for the current user about a "
        "specific video, with optional visibility settings."
    ),
)
class ContributorRatingList(generics.ListCreateAPIView):
    queryset = ContributorRating.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ContributorRatingCreateSerializer
        return ContributorRatingSerializer

    def get_queryset(self):
        ratings = RatingsWithAnnotations.filter(
            user=self.request.user, n_comparisons__gt=0
        )
        is_public = self.request.query_params.get("is_public")
        if is_public:
            if is_public == "true":
                ratings = ratings.filter(is_public=True)
            elif is_public == "false":
                ratings = ratings.filter(is_public=False)
            else:
                raise exceptions.ValidationError(
                    "'is_public' query param must be 'true' or 'false'"
                )
        return ratings


class ContributorRatingUpdateAll(generics.GenericAPIView):
    """
    Mark all contributor ratings by current user as public or private.
    """

    serializer_class = ContributorRatingUpdateAllSerializer

    def get_queryset(self):
        return ContributorRating.objects.filter(user=self.request.user)

    def patch(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset.update(is_public=serializer.validated_data["is_public"])
        return Response(serializer.data)
