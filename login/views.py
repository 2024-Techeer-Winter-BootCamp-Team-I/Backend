from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.helpers import complete_social_login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import User
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

# 로그인 뷰 (Django 기본 뷰)
def login(request):
    return render(request, 'login/index.html')

# 홈 뷰 (Django 기본 뷰)
def home(request):
    return render(request, 'login/home.html')

def github_callback(request):
    try:
        print("인증 코드:", request.GET.get('code'))
        adapter = GitHubOAuth2Adapter(request)
        client = OAuth2Client(request)
        token = client.get_access_token(request.GET['code'])
        print("액세스 토큰:", token['access_token'])

        social_account = SocialAccount.objects.get(user=request.user, provider='github')
        print("GitHub 소셜 계정:", social_account)

        social_token = SocialToken(account=social_account, token=token['access_token'])
        social_token.save()
        print("토큰 저장 완료:", social_token.token)

        return redirect('home')
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return redirect('error_page')

# SaveInfo APIView (DRF 뷰)
class SaveInfo(APIView):
    permission_classes = [IsAuthenticated]  # IsAuthenticated 사용

    @swagger_auto_schema(
        operation_summary="로그인한 사용자 정보 조회",
        operation_description="GET 요청으로 로그인한 사용자 정보 조회",
        responses={
            200: openapi.Response(
                description="GET 요청 처리 성공",
                examples={
                    "application/json": {
                        "message": "사용자 정보를 저장하려면 POST 요청을 보내세요.",
                        "user_id": "사용자 아이디",
                        "github_access_token": "GitHub 액세스 토큰"
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

        # GitHub 액세스 토큰 가져오기
        try:
            # 1. GitHub 소셜 계정이 연결되었는지 확인
            social_account = request.user.socialaccount_set.get(provider='github')
            
            # 2. 소셜 계정에 토큰이 있는지 확인
            social_token = social_account.socialtoken_set.first()
            if not social_token:
                return Response({"message": "GitHub 액세스 토큰을 찾을 수 없습니다."}, status=401)
            
            # 3. 액세스 토큰 가져오기
            access_token = social_token.token
        except SocialAccount.DoesNotExist:
            return Response({"message": "이 사용자에게 연결된 GitHub 계정이 없습니다."}, status=401)

        return Response(
            {
                "message": "사용자 정보를 저장하려면 POST 요청을 보내세요.",
                "user_id": user_id,
                "github_access_token": access_token  # GitHub 액세스 토큰 반환
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
                    "application/json": {
                        "message": "사용자 정보가 성공적으로 저장되었습니다.",
                        "github_access_token": "GitHub 액세스 토큰"
                    }
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
        """
        POST 요청으로 로그인한 사용자 정보를 저장합니다.
        """
        if request.user.is_authenticated:
            github_username = request.data.get("github_username")
            if not github_username:
                return Response({"message": "GitHub 사용자 이름이 필요합니다."}, status=400)

            try:
                # 1. GitHub 소셜 계정이 연결되었는지 확인
                social_account = request.user.socialaccount_set.get(provider='github')
                
                # 2. 소셜 계정에 토큰이 있는지 확인
                social_token = social_account.socialtoken_set.first()
                if not social_token:
                    return Response({"message": "GitHub 액세스 토큰을 찾을 수 없습니다."}, status=401)
                
                # 3. 액세스 토큰 가져오기
                access_token = social_token.token

                # 4. 사용자 정보 저장
                user, created = User.objects.get_or_create(username=github_username)  # username으로 변경
                message = (
                    "사용자 정보가 성공적으로 저장되었습니다." if created else "이미 저장된 사용자입니다."
                )
                return Response({"message": message, "github_access_token": access_token}, status=200)
            except SocialAccount.DoesNotExist:
                return Response({"message": "이 사용자에게 연결된 GitHub 계정이 없습니다."}, status=401)
            except Exception as e:
                return Response({"message": f"오류 발생: {str(e)}"}, status=500)
        return Response({"message": "인증되지 않은 사용자입니다."}, status=401)

# GitHub 액세스 토큰 조회 뷰 (DRF 뷰)
class GetAccessToken(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GitHub 액세스 토큰을 가져오는 뷰
        """
        try:
            print("인증된 사용자:", request.user)  # 로그 추가
            # 1. GitHub 소셜 계정이 연결되었는지 확인
            social_account = request.user.socialaccount_set.get(provider='github')
            print("GitHub 소셜 계정:", social_account)  # 로그 추가
            
            # 2. 소셜 계정에 토큰이 있는지 확인
            social_token = social_account.socialtoken_set.first()
            if not social_token:
                print("GitHub 액세스 토큰이 없습니다.")  # 로그 추가
                return Response({"message": "GitHub 액세스 토큰을 찾을 수 없습니다."}, status=401)
            
            # 3. 액세스 토큰 가져오기
            access_token = social_token.token
            print("액세스 토큰:", access_token)  # 로그 추가

            # 4. 액세스 토큰 반환
            return Response({
                "message": "GitHub 액세스 토큰이 성공적으로 조회되었습니다.",
                "access_token": access_token
            }, status=200)

        except SocialAccount.DoesNotExist:
            print("GitHub 소셜 계정이 없습니다.")  # 로그 추가
            return Response({"message": "이 사용자에게 연결된 GitHub 계정이 없습니다."}, status=401)
        except Exception as e:
            print(f"오류 발생: {str(e)}")  # 로그 추가
            return Response({"message": f"오류 발생: {str(e)}"}, status=500)

# GitHub 재인증 뷰 (Django 기본 뷰)
def reauthenticate_github(request):
    """
    GitHub 재인증을 처리하는 뷰
    """
    try:
        # 사용자의 GitHub 소셜 계정을 가져옴
        social_account = SocialAccount.objects.get(user=request.user, provider='github')
        # 재인증 프로세스 시작
        return complete_social_login(request, social_account)
    except SocialAccount.DoesNotExist:
        # GitHub 계정이 없는 경우 오류 페이지로 리디렉션
        return redirect('error_page')  # 오류 페이지 URL로 변경

# 오류 페이지 뷰 (Django 기본 뷰)
def error_page(request):
    """
    오류 페이지를 렌더링합니다.
    """
    return render(request, 'board/error.html', {'error': '알 수 없는 오류가 발생했습니다.'})