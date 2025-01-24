import time

import docker
from celery import shared_task


@shared_task
def create_dind_task(github_name, github_url, repo_name, base_domain):
    client = docker.from_env()
    container_name = f"{github_name}-dind"

    try:
        # DIND 컨테이너 생성
        container = client.containers.run(
            image = "docker:dind",
            name = container_name,
            privileged=True,
            detach = True,
            labels = {
                "traefik.enable": "true",
                f"traefik.http.routers.{github_name}.rule": f"HostRegexp(`{github_name}.{base_domain}`)",
                f"traefik.http.routers.{github_name}.tls.certresolver": "letsencrypt",
                f"traefik.http.routers.{github_name}.entrypoints": "websecure",
                f"traefik.http.services.{github_name}.loadbalancer.server.port": "8000",
                f"traefik.http.middlewares.{github_name}-replacepathregex.replacepathregex.regex": "^/.*",
                f"traefik.http.middlewares.{github_name}-replacepathregex.replacepathregex.replacement": "/"
            },
            environment = {"DOCKER_TLS_CERTDIR": ""},
            network = "directory_DevSketch-Net",
        )

        # 도커 데몬 준비 대기
        start_time = time.time()
        while time.time() - start_time < 30:
            exit_code, _ = container.exec_run("docker info")
            if exit_code == 0:
                break
            time.sleep(1)
        else:
            raise Exception("도커 데몬 준비 실패.")

            # Git 및 도커 컴포즈 설치
            install_commands = (
                "apk add --no-cache curl git && "
                "curl -L https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose && "
                "chmod +x /usr/local/bin/docker-compose && "
                "mkdir -p /app"
            )
            exit_code, output = container.exec_run(['/bin/sh', '-c', install_commands], tty=True, privileged=True)
            if exit_code != 0:
                raise Exception(f"도커 컴포즈 및 git 설치 실패: {output.decode()}")

            # Git 클론 및 디렉토리 확인
            clone_command = f"git clone {github_url} /app/{repo_name}"
            container.exec_run(clone_command, tty=True, privileged=True)

            # docker-compose 실행
            compose_command = f"docker-compose -f /app/{repo_name}/docker-compose.yml up --build -d"
            exit_code, output = container.exec_run(compose_command, tty=True, privileged=True)
            if exit_code != 0:
                raise Exception(f"docker-compose 실행 실패: {output.decode()}")

            return {"message": "도커 컨테이너 생성 및 서비스 실행 성공"}

    except Exception as e:
        return {"error": str(e)}