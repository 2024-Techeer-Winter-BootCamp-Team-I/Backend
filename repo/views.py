from django.contrib.auth import get_user_model  # User 모델 임포트
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
import logging
from .tasks import copy_and_push_to_github
from login.models import Project
from celery.result import AsyncResult

# User 모델 가져오기
User = get_user_model()

# 로깅 설정
logger = logging.getLogger(__name__)

@swagger_auto_schema(
    method='post',
    operation_summary='레포지토리 생성 API',
    operation_description="""
    GitHub 레포지토리 생성 API
    - 사용자가 GitHub로 로그인한 상태여야 합니다.
    - GitHub 액세스 토큰을 사용하여 레포지토리를 생성합니다.
    - 조직(organization)에 레포지토리를 생성할 수도 있습니다.
    """,
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'organization_name': openapi.Schema(type=openapi.TYPE_STRING, description='레포지토리를 생성할 조직 이름'),
            'repo_name': openapi.Schema(type=openapi.TYPE_STRING, description='생성할 레포지토리 이름'),
            'private': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='비공개 레포지토리 여부 (기본값: false)'),
            'project_dir': openapi.Schema(type=openapi.TYPE_STRING, description='프로젝트 디렉터리 경로'),
        },
        required=['repo_name', 'project_dir']  # project_dir도 필수로 변경
    ),
    responses={
        201: openapi.Response(
            description='레포지토리 생성 성공',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING, description='작업 상태'),
                    'repo_url': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 레포지토리 URL'),
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
                }
            )
        ),
        400: openapi.Response(
            description='잘못된 요청',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
                }
            )
        ),
        401: openapi.Response(
            description='인증 실패',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
                }
            )
        ),
        500: openapi.Response(
            description='서버 오류',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
                }
            )
        ),
    }
)

@api_view(['POST'])
def create_repo(request):
    """
    GitHub 레포지토리 생성 및 파일 푸시 API
    """
    if request.method != 'POST':
        return Response({"message": "GET 요청은 허용되지 않습니다. POST 요청을 사용하세요."}, status=405)

    # 사용자의 GitHub 액세스 토큰 확인
    user = request.user
    if not isinstance(user, User):  # User 모델의 인스턴스인지 확인
        logger.error("request.user가 User 모델의 인스턴스가 아닙니다.")
        return Response({"message": "인증된 사용자 정보가 올바르지 않습니다."}, status=401)

    access_token = user.access_token

    if not access_token:
        logger.error("GitHub 액세스 토큰이 없습니다.")
        return Response({"message": "GitHub 액세스 토큰이 없습니다."}, status=401)

    # 요청 데이터 유효성 검사
    repo_name = request.data.get('repo_name')
    private = request.data.get('private', False)
    organization_name = request.data.get('organization_name')  # 조직 이름 (옵션)
    project_dir = request.data.get('project_dir')  # 프로젝트 디렉터리 경로 (필수)

    if not repo_name or not project_dir:
        logger.error("repo_name 또는 project_dir이 제공되지 않았습니다.")
        return Response(
            {"message": "repo_name과 project_dir은 필수입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Celery 태스크 실행
        task = copy_and_push_to_github.delay(
            project_dir=project_dir,
            frontend_template_dir=None,  # 필요 시 추가
            backend_template_dir=None,   # 필요 시 추가
            repo_name=repo_name,
            username=user.github_username,
            email=user.email,
            access_token=access_token,
            organization_name=organization_name,
            private=private
        )

        # 태스크 완료 대기
        task.wait()

        # 성공 응답
        return Response({
            "status": "success",
            "repo_url": task.result,  # Celery 태스크에서 반환된 레포지토리 URL
            "message": "레포지토리 생성 및 파일 푸시가 완료되었습니다."
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"레포지토리 생성 중 오류 발생: {str(e)}", exc_info=True)
        return Response({
            "status": "error",
            "message": f"레포지토리 생성 실패: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)