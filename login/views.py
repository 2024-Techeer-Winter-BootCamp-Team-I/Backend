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
            openapi.Parameter('code', openapi.IN_QUERY, description="GitHub 로그인 후 받은 코드", type=openapi.TYPE_STRING)
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
            print(response_data)  # GitHub 응답 로그
            return Response({"error": "깃허브 액세스 토큰을 받는데 실패 하였습니다."}, status=status.HTTP_400_BAD_REQUEST)

        access_token = response_data['access_token']

        # 사용자의 GitHub 사용자명 정보 가져오기
        user_info_url = "https://api.github.com/user"
        headers = {'Authorization': f'token {access_token}'}
        user_info_response = requests.get(user_info_url, headers=headers)
        if user_info_response.status_code != 200:
            print(user_info_response.json())  # 사용자 정보 요청 로그
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
        if created:
            message = "회원가입에 성공하였습니다."
        else:
            message = "로그인에 성공하였습니다."

        return Response({"message": message}, status=status.HTTP_200_OK)

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


    
# View 함수
def login(request):
    return render(request, 'login/index.html')

class SaveTokenView(APIView):
    authentication_classes = [TokenAuthentication]  # 인증 방법 설정
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    @swagger_auto_schema(
        operation_summary="소셜 로그인 후 토큰 저장",
        operation_description="소셜 로그인 후 사용자 정보 저장 및 JWT 토큰 생성",
        responses={
            200: openapi.Response(
                description="토큰 저장 성공",
                examples={
                    "application/json": {
                        "message": "사용자 정보가 성공적으로 저장되었습니다.",
                        "access_token": "access_token_string",
                        "refresh_token": "refresh_token_string"
                    }
                }
            ),
            500: openapi.Response(
                description="서버 오류",
                examples={
                    "application/json": {
                        "message": "오류 발생: 오류 메시지"
                    }
                }
            ),
        },
    )
    def get(self, request):
        social_user = request.user  # 소셜 로그인 사용자 정보
        try:
            # user_id 기준으로 사용자 정보 가져오기 또는 생성
            user, created = User.objects.get_or_create(
                user_id=social_user.user_id,
                defaults={
                    "name": social_user.name,
                    "email": social_user.email,
                }
            )

            # 사용자 데이터베이스 저장 여부 메시지
            if created:
                message = "사용자 정보가 성공적으로 저장되었습니다."
            else:
                message = "이미 저장된 사용자입니다."

            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # 토큰을 쿠키에 저장 (HttpOnly 옵션 활성화)
            response = JsonResponse({
                "message": message,
                "access_token": access_token,
                "refresh_token": refresh_token,
            })

            # 토큰을 쿠키에 저장
            response.set_cookie("access", access_token, httponly=True)
            response.set_cookie("refresh", refresh_token, httponly=True)

            return render(request,'login/home.html')
        except Exception as e:
            return JsonResponse({"message": f"오류 발생: {str(e)}"}, status=500)
        
        
def home(request):
    return render(request, 'login/home.html')

from django.shortcuts import render
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from .models import User  # User 모델 import

def token(request):
    if request.method == "POST":
        try:
            # 폼에서 GitHub 소셜 로그인 정보 가져오기
            user_id = request.POST.get('github_user_id')
            name = request.POST.get('github_name')
            email = request.POST.get('github_email')

            if not user_id or not name or not email:
                return JsonResponse({"message": "GitHub 소셜 로그인 정보를 찾을 수 없습니다."}, status=400)

            # user_id 기준으로 사용자 정보 가져오기 또는 생성
            user, created = User.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "name": name,
                    "email": email,
                }
            )

            # 사용자 데이터베이스 저장 여부 메시지
            if created:
                message = "사용자 정보가 성공적으로 저장되었습니다."
            else:
                message = "이미 저장된 사용자입니다."

            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # 토큰을 쿠키에 저장 (HttpOnly 옵션 활성화)
            response = render(request, 'login/token.html', {
                "message": message,
                "access_token": access_token,
                "refresh_token": refresh_token,
            })
            response.set_cookie("access", access_token, httponly=True)
            response.set_cookie("refresh", refresh_token, httponly=True)

            return response
        except Exception as e:
            return JsonResponse({"message": f"오류 발생: {str(e)}"}, status=500)
    else:
        # GET 요청 처리 (예: 폼을 보여주는 경우)
        return render(request, 'login/token_form.html')

# SaveInfo APIView
class SaveInfo(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="로그인한 사용자 정보 조회",
        operation_description="GET 요청으로 로그인한 사용자 정보 조회",
        responses={
            200: openapi.Response(
                description="GET 요청 처리 성공",
                examples={
                    "application/json": {
                        "message": "사용자 정보를 저장하려면 POST 요청을 보내세요.",
                        "user_id": "사용자 아이디"
                    }
                }
            )
        },
    )
    def get(self, request):
        """
        로그인 후 GET 요청 처리
        """
        user_id = request.user.username  # 로그인한 사용자의 아이디 가져오기
        return Response(
            {
                "message": "사용자 정보를 저장하려면 POST 요청을 보내세요.",
                "user_id": user_id
            },
            status=200
        )

    @swagger_auto_schema(
        operation_summary="로그인한 사용자 정보 저장",
        operation_description="GitHub 소셜 로그인 후 사용자 정보를 데이터베이스에 저장합니다.",
        responses={
            200: openapi.Response(
                description="성공적으로 저장",
                examples={
                    "application/json": {"message": "사용자 정보가 성공적으로 저장되었습니다."}
                }
            ),
            400: openapi.Response(
                description="잘못된 요청",
                examples={
                    "application/json": {"message": "잘못된 요청입니다."}
                }
            ),
            401: openapi.Response(
                description="인증되지 않은 사용자",
                examples={
                    "application/json": {"message": "인증되지 않은 사용자입니다."}
                }
            ),
        },
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'github_username': openapi.Schema(type=openapi.TYPE_STRING, description='GitHub 사용자 이름')
            },
            required=['github_username']
        )
    )
    def post(self, request):
        if request.user.is_authenticated:  
            # 실제 소셜 로그인: request.user에서 사용자 이름 추출
            github_username = request.user.username

            # Swagger 테스트: request.data에서 사용자 이름 추출 (테스트용)
            if not github_username:
                github_username = request.data.get("github_username")
                if not github_username:
                    return Response({"message": "GitHub 사용자 이름이 필요합니다."}, status=400)

            try:
                # 사용자 정보 저장 또는 조회
                user, created = User.objects.get_or_create(user_id=github_username)
                message = (
                    "사용자 정보가 성공적으로 저장되었습니다." if created else "이미 저장된 사용자입니다."
                )

                # JWT 토큰 생성
                token = TokenObtainPairSerializer.get_token(user)
                refresh_token = str(token)
                access_token = str(token.access_token)

                # 응답 생성
                res = Response(
                    {
                        "message": message,
                        "token": {
                            "access": access_token,
                            "refresh": refresh_token,
                        },
                    },
                    status=200,
                )

                # 토큰을 쿠키에 저장
                res.set_cookie("access", access_token, httponly=True)
                res.set_cookie("refresh", refresh_token, httponly=True)

                return res
            except Exception as e:
                return Response({"message": f"오류 발생: {str(e)}"}, status=500)
        return Response({"message": "인증되지 않은 사용자입니다."}, status=401)