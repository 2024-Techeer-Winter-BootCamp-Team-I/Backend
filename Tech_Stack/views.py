from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
import os
import logging
from .tasks import copy_template_files
from .models import Project, TechStack, ProjectTech

# 로거 초기화
logger = logging.getLogger(__name__)

class TechStackSetupView(APIView):
    @swagger_auto_schema(
        operation_summary='프로젝트 세팅 API',
        operation_description="Create a new project with the selected tech stack",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'frontend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='프론트엔드 기술 스택 리스트'),
                'backend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='백엔드 기술 스택 리스트'),
                'directory_name': openapi.Schema(type=openapi.TYPE_STRING, description='디렉터리 이름'),
            },
            required=['directory_name']
        ),
        responses={
            202: openapi.Response('Accepted', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'task_id': openapi.Schema(type=openapi.TYPE_STRING, description='Celery 태스크 ID'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
                    'project_dir': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 프로젝트 디렉터리 경로'),
                }
            )),
            400: openapi.Response('Invalid tech stack name'),
            500: openapi.Response('Failed to create project'),
        }
    )
    def post(self, request):
        frontend_tech_stack = request.data.get('frontend_tech_stack', [])
        backend_tech_stack = request.data.get('backend_tech_stack', [])
        directory_name = request.data.get('directory_name')

        if not directory_name:
            return Response(
                {"error": "디렉터리 이름은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 디렉터리 생성
            project_dir = os.path.join(settings.BASE_DIR, "temp", directory_name)
            os.makedirs(project_dir, exist_ok=True)

            # 프로젝트 모델에 디렉터리 경로 저장
            project = Project.objects.create(
                user=request.user,  # 현재 사용자
                name=directory_name,  # 프로젝트 이름
                directory_path=project_dir  # 디렉터리 경로 저장
            )

            # 프론트엔드 템플릿 처리 (프론트엔드 기술 스택이 있는 경우에만)
            frontend_template_dir = None
            if frontend_tech_stack:
                frontend_template_dir = self.find_matching_template(frontend_tech_stack, 'frontend')
                if frontend_template_dir:
                    self.save_project_tech(project, frontend_tech_stack, project_dir)

            # 백엔드 템플릿 처리 (백엔드 기술 스택이 있는 경우에만)
            backend_template_dir = None
            if backend_tech_stack:
                backend_template_dir = self.find_matching_template(backend_tech_stack, 'backend')
                if backend_template_dir:
                    self.save_project_tech(project, backend_tech_stack, project_dir)

            # Celery 태스크 실행 (프론트엔드 또는 백엔드 중 하나라도 있으면 실행)
            if frontend_template_dir or backend_template_dir:
                task = copy_template_files.delay(project_dir, frontend_template_dir, backend_template_dir)
                logger.info(f"Celery 태스크 ID: {task.id}")

                return Response(  # 성공 시
                    {
                        "task_id": task.id,
                        "message": "성공",
                        "project_dir": project_dir  # 생성된 디렉터리 경로 추가
                    },
                    status=status.HTTP_202_ACCEPTED
                )
            else:
                return Response(
                    {"error": "유효한 기술 스택이 제공되지 않았습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            logger.error(f"프로젝트 생성 중 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {"error": "프로젝트 생성 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def find_matching_template(self, tech_stack_name, project_type):
        """
        사용자가 입력한 기술 스택을 기반으로 적절한 템플릿을 찾습니다.
        """
        if project_type == 'frontend':
            templates = [
                "react-js-npm-vite",
                "react-js-npm-webpack",
                "react-ts-npm-vite",
                "react-ts-npm-webpack",
                "react-js-yarn-vite",
                "react-js-yarn-webpack",
                "react-ts-yarn-vite",
                "react-ts-yarn-webpack",
            ]
        elif project_type == 'backend':
            templates = [
                "Django_postgresql",
                "Django_mysql",
                "Node.js_postgresql",
                "Node.js_mysql",
            ]

        # 기술 스택을 소문자로 변환하여 비교
        tech_stack_name = [tech.lower() for tech in tech_stack_name]
        for template in templates:
            template_lower = template.lower()
            if all(tech in template_lower for tech in tech_stack_name):
                return os.path.join("Tech_Stack", project_type.capitalize(), template)

        return None
 
    def save_project_tech(self, project, tech_stack_names, project_dir):
        """
        ProjectTech 모델에 데이터를 저장합니다.
        사용자가 입력한 기술 스택이 TechStack 모델에 없는 경우, 새로운 기술 스택을 추가합니다.
        """
        if not tech_stack_names:
            logger.warning("tech_stack_names가 비어 있습니다.")
            return

        for tech_name in tech_stack_names:
            # TechStack 모델에서 기술 스택을 찾습니다.
            tech_stack = TechStack.objects.filter(name__iexact=tech_name).first()

            # 기술 스택이 없는 경우, 새로운 기술 스택을 추가합니다.
            if not tech_stack:
                logger.info(f"새로운 기술 스택 추가: {tech_name}")

                # 기술 스택 타입 결정
                if any(keyword in tech_name.lower() for keyword in ["react", "js", "npm", "vite", "webpack","ts","yarn","javascript","typescript"]):
                    stack_type = "frontend"
                elif any(keyword in tech_name.lower() for keyword in ["django", "node.js", "mysql", "postgresql"]):
                    stack_type = "backend"
                else:
                    stack_type = "unknown"  # 기본값

                tech_stack = TechStack.objects.create(
                    name=tech_name,
                    type=stack_type,  # 프론트엔드/백엔드 구분
                    created_at=timezone.now(),
                    deleted_at=None
                )

            # ProjectTech 모델에 데이터를 저장합니다.
            ProjectTech.objects.create(
                project_id=project.id,  # project.id를 사용하여 id 값을 전달
                tech_id=tech_stack.id,  # tech_stack.id를 사용하여 id 값을 전달
                file_path=project_dir  # project_dir을 file_path에 저장
            )