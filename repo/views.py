from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import requests
from allauth.socialaccount.models import SocialToken
from django.shortcuts import get_object_or_404

@swagger_auto_schema(
    method='post',
    operation_summary='GitHub 레포지토리 생성',
    operation_description='GitHub에 새로운 레포지토리를 생성합니다. 선택적으로 조직(organization)을 지정할 수 있습니다.',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'organization_name': openapi.Schema(type=openapi.TYPE_STRING, description='조직 이름 (선택사항)'),
            'repo_name': openapi.Schema(type=openapi.TYPE_STRING, description='생성할 레포지토리 이름'),
            'private': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='비공개 레포지토리 여부 (선택사항, 기본값: false)'),
        },
        required=['repo_name']  # 필수 필드: repo_name
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
    }
)
@api_view(['POST'])
def create_repo(request):
    """
    GitHub 레포지토리 생성 API
    - 사용자가 GitHub로 로그인한 상태여야 합니다.
    - GitHub 액세스 토큰을 사용하여 레포지토리를 생성합니다.
    - 조직(organization)에 레포지토리를 생성할 수도 있습니다.
    """
    user = request.user
    if not user.is_authenticated:
        return Response({"message": "사용자가 인증되지 않았습니다."}, status=401)

    # 사용자의 GitHub 액세스 토큰 가져오기
    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider='github')
        access_token = social_token.token
    except SocialToken.DoesNotExist:
        return Response({"message": "GitHub 액세스 토큰을 찾을 수 없습니다."}, status=401)

    # 요청 데이터 파싱
    organization_name = request.data.get('organization_name')  # 조직 이름 (선택사항)
    repo_name = request.data.get('repo_name')  # 레포지토리 이름 (필수)
    private = request.data.get('private', False)  # 비공개 레포지토리 여부 (선택사항, 기본값: false)

    # 레포지토리 이름이 없는 경우 에러 반환
    if not repo_name:
        return Response({"message": "레포지토리 이름은 필수입니다."}, status=400)

    # GitHub API 엔드포인트 설정
    if organization_name:
        # 조직(organization)에 레포지토리 생성
        url = f'https://api.github.com/orgs/{organization_name}/repos'
    else:
        # 사용자의 개인 계정에 레포지토리 생성
        url = 'https://api.github.com/user/repos'

    # GitHub API에 전송할 데이터 준비
    payload = {
        "name": repo_name,  # 레포지토리 이름
        "private": private,  # 비공개 여부
    }

    # GitHub API 요청 헤더 설정
    headers = {
        "Authorization": f"Bearer {access_token}",  # 액세스 토큰 사용
        "Accept": "application/vnd.github.v3+json"  # GitHub API 버전 지정
    }

    # GitHub API에 POST 요청 보내기
    response = requests.post(url, json=payload, headers=headers)

    # 응답 처리
    if response.status_code == 201:
        # 레포지토리 생성 성공
        repo_url = response.json().get('html_url')  # 생성된 레포지토리 URL
        return Response({
            "status": "success",
            "repo_url": repo_url,
            "message": "레포지토리가 성공적으로 생성되었습니다."
        }, status=201)
    else:
        # 레포지토리 생성 실패
        return Response({
            "message": f"레포지토리 생성 실패: {response.json().get('message', '알 수 없는 오류')}"
        }, status=response.status_code)