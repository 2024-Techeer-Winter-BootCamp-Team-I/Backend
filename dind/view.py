import logging
import time

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
                    f"traefik.http.routers.{github_name}.rule": f"Host(`{github_name}.localhost`)",
                    f"traefik.http.routers.{github_name}.service": f"{github_name}-service",
                    f"traefik.http.services.{github_name}-service.loadbalancer.server.port": "8000",
                    "traefik.docker.network": "backend_DevSketch-Net",
                },
                environment={"DOCKER_TLS_CERTDIR": ""},
                network="backend_DevSketch-Net",
                command="/bin/sh -c 'sleep 300 && docker stop $(hostname) && docker rm $(hostname)'"
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

    while time.time() - start_time < 35:
        exit_code, _ = container.exec_run("docker info")

        if exit_code == 0:
            return True

        time.sleep(1)

    return False