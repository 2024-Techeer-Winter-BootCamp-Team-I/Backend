from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from django.utils import timezone
import os
import logging
import shutil
from .tasks import copy_template_files
from .models import Project, TechStack, ProjectTech
from Tech_Stack.tasks import merge_design_with_project
from document.models import Document
from django.contrib.auth import get_user_model
from .utils import find_matching_template  

User = get_user_model()
logger = logging.getLogger(__name__)

class TechStackSetupView(ViewSet):
    @swagger_auto_schema(
        operation_summary='초기 디렉터리 생성 API',
        operation_description="사용자가 선택한 기술 스택에 따라 초기 디렉터리를 생성합니다. document_id가 제공되면 설계 결과물과 합칩니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'frontend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='프론트엔드 기술 스택 리스트'),
                'backend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='백엔드 기술 스택 리스트'),
                'directory_name': openapi.Schema(type=openapi.TYPE_STRING, description='디렉터리 이름'),
                'document_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='설계 문서 ID (선택 사항)'),
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
            400: openapi.Response('Invalid tech stack name or directory name'),
            404: openapi.Response('Document not found (if document_id is provided)'),
            500: openapi.Response('Failed to create project or merge design'),
        }
    )
    @action(detail=False, methods=['post'])
    def setup_project(self, request):
        frontend_tech_stack = request.data.get('frontend_tech_stack', [])
        backend_tech_stack = request.data.get('backend_tech_stack', [])
        directory_name = request.data.get('directory_name')
        document_id = request.data.get('document_id')

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
                user=request.user,
                name=directory_name,
                directory_path=project_dir
            )

            # 프론트엔드 템플릿 처리
            frontend_template_dir = find_matching_template(frontend_tech_stack, 'frontend')
            if frontend_template_dir:
                if os.path.exists(frontend_template_dir):
                    shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"),dirs_exist_ok=True)
                    logger.info(f"Frontend template copied from {frontend_template_dir} to {os.path.join(project_dir, 'frontend')}")
                else:
                    logger.warning(f"Frontend template directory does not exist: {frontend_template_dir}")
            else:
                logger.warning("No frontend template directory found.")

            # 백엔드 템플릿 처리
            backend_template_dir = find_matching_template(backend_tech_stack, 'backend')
            if backend_template_dir:
                if os.path.exists(backend_template_dir):
                    shutil.copytree(backend_template_dir, os.path.join(project_dir, "backend"),dirs_exist_ok=True)
                    logger.info(f"Backend template copied from {backend_template_dir} to {os.path.join(project_dir, 'backend')}")
                else:
                    logger.warning(f"Backend template directory does not exist: {backend_template_dir}")
            else:
                logger.warning("No backend template directory found.")

            # document_id가 0이 아닐 경우, 설계 결과물과 합치기
            if document_id and document_id != 0:
                try:
                    document = Document.objects.get(id=document_id)
                    merge_design_with_project.delay(
                        project_dir=project_dir,
                        erd_code=document.erd_code,
                        api_code=document.api_code,
                        diagram_code=document.diagram_code,
                        frontend_tech_stack=frontend_tech_stack,
                        backend_tech_stack=backend_tech_stack
                    ).get()
                    message = "초기 디렉터리 생성 및 설계 결과물 합치기 성공"
                except Document.DoesNotExist:
                    return Response(
                        {"error": "설계 문서를 찾을 수 없습니다."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                message = "초기 디렉터리 생성 성공"

            return Response(
                {
                    "message": message,
                    "project_dir": project_dir
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.error(f"초기 디렉터리 생성 중 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {"error": "초기 디렉터리 생성 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
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
                elif any(keyword in tech_name.lower() for keyword in ["django", "node.js", "sqlite3", "mysql", "postgresql"]):
                    stack_type = "backend"
                else:
                    stack_type = "unknown"  # 기본값

                tech_stack = TechStack.objects.create(
                    name=tech_name,
                    type=stack_type,
                    created_at=timezone.now(),
                    deleted_at=None
                )

            # ProjectTech 모델에 데이터를 저장합니다.
            ProjectTech.objects.create(
                project_id=project.id,
                tech_id=tech_stack.id,
                file_path=project_dir
            )

class MergeDesignWithProjectView(APIView):
    @swagger_auto_schema(
        operation_summary='초기 디렉터리 생성 및 설계 결과물 합치기 API',
        operation_description="사용자가 선택한 기술 스택에 따라 초기 디렉터리를 생성합니다. document_id가 제공되면 설계 결과물과 합칩니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'frontend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='프론트엔드 기술 스택 리스트'),
                'backend_tech_stack': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='백엔드 기술 스택 리스트'),
                'directory_name': openapi.Schema(type=openapi.TYPE_STRING, description='디렉터리 이름'),
                'document_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='설계 문서 ID (선택 사항)'),  # document_id는 선택 사항
            },
            required=['directory_name']  # directory_name만 필수, document_id는 선택
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
            400: openapi.Response('Invalid tech stack name or directory name'),
            404: openapi.Response('Document not found (if document_id is provided)'),
            500: openapi.Response('Failed to create project or merge design'),
        }
    )
    def post(self, request):
        frontend_tech_stack = request.data.get('frontend_tech_stack', [])
        backend_tech_stack = request.data.get('backend_tech_stack', [])
        directory_name = request.data.get('directory_name')
        document_id = request.data.get('document_id')  # document_id는 선택 사항

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
                frontend_template_dir = find_matching_template(frontend_tech_stack, 'frontend')
                if frontend_template_dir:
                    self.save_project_tech(project, frontend_tech_stack, project_dir)

            # 백엔드 템플릿 처리 (백엔드 기술 스택이 있는 경우에만)
            backend_template_dir = None
            if backend_tech_stack:
                backend_template_dir = find_matching_template(backend_tech_stack, 'backend')
                if backend_template_dir:
                    self.save_project_tech(project, backend_tech_stack, project_dir)

            # document_id가 제공된 경우, 설계 결과물과 합치기
            if document_id:
                try:
                    # 설계 문서 조회
                    document = Document.objects.get(id=document_id)

                    # 설계 결과물과 초기 디렉터리 합치기
                    merge_design_with_project.delay(
                        project_dir=project_dir,
                        erd_code=document.erd_code,
                        api_code=document.api_code,
                        diagram_code=document.diagram_code,
                        backend_tech_stack=backend_tech_stack  # 백엔드 기술 스택 추가
                    ).get()  # .get()을 사용하여 동기적으로 실행

                    message = "초기 디렉터리 생성 및 설계 결과물 합치기 성공"
                except Document.DoesNotExist:
                    return Response(
                        {"error": "설계 문서를 찾을 수 없습니다."},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # document_id가 없을 경우, 정적 파일만 복사
                if frontend_template_dir:
                    shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"),dirs_exist_ok=True)
                if backend_template_dir:
                    shutil.copytree(backend_template_dir, os.path.join(project_dir, "backend"),dirs_exist_ok=True)
                message = "초기 디렉터리 생성 성공 (정적 파일 복사 완료)"

            # Celery 태스크 실행 (프론트엔드 또는 백엔드 중 하나라도 있으면 실행)
            if frontend_template_dir or backend_template_dir:
                task = copy_template_files.delay(project_dir, frontend_template_dir, backend_template_dir)
                logger.info(f"Celery 태스크 ID: {task.id}")

                return Response(  # 성공 시
                    {
                        "task_id": task.id,
                        "message": message,
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
            logger.error(f"초기 디렉터리 생성 중 오류 발생: {str(e)}", exc_info=True)
            return Response(
                {"error": "초기 디렉터리 생성 중 오류가 발생했습니다."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )