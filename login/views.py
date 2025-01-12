from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='post',
    operation_summary='로그인 API',
    operation_description='사용자 로그인을 처리합니다.',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'github_id': openapi.Schema(type=openapi.TYPE_STRING, description='GitHub ID'),
        },
        required=['github_id']
    ),
    responses={
        200: openapi.Response(
            description='로그인 성공',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='로그인 성공 메시지'),
                    'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='사용자 ID'),
                    'github_id': openapi.Schema(type=openapi.TYPE_STRING, description='GitHub ID'),
                }
            )
        ),
        400: openapi.Response(
            description='로그인 실패',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='로그인 실패 메시지'),
                }
            )
        )
    }
)
@api_view(['POST'])
def login(request):
    github_id = request.data.get('github_id')

    # 여기서 실제 로그인 로직을 처리합니다.
    # 예를 들어, 데이터베이스에서 사용자를 찾고, 인증을 수행하는 등의 작업을 할 수 있습니다.

    if github_id:  # 간단한 예시로 github_id가 제공되면 성공으로 가정
        return Response({
            "message": "Login successful",
            "user_id": 1,  # 실제 사용자 ID를 반환
            "github_id": github_id
        }, status=200)
    else:
        return Response({
            "message": "Login failed"
        }, status=400)
        
def home(request):
    return render(request,'login/home.html')