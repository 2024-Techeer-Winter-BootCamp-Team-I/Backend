from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
import shutil
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='post',
    operation_summary = '디렉터리 생성 API',
    operation_description="사용자가 선택한 기술 스택에 따라 디렉터리를 생성하고 파일을 복사합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'directory_name': openapi.Schema(type=openapi.TYPE_STRING, description='생성할 디렉터리 이름'),
            'tech_stack': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description='선택된 기술 스택 리스트 (1: 프론트엔드, 2: 백엔드)'
            ),
        },
        required=['directory_name', 'tech_stack']
    ),
    responses={
        201: openapi.Response(
            '디렉터리 생성 성공',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'directory_path': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: openapi.Response('잘못된 요청 데이터'),
        500: openapi.Response('디렉터리 생성 실패'),
    }
)
@api_view(['POST'])
def create_directories(request):
    """
    디렉터리 생성 API
    - 사용자가 선택한 기술 스택에 따라 디렉터리를 생성하고 파일을 복사합니다.
    """
    # 요청 데이터 유효성 검사
    directory_name = request.data.get('directory_name')
    tech_stack = request.data.get('tech_stack')

    if not directory_name or not tech_stack:
        return Response(
            {"status": "error", "message": "directory_name과 tech_stack은 필수입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # 1. 임시 디렉터리 생성
        temp_dir = os.path.join("temp", directory_name)
        os.makedirs(temp_dir, exist_ok=True)

        # 2. 선택된 기술 스택에 따라 파일 복사
        if 1 in tech_stack:  # 프론트엔드
            frontend_template = "react-typescript-npm-vite"  # 예시
            frontend_dir = os.path.join("Frontend", frontend_template)
            shutil.copytree(frontend_dir, os.path.join(temp_dir, "frontend"))

        if 2 in tech_stack:  # 백엔드
            backend_template = "django-rest-framework"  # 예시
            backend_dir = os.path.join("Backend", backend_template)
            shutil.copytree(backend_dir, os.path.join(temp_dir, "backend"))

        # 성공 응답
        return Response({
            "status": "success",
            "message": "디렉터리 생성이 완료되었습니다.",
            "directory_path": temp_dir
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(e)
        return Response({
            "status": "error",
            "message": f"디렉터리 생성 실패: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)