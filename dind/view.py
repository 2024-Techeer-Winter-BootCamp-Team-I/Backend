import logging
import time
import os

import docker
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from dind.serializers import CreateDindSerializer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Create your views here.

@swagger_auto_schema(
    methods=['POST'],
    operation_summary="도커 컨테이너 생성 API",
    request_body=CreateDindSerializer,
    responses={
        201: "도커 컨테이너 생성 성공",
        400: "Bad Request",
        500: "Internal Server Error",
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_dind_handler(request):
    serializer = CreateDindSerializer(data = request.data)

    if serializer.is_valid():

        github_name = serializer.validated_data.get("github_name")
        github_url = serializer.validated_data.get("github_url")
        repo_name = serializer.validated_data.get("repo_name")

        base_domain = os.environ.get("BASE_DOMAIN", "localhost")

        client = docker.from_env()
        container_name = f"{github_name}-dind"

        try:
            #DIND 컨테이너 생성
            container = client.containers.run(
                image="docker:dind",
                name=container_name,
                privileged=True,
                detach=True,
                labels={
                    "traefik.enable": "true",
                    f"traefik.http.routers.{github_name}.rule": f"HostRegexp(`{github_name}.{base_domain}`)",
                    f"traefik.http.routers.{github_name}.tls.certresolver": "letsencrypt",
                    f"traefik.http.routers.{github_name}.entrypoints": "websecure",
                    f"traefik.http.services.{github_name}.loadbalancer.server.port": "8000",
                    f"traefik.http.middlewares.{github_name}-replacepathregex.replacepathregex.regex": "^/.*",
                    f"traefik.http.middlewares.{github_name}-replacepathregex.replacepathregex.replacement": "/"
                },
                environment={"DOCKER_TLS_CERTDIR": ""},
                network="directory_DevSketch-Net",
            )

            #도커 데몬이 준비될 때까지 대기
            if not wait_for_docker(container):
                return Response(
                    {"error": "도커 데몬 준비 실패."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            #도커 컴포즈 및 git 설치 및 /app 디렉토리 생성
            install_commands = (
                "apk add --no-cache curl git && "
                "curl -L https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && "
                "chmod +x /usr/local/bin/docker-compose && "
                "mkdir -p /app"
            )
            exit_code, output = container.exec_run(
                ['/bin/sh', '-c', install_commands],
                tty=True,
                privileged=True
            )
            if exit_code != 0:
                return Response(
                    {"error": f"도커 컴포즈 및 git 설치 실패: {output.decode()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            #Git 클론
            clone_command = f"git clone {github_url} /app/{repo_name}"
            exit_code, output = container.exec_run(clone_command, tty=True, privileged=True)
            if exit_code != 0:
                return Response(
                    {"error": f"Git 클론 실패: {output.decode()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

             # /app/{repo_name} 디렉토리 확인
            check_dir_command = f"ls /app/{repo_name}"
            exit_code, output = container.exec_run(check_dir_command)
            if exit_code != 0:
                return Response(
                    {"error": f"/app/{repo_name} 디렉토리 확인 실패: {output.decode()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # docker-compose.yml 파일 확인
            check_compose_command = f"ls /app/{repo_name}/docker-compose.yml"
            exit_code, output = container.exec_run(check_compose_command)
            if exit_code != 0:
                return Response(
                    {"error": "docker-compose.yml 파일이 존재하지 않습니다."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            #docker-compose 실행
            compose_command = f"docker-compose -f /app/{repo_name}/docker-compose.yml up --build -d"
            exit_code, output = container.exec_run(compose_command, tty=True, privileged=True)
            if exit_code != 0:
                return Response(
                    {"error": f"docker-compose 실행 실패: {output.decode()}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "도커 컨테이너 생성 및 서비스 실행 성공"},
                status=status.HTTP_201_CREATED,
            )

        except docker.errors.APIError as e:
            return Response(
                {"error": f"도커 API 에러: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            return Response(
                {"error": f"알 수 없는 에러: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            pass

#도커 기다리는 함수
def wait_for_docker(container):

    start_time = time.time()

    while time.time() - start_time < 30:
        exit_code, _ = container.exec_run("docker info")

        if exit_code == 0:
            return True

        time.sleep(1)

    return False