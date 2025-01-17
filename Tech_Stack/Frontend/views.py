from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
import os
import shutil
import requests

class FrontendSetupView(APIView):
    @swagger_auto_schema(
        operation_summary='Frontend 세팅 API',
        operation_description="Create a new frontend project with the selected tech stack",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'tech_stack_name': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='선택한 기술스택의 세부 기술스택 리스트'),
            },
            required=['tech_stack_name']
        ),
        responses={
            200: openapi.Response('success', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            400: openapi.Response('Invalid tech stack name'),
            500: openapi.Response('Failed to create project'),
        }
    )
    def post(self, request):
        tech_stack_name = request.data.get('tech_stack_name')

        if not tech_stack_name:
            return Response(
                {"error": "tech_stack_name은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. 선택된 기술 스택에 따라 템플릿 찾기
            matching_template = self.find_matching_template(tech_stack_name)
            if not matching_template:
                return Response(
                    {"error": "매칭되는 템플릿을 찾을 수 없습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. 템플릿 디렉토리 경로 설정 
            template_base_dir = os.path.join("/Backend", "Tech_Stack", "Frontend")
            template_dir = os.path.join(template_base_dir, matching_template)
            print(f"Frontend Template directory: {template_dir}")  # 디버깅용 로그

            if not os.path.exists(template_dir):
                return Response(
                    {"error": f"템플릿 디렉토리를 찾을 수 없습니다: {template_dir}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 3. 임시 디렉터리 생성
            temp_dir = os.path.join(settings.BASE_DIR, "temp", f"my-{'-'.join(tech_stack_name)}-project")
            os.makedirs(temp_dir, exist_ok=True)

            # 4. 템플릿 디렉터리 복사
            shutil.copytree(template_dir, os.path.join(temp_dir, "frontend"))

            # 5. repo 앱의 create_repo 엔드포인트로 데이터 전달
            repo_url = f"http://{settings.BACKEND_DOMAIN}/api/repo/create/"
            response = requests.post(
                repo_url,
                json={
                    "repo_name": f"my-{'-'.join(tech_stack_name)}-project",
                    "frontend_template": matching_template,  # 매칭된 템플릿 이름 전달
                    "private": False
                },
                headers={"Authorization": f"Bearer {request.auth}"}  # 인증 토큰 전달
            )

            # 6. repo 앱의 응답을 그대로 반환
            return Response(response.json(), status=response.status_code)

        except Exception as e:
            print(f"Error: {e}")
            return Response(
                {"error": "Failed to create project"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def find_matching_template(self, tech_stack_name):
        """
        사용자가 입력한 기술 스택을 기반으로 적절한 템플릿을 찾습니다.
        """
        templates = [
            "React",
            "Vue",
        ]

        # 기술 스택을 기반으로 템플릿 선택
        for template in templates:
            if all(tech in template for tech in tech_stack_name):
                return template

        return None  # 매칭되는 템플릿이 없는 경우


class FrontendView(APIView):
    def get(self, request, *args, **kwargs):
        """
        프론트엔드 뷰를 반환합니다.
        """
        return Response({"message": "프론트엔드 뷰에 접근했습니다."}, status=status.HTTP_200_OK)