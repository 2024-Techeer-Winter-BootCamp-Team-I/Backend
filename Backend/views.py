from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests
from django.conf import settings

class BackendSetupView(APIView):
    @swagger_auto_schema(
        operation_summary='Backend 세팅 API',
        operation_description="Create a new backend project with the selected tech stack",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'tech_stack_type': openapi.Schema(type=openapi.TYPE_STRING, description='Type of tech stack (1: 프론트엔드, 2: 백엔드)'),
                'tech_stack_name': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='선택한 기술스택의 세부 기술스택 리스트'),
            },
            required=['tech_stack_type', 'tech_stack_name']
        ),
        responses={
            200: openapi.Response('success', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            400: openapi.Response('Invalid tech stack type or name'),
            500: openapi.Response('Failed to create project'),
        }
    )
    def post(self, request):
        tech_stack_type = request.data.get('tech_stack_type')
        tech_stack_name = request.data.get('tech_stack_name')

        # tech_stack_type이 2(백엔드)가 아니면 에러 반환
        if tech_stack_type != "2":
            return Response(
                {"error": "Invalid tech stack type. Only type '2' (backend) is supported."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # repo 앱의 create_repo 엔드포인트로 데이터 전달
            repo_url = f"http://{settings.BACKEND_DOMAIN}/api/repo/create/"
            response = requests.post(
                repo_url,
                json={
                    "repo_name": f"my-{'-'.join(tech_stack_name)}-project",
                    "backend_template": '-'.join(tech_stack_name),  # 예: "django-rest-framework"
                    "private": False
                },
                headers={"Authorization": f"Bearer {request.auth}"}  # 인증 토큰 전달
            )

            # repo 앱의 응답을 그대로 반환
            return Response(response.json(), status=response.status_code)
        except Exception as e:
            print(e)
            return Response(
                {"error": "Failed to create project"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )