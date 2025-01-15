import os
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from github import Github
from allauth.socialaccount.models import SocialToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@swagger_auto_schema(
    method='post',
    operation_summary = '레포지토리 생성 API',
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
        },
        required=['repo_name']
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
    - 사용자가 GitHub로 로그인한 상태여야 합니다.
    - GitHub 액세스 토큰을 사용하여 레포지토리를 생성하고 파일을 푸시합니다.
    - 조직(organization)에 레포지토리를 생성할 수도 있습니다.
    """
    if request.method != 'POST':
        return Response({"message": "GET 요청은 허용되지 않습니다. POST 요청을 사용하세요."}, status=405)

    user = request.user
    if not user.is_authenticated:
        return Response({"message": "사용자가 인증되지 않았습니다."}, status=401)

    # 사용자의 GitHub 액세스 토큰 가져오기
    try:
        social_token = SocialToken.objects.get(account__user=user, account__provider='github')
        access_token = social_token.token
    except SocialToken.DoesNotExist:
        return Response({"message": "GitHub 액세스 토큰을 찾을 수 없습니다."}, status=401)

    # 요청 데이터 유효성 검사
    directory_path = request.data.get('directory_path')
    repo_name = request.data.get('repo_name')
    private = request.data.get('private', False)
    organization_name = request.data.get('organization_name')  # 조직 이름 (옵션)

    if not directory_path or not repo_name:
        return Response(
            {"message": "directory_path와 repo_name은 필수입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # GitHub API 클라이언트 초기화
        g = Github(access_token)

        # 레포지토리 생성
        if organization_name:
            # 조직(organization)에 레포지토리 생성
            org = g.get_organization(organization_name)
            repo = org.create_repo(repo_name, private=private)
        else:
            # 사용자의 개인 계정에 레포지토리 생성
            user = g.get_user()
            repo = user.create_repo(repo_name, private=private)

        # 파일 푸시
        push_directory_to_github(repo, directory_path)

        # 성공 응답
        return Response({
            "status": "success",
            "repo_url": repo.html_url,
            "message": "레포지토리 생성 및 파일 푸시가 완료되었습니다."
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        print(e)
        return Response({
            "status": "error",
            "message": f"레포지토리 생성 실패: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def push_directory_to_github(repo, directory):
    """
    디렉터리의 파일을 GitHub 레포지토리에 푸시합니다.
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            repo_path = os.path.relpath(file_path, directory).replace('\\', '/')
            repo.create_file(
                path=repo_path,
                message=f"Add {repo_path}",
                content=content,
                branch="main"
            )