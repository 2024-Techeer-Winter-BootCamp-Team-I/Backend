import time

import docker
from celery import shared_task
from docker.errors import NotFound

@shared_task
def create_dind_task(github_name, github_url, repo_name, base_domain):
    client = docker.from_env()
    container_name = f"{github_name}-dind"

    try:
        # DIND 컨테이너 생성
        container1 = client.containers.run(
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

        #container = client.containers.get(container_name)

        # 도커 데몬 준비 대기
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                container = client.containers.get(container_name)
                print(f"Container '{container_name}' found.")
                break
            except NotFound:
                print(f"Container '{container_name}' not found, retrying...")
                time.sleep(1)
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                time.sleep(1)

        print("작업실행1")
        clone_command = f"git clone {github_url}"
        exit_code, output = container.exec_run(clone_command, tty=True, privileged=True)
        if exit_code != 0:
            raise Exception({output.decode()})

        time.sleep(3)

        print("작업실행2")
        # /app/{repo_name} 디렉토리 확인
        check_dir_command = f"ls {repo_name}"
        exit_code, output = container.exec_run(check_dir_command)
        if exit_code != 0:
            raise Exception({output.decode()})

        time.sleep(3)

        print("작업실행3")
        # docker-compose.yml 파일 확인
        check_compose_command = f"ls {repo_name}/docker-compose.yml"
        exit_code, output = container.exec_run(check_compose_command)
        if exit_code != 0:
            raise Exception({output.decode()})

        time.sleep(5)
        client = docker.from_env()
        container = client.containers.get(container_name)

        # docker-compose 실행
        compose_command = f"docker info"
        exit_code, output = container.exec_run(compose_command, tty=True, privileged=True)
        print({output.decode()})
        if exit_code != 0:
            raise Exception({output.decode()})

        print("작업실행4")
        # docker-compose 실행
        compose_command = f"docker-compose -f {repo_name}/docker-compose.yml up --build -d"
        exit_code, output = container.exec_run(compose_command, tty=True, privileged=True)
        if exit_code != 0:
            raise Exception({output.decode()})

        return {"message": "도커 컨테이너 생성 및 서비스 실행 성공"}

    except Exception as e:
        return {"error": str(e)}