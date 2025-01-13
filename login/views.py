from django.shortcuts import render, redirect
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import User

# View 함수
def login(request):
    return render(request, 'login/index.html')

def home(request):
    return render(request, 'login/home.html')

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
        """
        POST 요청으로 로그인한 사용자 정보를 저장합니다.
        """
        if request.user.is_authenticated:
            github_username = request.data.get("github_username")
            if not github_username:
                return Response({"message": "GitHub 사용자 이름이 필요합니다."}, status=400)

            try:
                user, created = User.objects.get_or_create(user_id=github_username)
                message = (
                    "사용자 정보가 성공적으로 저장되었습니다." if created else "이미 저장된 사용자입니다."
                )
                return Response({"message": message}, status=200)
            except Exception as e:
                return Response({"message": f"오류 발생: {str(e)}"}, status=500)
        return Response({"message": "인증되지 않은 사용자입니다."}, status=401)
