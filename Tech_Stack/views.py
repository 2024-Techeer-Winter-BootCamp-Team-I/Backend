from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
import os
import shutil
import requests

class TechStackSetupView(APIView):
    @swagger_auto_schema(
        operation_summary='프로젝트 세팅 API',
        operation_description="Create a new project with the selected tech stack",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'frontend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='프론트엔드 기술 스택 리스트'),
                'backend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='백엔드 기술 스택 리스트'),
            },
            required=[]
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
        frontend_tech_stack = request.data.get('frontend_tech_stack', [])
        backend_tech_stack = request.data.get('backend_tech_stack', [])

        if not frontend_tech_stack and not backend_tech_stack:
            return Response(
                {"error": "프론트엔드 또는 백엔드 기술 스택 중 하나는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 임시 디렉터리 생성
            temp_dir = os.path.join(settings.BASE_DIR, "temp", "my-project")
            os.makedirs(temp_dir, exist_ok=True)

            # 프론트엔드 템플릿 처리
            frontend_template = None
            if frontend_tech_stack:
                frontend_template = self.find_matching_template(frontend_tech_stack, 'frontend')
                if not frontend_template:
                    return Response(
                        {"error": "프론트엔드 템플릿을 찾을 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                frontend_template_dir = os.path.join("Tech_Stack", "Frontend", frontend_template)
                if not os.path.exists(frontend_template_dir):
                    return Response(
                        {"error": f"프론트엔드 템플릿 디렉토리를 찾을 수 없습니다: {frontend_template_dir}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                shutil.copytree(frontend_template_dir, os.path.join(temp_dir, "frontend"))

            # 백엔드 템플릿 처리
            backend_template = None
            if backend_tech_stack:
                backend_template = self.find_matching_template(backend_tech_stack, 'backend')
                if not backend_template:
                    return Response(
                        {"error": "백엔드 템플릿을 찾을 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                backend_template_dir = os.path.join("Tech_Stack", "Backend", backend_template)
                if not os.path.exists(backend_template_dir):
                    return Response(
                        {"error": f"백엔드 템플릿 디렉토리를 찾을 수 없습니다: {backend_template_dir}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                shutil.copytree(backend_template_dir, os.path.join(temp_dir, "backend"))

            # repo 앱의 create_repo 엔드포인트로 데이터 전달
            repo_url = f"http://{settings.BACKEND_DOMAIN}/api/repo/create/"
            response = requests.post(
                repo_url,
                json={
                    "repo_name": "my-project",
                    "frontend_template": frontend_template,
                    "backend_template": backend_template,
                    "private": False
                },
                headers={"Authorization": f"Bearer {request.auth}"}  # 인증 토큰 전달
            )

            # repo 앱의 응답을 그대로 반환
            return Response(response.json(), status=response.status_code)

        except Exception as e:
            print(f"Error: {e}")
            return Response(
                {"error": "Failed to create project"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def find_matching_template(self, tech_stack_name, project_type):
        """
        사용자가 입력한 기술 스택을 기반으로 적절한 템플릿을 찾습니다.
        """
        if project_type == 'frontend':
            templates = [
                "React",
                "Vue",
            ]
        elif project_type == 'backend':
            templates = [
                "Django",
                "Node.js",
            ]

        # 기술 스택을 기반으로 템플릿 선택
        for template in templates:
            if all(tech in template for tech in tech_stack_name):
                return template

        return None  # 매칭되는 템플릿이 없는 경우