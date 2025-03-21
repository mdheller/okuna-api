from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openbook_moderation.permissions import IsNotSuspended
from openbook_common.utils.helpers import normalize_list_value_in_request_data
from openbook_posts.permissions import IsGetOrIsAuthenticated
from openbook_posts.views.posts.serializers import AuthenticatedUserPostSerializer, \
    GetPostsSerializer, UnauthenticatedUserPostSerializer, CreatePostSerializer, GetTopPostsSerializer, \
    AuthenticatedUserTopPostSerializer, GetTrendingPostsSerializer, AuthenticatedUserTrendingPostSerializer


class Posts(APIView):
    permission_classes = (IsGetOrIsAuthenticated, IsNotSuspended)

    def put(self, request):

        request_data = request.data.dict()

        normalize_list_value_in_request_data('circle_id', request_data)

        serializer = CreatePostSerializer(data=request_data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        text = data.get('text')
        image = data.get('image')
        video = data.get('video')
        circles_ids = data.get('circle_id')
        is_draft = data.get('is_draft')
        user = request.user

        with transaction.atomic():
            if circles_ids:
                post = user.create_encircled_post(text=text, circles_ids=circles_ids, image=image, video=video, is_draft=is_draft)
            else:
                post = user.create_public_post(text=text, image=image, video=video, is_draft=is_draft)

        post_serializer = AuthenticatedUserPostSerializer(post, context={"request": request})

        return Response(post_serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        if request.user.is_authenticated:
            return self.get_posts_for_authenticated_user(request)
        return self.get_posts_for_unauthenticated_user(request)

    def get_posts_for_authenticated_user(self, request):
        query_params = request.query_params.dict()
        normalize_list_value_in_request_data('circle_id', query_params)
        normalize_list_value_in_request_data('list_id', query_params)

        serializer = GetPostsSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        circles_ids = data.get('circle_id')
        lists_ids = data.get('list_id')
        max_id = data.get('max_id')
        min_id = data.get('min_id')
        count = data.get('count', 10)
        username = data.get('username')

        user = request.user

        if username:
            if username == user.username:
                posts = user.get_posts(max_id=max_id)
            else:
                posts = user.get_posts_for_user_with_username(username, max_id=max_id, min_id=min_id)
        else:
            posts = user.get_timeline_posts(
                circles_ids=circles_ids,
                lists_ids=lists_ids,
                max_id=max_id,
                min_id=min_id,
                count=count
            )

        posts = posts.order_by('-id')[:count]

        post_serializer_data = AuthenticatedUserPostSerializer(posts, many=True, context={"request": request}).data

        return Response(post_serializer_data, status=status.HTTP_200_OK)

    def get_posts_for_unauthenticated_user(self, request):
        query_params = request.query_params.dict()

        serializer = GetPostsSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        max_id = data.get('max_id')
        count = data.get('count', 10)
        username = data.get('username')

        User = get_user_model()

        posts = User.get_unauthenticated_public_posts_for_user_with_username(
            max_id=max_id,
            username=username
        ).order_by('-created')[:count]

        post_serializer = UnauthenticatedUserPostSerializer(posts, many=True, context={"request": request})

        return Response(post_serializer.data, status=status.HTTP_200_OK)


class TrendingPosts(APIView):
    permission_classes = (IsAuthenticated, IsNotSuspended)

    def get(self, request):
        user = request.user

        posts = user.get_trending_posts_old()[:30]
        posts_serializer = AuthenticatedUserPostSerializer(posts, many=True, context={"request": request})
        return Response(posts_serializer.data, status=status.HTTP_200_OK)


class TrendingPostsNew(APIView):
    permission_classes = (IsAuthenticated, IsNotSuspended)

    def get(self, request):
        query_params = request.query_params.dict()

        serializer = GetTrendingPostsSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        max_id = data.get('max_id')
        min_id = data.get('min_id')
        count = data.get('count', 30)
        user = request.user

        trending_posts = user.get_trending_posts(max_id=max_id, min_id=min_id).order_by('-id')[:count]
        posts_serializer = AuthenticatedUserTrendingPostSerializer(trending_posts, many=True, context={"request": request})
        return Response(posts_serializer.data, status=status.HTTP_200_OK)


class TopPosts(APIView):
    permission_classes = (IsAuthenticated, IsNotSuspended)

    def get(self, request):
        query_params = request.query_params.dict()

        serializer = GetTopPostsSerializer(data=query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        max_id = data.get('max_id')
        min_id = data.get('min_id')
        count = data.get('count', 20)
        exclude_joined_communities = data.get('exclude_joined_communities', False)

        user = request.user

        top_posts = user.get_top_posts(max_id=max_id, min_id=min_id,
                                       exclude_joined_communities=exclude_joined_communities).order_by('-id')[:count]
        posts_serializer = AuthenticatedUserTopPostSerializer(top_posts, many=True, context={"request": request})
        return Response(posts_serializer.data, status=status.HTTP_200_OK)
