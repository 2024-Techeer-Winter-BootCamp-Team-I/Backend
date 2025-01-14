from django.shortcuts import render, redirect
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer  # JWT 토큰 생성용
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import TokenAuthentication
from social_django.models import UserSocialAuth  # UserSocialAuth 모델 임포트
import os
import requests
from dotenv import load_dotenv
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import AllowAny
from login.serializers import LoginResponseSerializer

class LoginGithubView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # 깃허브 oauth2 로그인 페이지로 리다이렉트
        github_oauth_url = f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&redirect_uri={os.getenv('GITHUB_REDIRECT_URI')}&scope=repo,read:org,public_repo,write:discussion"
        return redirect(github_oauth_url)


class LoginGithubCallbackView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('code', openapi.IN_QUERY, description="GitHub 로그인 후 받은 코드", type=openapi.TYPE_STRING, required=True)
        ]
    )
    def get(self, request):
        code = request.GET.get('code')
        if not code:
            return Response({"error": "Code 파라미터가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # GitHub 액세스 토큰 요청
        token_url = "https://github.com/login/oauth/access_token"
        payload = {
            'client_id': os.getenv("GITHUB_CLIENT_ID"),
            'client_secret': os.getenv("GITHUB_CLIENT_SECRET"),
            'code': code,
            'redirect_uri': os.getenv("GITHUB_REDIRECT_URI")
        }
        response = requests.post(token_url, data=payload, headers={'Accept': 'application/json'})
        response_data = response.json()

        if 'access_token' not in response_data:
            print(response_data)
            return Response({"error": "깃허브 액세스 토큰을 받는데 실패 하였습니다."}, status=status.HTTP_400_BAD_REQUEST)

        access_token = response_data['access_token']

        # GitHub 사용자 정보 가져오기
        user_info_url = "https://api.github.com/user"
        headers = {'Authorization': f'token {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        if user_info_response.status_code != 200:
            print(user_info_response.json())
            return Response({"error": "사용자 정보를 가져오는 데 실패하였습니다."}, status=status.HTTP_400_BAD_REQUEST)

        user_data = user_info_response.json()

                # 사용자 생성 또는 가져오기
        user, created = self.social_user_get_or_create(
            github_id=user_data["id"],
            github_username=user_data["login"],
            profile_image=user_data["avatar_url"],
            access_token=access_token
        )

        # 메시지 설정
        message = "로그인 성공.(이미 저장된 사용자)"
        if created:
            message = "로그인 성공."

        # JWT 토큰 생성
        jwt_token = TokenObtainPairSerializer.get_token(user)
        refresh_token = str(jwt_token)
        jwt_access_token = str(jwt_token.access_token)

        # Serializer를 사용해 응답 데이터 처리
        response_data = LoginResponseSerializer(
            {
                "message": message,
                "access": jwt_access_token,
                "refresh": refresh_token,
            }
        )

        # 응답 생성
        res = Response(response_data.data, status=status.HTTP_200_OK)

        # 토큰을 쿠키에 저장
        res.set_cookie("access", jwt_access_token, httponly=True)
        res.set_cookie("refresh", refresh_token, httponly=True)

        return res

    @transaction.atomic
    def social_user_get_or_create(self, github_id, github_username, access_token, profile_image=None):
        """
        GitHub ID를 기준으로 User를 가져오거나 새로 생성합니다.
        """
        user = User.objects.filter(github_id=github_id).first()

        if user:
            return user, False

        return self.social_user_create(
            github_id=github_id,
            github_username=github_username,
            profile_image=profile_image,
            access_token=access_token
        ), True

    @transaction.atomic
    def social_user_create(self, github_id, github_username, access_token, profile_image=None):
        """
        새로운 사용자를 생성합니다.
        """
        user = User(
            github_id=github_id,
            github_username=github_username,
            profile_image=profile_image,
            access_token=access_token
        )

        user.full_clean()  # 모델 유효성 검사
        user.save()  # 데이터베이스에 저장
        return user


    @transaction.atomic
    def social_user_get_or_create(self, github_id, github_username, access_token, profile_image=None):
        """
        GitHub ID를 기준으로 User를 가져오거나 새로 생성합니다.
        """
        user = User.objects.filter(github_id=github_id).first()

        if user:
            return user, False

        return self.social_user_create(
            github_id=github_id,
            github_username=github_username,
            profile_image=profile_image,
            access_token=access_token
        ), True

    @transaction.atomic
    def social_user_create(self, github_id, github_username, access_token, profile_image=None):
        """
        새로운 사용자를 생성합니다.
        """
        user = User(
            github_id=github_id,
            github_username=github_username,
            profile_image=profile_image,
            access_token=access_token
        )

        user.full_clean()  # 모델 유효성 검사
        user.save()  # 데이터베이스에 저장
        return user