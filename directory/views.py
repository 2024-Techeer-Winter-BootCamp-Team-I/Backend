from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
import shutil

@swagger_auto_schema(
    method='post',
    operation_summary='디렉터리 생성 및 뷰 전환 API',
    operation_description="사용자가 선택한 기술 스택에 따라 디렉터리를 생성하고, 해당 기술 스택 뷰로 전환합니다.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'directory_name': openapi.Schema(type=openapi.TYPE_STRING, description='생성할 디렉터리 이름'),
            'tech_stack': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description='선택된 기술 스택 리스트 (1: 프론트엔드, 2: 백엔드 (중복가능))'
            ),
        },
        required=['directory_name', 'tech_stack']
    ),
    responses={
        200: openapi.Response(
            '뷰 전환 성공',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'redirect_to': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: openapi.Response('잘못된 요청 데이터'),
        500: openapi.Response('뷰 전환 실패'),
    }
)
@api_view(['POST'])
def create_directories(request):
    """
    디렉터리 생성 및 뷰 전환 API
    - 사용자가 선택한 기술 스택에 따라 디렉터리를 생성하고, 해당 기술 스택 뷰로 전환합니다.
    - 1번(프론트엔드)과 2번(백엔드)을 중복으로 선택할 수 있습니다.
    - 디렉터리 이름은 하나이며, 선택한 기술 스택에 따라 정적 파일을 디렉터리 안에 추가합니다.
    - 중복 선택 시, 프론트엔드 뷰와 백엔드 뷰를 순차적으로 방문합니다.
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
        # 디렉터리 생성
        base_dir = os.path.join("static", directory_name)  # 디렉터리 경로 설정
        os.makedirs(base_dir, exist_ok=True)  # 디렉터리 생성 (이미 존재하면 무시)

        # 기술 스택에 따라 정적 파일 복사
        if 1 in tech_stack:  # 프론트엔드
            frontend_template_dir = os.path.join("Tech_Stack", "Frontend")  # 프론트엔드 템플릿 경로
            if not os.path.exists(frontend_template_dir):
                return Response({
                    "status": "error",
                    "message": f"프론트엔드 템플릿 디렉토리를 찾을 수 없습니다: {frontend_template_dir}"
                }, status=status.HTTP_400_BAD_REQUEST)
            shutil.copytree(frontend_template_dir, os.path.join(base_dir, "frontend"))  # 프론트엔드 파일 복사

        if 2 in tech_stack:  # 백엔드
            backend_template_dir = os.path.join("Tech_Stack", "Backend")  # 백엔드 템플릿 경로
            if not os.path.exists(backend_template_dir):
                return Response({
                    "status": "error",
                    "message": f"백엔드 템플릿 디렉토리를 찾을 수 없습니다: {backend_template_dir}"
                }, status=status.HTTP_400_BAD_REQUEST)
            shutil.copytree(backend_template_dir, os.path.join(base_dir, "backend"))  # 백엔드 파일 복사

        # 뷰 전환 로직
        if 1 in tech_stack and 2 in tech_stack:  # 프론트엔드와 백엔드 모두 선택된 경우
            return Response({
                "status": "success",
                "message": "프론트엔드 뷰와 백엔드 뷰를 순차적으로 방문합니다.",
                "redirect_to": ["/frontend/", "/backend/"]  # 프론트엔드와 백엔드 뷰 URL
            }, status=status.HTTP_200_OK)

        elif 1 in tech_stack:  # 프론트엔드만 선택된 경우
            return Response({
                "status": "success",
                "message": "프론트엔드 뷰로 전환합니다.",
                "redirect_to": ["/frontend/"]  # 프론트엔드 뷰 URL
            }, status=status.HTTP_200_OK)

        elif 2 in tech_stack:  # 백엔드만 선택된 경우
            return Response({
                "status": "success",
                "message": "백엔드 뷰로 전환합니다.",
                "redirect_to": ["/backend/"]  # 백엔드 뷰 URL
            }, status=status.HTTP_200_OK)

        else:  # 기술 스택이 선택되지 않은 경우
            return Response({
                "status": "error",
                "message": "선택된 기술 스택이 없습니다."
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print(e)
        return Response({
            "status": "error",
            "message": f"뷰 전환 실패: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)