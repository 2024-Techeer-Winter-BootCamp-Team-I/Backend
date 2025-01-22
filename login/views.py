import os
import requests

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
from dotenv import load_dotenv
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import AllowAny
from login.serializers import LoginResponseSerializer
from login.serializers import UserProfileSerializer
from .models import Project
from document.models import Document
from django.db.models import Q
from django.http import HttpResponseRedirect

class LoginGithubView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="깃허브 소셜로그인 API",  # Swagger UI에서 이 API의 간단한 설명
        responses={
            302: openapi.Response(
                description="GitHub OAuth 로그인 페이지로 리다이렉트",
                headers={
                    'Location': openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='GitHub OAuth 로그인 페이지 URL'
                    )
                }
            )
        }
    )
    def get(self, request):
        # 깃허브 oauth2 로그인 페이지로 리다이렉트
        github_oauth_url = f"https://github.com/login/oauth/authorize?client_id={os.getenv('GITHUB_CLIENT_ID')}&redirect_uri={os.getenv('GITHUB_REDIRECT_URI')}&scope=repo,read:org,public_repo,write:discussion"
        return redirect(github_oauth_url)

class CodeView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="인가코드 확인 테스트 API",  # Swagger UI에서 이 API의 간단한 설명
    )
    def get(self, request):
        # 콜백 URL에서 전달된 인증 코드를 가져옵니다.
        code = request.GET.get('code')
        if not code:
            return Response({"error": "Code 파라미터가 없습니다."}, status=400)

        # 인증 코드를 확인할 수 있도록 반환합니다.
        return Response({"code": code}, status=200)

    

class LoginGithubCallbackView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_summary="소셜로그인 후 콜백 API",
        manual_parameters=[
            openapi.Parameter(
                'code',
                openapi.IN_QUERY,
                description="GitHub 로그인 후 받은 코드",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response('로그인 성공', LoginResponseSerializer),
            400: openapi.Response('잘못된 요청'),
        }
    )
    def get(self, request):
        code = request.GET.get('code')
        print(f"Received code: {code}")
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
        print(payload)
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
        
        # GitHub 이메일 정보 가져오기
        email_url = "https://api.github.com/user/emails"
        email_response = requests.get(email_url, headers=headers)
        if email_response.status_code != 200:
            # 이메일 정보를 가져오지 못한 경우, 임시 이메일 생성
            primary_email = f"{user_data['login']}@example.com"
        else:
            email_data = email_response.json()
            primary_email = next((email['email'] for email in email_data if email['primary']), None)
            if not primary_email:
                primary_email = f"{user_data['login']}@example.com"  # 임시 이메일 생성

        password = 1234
        # 사용자 생성 또는 가져오기
        user, created = self.social_user_get_or_create(
            github_username=user_data["login"],
            email=primary_email,  # GitHub에서 가져온 이메일 또는 임시 이메일 사용
            profile_image=user_data["avatar_url"],
            access_token=access_token
        )
        
        print(f"Authenticated user: {user}")
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

        # # 응답 생성
        # res = Response(response_data.data, status=status.HTTP_200_OK)

        res = HttpResponseRedirect("http://localhost:5173/")
        res["Authorization"] = f"Bearer {jwt_access_token}"

        # 토큰을 쿠키에 저장
        # 클라이언트와 동일한 도메인으로 설정
        # 다른 도메인 간 쿠키 공유 허용
        res.set_cookie("jwt_access",jwt_access_token,httponly=True,samesite="Lax",secure=False)
        res.set_cookie("refresh", refresh_token, httponly=True,samesite="Lax",secure=False)

        return res


    @transaction.atomic
    def social_user_create(self, github_username, email, access_token, profile_image=None):
        """
        새로운 사용자를 생성합니다.
        """
        user = User(
            github_username=github_username,
            email = email,
            profile_image=profile_image,
            access_token=access_token
        )

        user.full_clean()  # 모델 유효성 검사
        user.save()  # 데이터베이스에 저장
        return user


    @transaction.atomic
    def social_user_get_or_create(self, github_username, email, access_token, profile_image=None):
        """
        GitHub ID를 기준으로 User를 가져오거나 새로 생성합니다.
        """
        user = User.objects.filter(github_username=github_username).first()

        if user:
            return user, False

        return self.social_user_create(
            github_username=github_username,
            email=email,
            profile_image=profile_image,
            access_token=access_token
        ), True
        
class MyPageView(APIView):
    permission_classes = [IsAuthenticated]  # 로그인된 사용자만 접근 가능
    
    @swagger_auto_schema(
        operation_summary="마이페이지 조회 API",  # Swagger UI에서 이 API의 간단한 설명
        operation_description="로그인된 사용자의 GitHub 사용자명과 연관된 프로젝트 이름 목록을 반환합니다."  # 상세 설명
    )
    def get(self, request):
        # 현재 로그인된 사용자 정보 가져오기
        user = request.user

        # 사용자와 연관된 프로젝트 이름 가져오기
        projects = Project.objects.filter(user=user)  # Project는 사용자와 FK로 연결되어 있음
        project_names = [project.name for project in projects]

        # 사용자 정보 직렬화
        data = {
            "github_username": user.github_username,  # 사용자의 GitHub 이름
            "project_names": project_names    # 사용자의 프로젝트 이름 목록
        }
        serializer = UserProfileSerializer(data)

        # 응답 반환
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="로그아웃",
        operation_description="로그아웃을 처리합니다. 리프레시 토큰을 전송하여 토큰을 무효화하고 쿠키를 삭제합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='리프레시 토큰'),
            },
            required=['refresh'],
        ),
        responses={
            200: openapi.Response(
                description="로그아웃 성공",
                examples={
                    "application/json": {
                        "message": "로그아웃 성공"
                    }
                }
            ),
            400: openapi.Response(
                description="잘못된 요청",
                examples={
                    "application/json": {
                        "error": "Refresh token is required"
                    }
                }
            ),
        }
    )
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # 토큰 무효화
            else:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            # 쿠키 삭제
            response = Response({
                "message": "로그아웃 성공",
                "logout_url": "https://github.com/logout?returnTo=http://localhost:5173/"  # GitHub 로그아웃 URL, 리다이렉트 url
            }, status=status.HTTP_200_OK)
            response.delete_cookie("jwt_access")
            response.delete_cookie("refresh")
            return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ProjectIDView(APIView):
    permission_classes = [IsAuthenticated]  # 로그인된 사용자만 접근 가능
    
    @swagger_auto_schema(
        operation_summary="프로젝트 상세 조회 API",
        operation_description="로그인된 사용자가 소유한 프로젝트의 이름과 관련된 저장된 문서를 조회합니다.",
        responses={
            200: openapi.Response(
                description="프로젝트 조회 성공",
                examples={
                    "application/json": {
                        "project_id": 1,
                        "project_name": "Sample Project",
                        "documents": [
                            {
                                "title": "Sample Document 1",
                                "erd_code": "example_erd_code",
                                "diagram_code": "example_diagram_code"
                            }
                        ]
                    }
                }
            ),
            404: openapi.Response(
                description="프로젝트를 찾을 수 없음",
                examples={
                    "application/json": {
                        "error": "프로젝트를 찾을 수 없습니다."
                    }
                }
            ),
            400: openapi.Response(
                description="잘못된 요청",
                examples={
                    "application/json": {
                        "error": "저장된 문서를 찾을 수 없습니다."
                    }
                }
            ),
        }
    )
    def get(self, request, project_id):  # project_id를 경로 파라미터로 받음
        try:
            # 프로젝트 ID로 프로젝트 객체 가져오기
            project = Project.objects.get(id=project_id)
            # 프로젝트에서 사용자 ID 가져오기
            user_id = project.user.id
            project_name = project.name

            # 사용자 ID와 프로젝트 이름으로 문서 필터링 (하나라도 저장된 상태만 필터링)
            matching_documents = Document.objects.filter(
                user_id=user_id,
                title=project_name
            ).filter(
                Q(is_diagram_saved=True) | Q(is_erd_saved=True) | Q(is_api_saved=True)  # 하나라도 저장된 상태
            ).values('title', 'erd_code', 'diagram_code')

            if not matching_documents:
                return Response(
                    {"error": "저장된 문서가 없습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "documents": list(matching_documents)
                },
                status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"error": "프로젝트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

    @swagger_auto_schema(
        operation_summary="프로젝트 삭제 API",
        operation_description="로그인된 사용자가 소유한 프로젝트를 삭제합니다. 해당 프로젝트와 관련된 모든 문서도 삭제됩니다.",
        responses={
            200: openapi.Response(
                description="프로젝트 삭제 성공",
                examples={
                    "application/json": {
                        "message": "프로젝트 삭제 성공"
                    }
                }
            ),
            404: openapi.Response(
                description="프로젝트를 찾을 수 없음",
                examples={
                    "application/json": {
                        "error": "프로젝트를 찾을 수 없습니다."
                    }
                }
            ),
            400: openapi.Response(
                description="잘못된 요청",
                examples={
                    "application/json": {
                        "error": "해당 사용자가 아닌 다른 사용자의 프로젝트는 삭제할 수 없습니다."
                    }
                }
            ),
        }
    )
    def delete(self, request, project_id):
        try:
            # 프로젝트 객체 가져오기
            project = Project.objects.get(id=project_id)

            # 프로젝트가 로그인된 사용자의 것인지 확인
            if project.user != request.user:
                return Response(
                    {"error": "해당 사용자가 아닌 다른 사용자의 프로젝트는 삭제할 수 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 프로젝트와 관련된 모든 문서 삭제
            Document.objects.filter(user_id=request.user, title=project.name).delete()

            # 프로젝트 삭제
            project.delete()

            return Response(
                {"message": "프로젝트 삭제 성공"},
                status=status.HTTP_200_OK
            )
        except Project.DoesNotExist:
            return Response(
                {"error": "프로젝트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )