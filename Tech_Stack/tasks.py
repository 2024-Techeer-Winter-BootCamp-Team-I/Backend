import os
import json
import re
import shutil
import subprocess
import textwrap
from celery import shared_task
from django.conf import settings
from celery import chain
from .utils import find_matching_template
from django.core.management import call_command
from django.views import View
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from document.models import Document
from openai import OpenAI
import requests
import redis

# Redis 클라이언트 생성
redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=True)

# DeepSeek API 설정
api_key = os.environ.get("DEEPSEEK_API_KEY")
api_url = os.environ.get("DEEPSEEK_API_URL")

def call_deepseek_api(prompt):
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    header = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }

    response = requests.post(api_url, json=payload, headers=header)

    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]
    else:
        error_msg = response.json().get("error", "Unknown error occurred.")
        raise Exception(f"DeepSeek API 호출 실패: {error_msg}")

@shared_task
def copy_template_files(project_dir, frontend_template_dir, backend_template_dir):
    """
    프론트엔드 및 백엔드 템플릿 파일을 복사하는 Celery 태스크
    """
    try:
        if frontend_template_dir:
            if os.path.exists(os.path.join(project_dir, "frontend")):
                shutil.rmtree(os.path.join(project_dir, "frontend"))
            shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"))

        if backend_template_dir:
            if os.path.exists(os.path.join(project_dir, "backend")):
                shutil.rmtree(os.path.join(project_dir, "backend"))
            shutil.copytree(backend_template_dir, os.path.join(project_dir, "backend"))

        return True
    except Exception as e:
        raise Exception(f"Error copying template files: {e}")
    
@shared_task
def generate_models_from_erd(erd_code):
    """
    ERD 코드를 기반으로 Django 모델 코드를 생성합니다.
    """
    prompt = f"""
        다음 Mermaid 형식의 ERD 코드를 Django 모델 코드로 변환해주세요. 아래 지시사항을 정확히 따라주세요:

        {erd_code}

        1. **모델 정의**
        - 각 엔티티는 Django의 `models.Model`을 상속받는 클래스로 정의하세요.
        - 필드 타입은 ERD의 데이터 타입에 맞게 적절히 선택하세요. (예: `IntegerField`, `CharField`, `ForeignKey` 등)
        - `primary_key=True` 옵션을 사용하여 기본 키를 명시하세요.
        - 외래 키는 `ForeignKey`를 사용하여 정의하세요. `on_delete` 옵션은 `models.CASCADE`로 설정하세요.

        2. **관계 정의**
        - 1:1 관계는 `OneToOneField`를 사용하세요.
        - 1:N 관계는 `ForeignKey`를 사용하세요.
        - M:N 관계는 `ManyToManyField`를 사용하세요.

        3. **메타 클래스**
        - 각 모델 클래스에 `Meta` 클래스를 추가하고, `verbose_name` 및 `verbose_name_plural`을 정의하세요.

        4. **출력 형식**
        - 생성된 Django 모델 코드만 출력하세요. 다른 설명은 생략하세요.
        - 설명과 주석 없이 Django에서 바로 사용할 수 있도록 '코드만' 출력하세요.
        - 순수한 Python 코드만 생성하세요.
        - `'''`(삼중 따옴표)를 사용하지 마세요.
        - 코드 블록이나 문자열 리터럴로 감싸지 마세요.
    """

    try:
        # DeepSeek API를 호출하여 Django 모델 코드 생성
        models_code = call_deepseek_api(prompt)
        return models_code
    except Exception as e:
        raise Exception(f"Error generating Django models from ERD: {e}")

def clean_api_code(api_code):
    """
    api_code에서 Markdown 코드 블록을 제거하고 순수한 JSON 데이터를 반환합니다.
    """
    # Markdown 코드 블록 제거
    if api_code.startswith("```json") and api_code.endswith("```"):
        api_code = api_code[7:-3].strip()  # ```json과 ``` 제거
    elif api_code.startswith("```") and api_code.endswith("```"):
        api_code = api_code[3:-3].strip()  # ``` 제거
    return api_code

def generate_api_endpoints(erd_code, api_code, backend_tech_stack):
    """
    ERD 코드와 API 코드를 기반으로 백엔드 기술 스택에 맞는 엔드포인트 코드를 생성합니다.
    """
    if "Django" in backend_tech_stack:
        try:
            # 프롬프트 생성
            prompt = f"""
                다음 지시사항에 따라 Django views.py 파일을 생성해주세요:

                ERD 코드{erd_code}와 API 코드{api_code}를 참고하여 Django views.py 파일을 생성해주세요

                출력 형식:
                - 순수한 Python 코드만 생성하세요.
                - `'''`(삼중 따옴표)를 사용하지 마세요.
                - 코드 블록이나 문자열 리터럴로 감싸지 마세요.
                - 설명과 주석 없이 Django에서 바로 사용할 수 있도록 코드만 출력하세요.

                모델 및 뷰 정의:
                - serializer를 사용하지 마세요.
                - ERD 코드를 기반으로 Django 모델을 생성하세요.
                - API 스펙을 기반으로 Django 뷰를 생성하세요.
                - 뷰는 Django REST Framework의 `APIView`를 사용하세요.
                - 각 엔드포인트에 대해 적절한 HTTP 메서드를 구현하세요.
            """

            # AI에게 코드 생성 요청
            views_code = call_deepseek_api(prompt)
            print(views_code)
            return views_code.strip()
        except Exception as e:
            raise ValueError(f"Error generating API endpoints: {e}")
    else:
        raise ValueError("지원되지 않는 백엔드 기술 스택입니다.")

def generate_swagger_from_api(api_code):
    """
    API 코드를 기반으로 Swagger 문서를 생성합니다.
    """
    return f"""
    {{
        "swagger": "2.0",
        "info": {{
            "title": "API Documentation",
            "version": "1.0.0"
        }},
        "paths": {{
            {api_code}
        }}
    }}
    """

@shared_task
def generate_urls_from_views(api_code, app_name):
    """
    views.py에 정의된 API 엔드포인트를 기반으로 urls.py를 동적으로 생성합니다.
    """
    # views_path = f"{app_name}/views.py"
    
    # # 파일 존재 여부 확인
    # if not os.path.exists(views_path):
    #     raise FileNotFoundError(f"'{views_path}' 파일이 존재하지 않습니다.")

    # # views.py 내용 읽기
    # try:
    #     with open(views_path, "r") as f:
    #         views_content = f.read()
    # except Exception as e:
    #     raise Exception(f"'{views_path}' 파일을 읽는 중 오류 발생: {e}")

    # print(views_content)
    
    # 프롬프트 구성
    prompt = f"""
        {api_code}코드를 기반으로 urls.py 코드를 생성하세요. 아래 지시사항을 정확히 따라주세요:

        1. **URL 패턴 정의**
        - 각 함수형 뷰 또는 클래스형 뷰를 기반으로 URL 패턴을 생성하세요.
        - 함수형 뷰는 `path()`를 사용하고, 클래스형 뷰는 `as_view()`를 호출하여 `path()`로 연결하세요.
        - `urlpatterns` 리스트에 모든 URL 패턴을 정의하세요.

        2. **앱 이름 지정**
        - `app_name`을 `api`로 설정하세요.
        
        3. **출력 형식**
        - 생성된 urls.py 코드만 출력하세요. 다른 설명은 생략하세요.
        - Django에서 바로 사용할 수 있도록 코드만 출력하세요.
        - 삼중 따옴표(`'''`)를 사용하지 마세요.
        - 코드 블록이나 문자열 리터럴로 감싸지 마세요.

        아래는 출력 예시입니다.
        예를 들어, views.py가 다음과 같다면:
        
        from django.http import JsonResponse

        def get_items(request):
            return JsonResponse("예시")

        class ItemDetailView(View):
            def get(self, request, item_id):
                return JsonResponse("예시")
        

        생성되는 urls.py는 다음과 같아야 합니다:
        
        from django.urls import path
        from . import views

        app_name = 'api'

        urlpatterns = [
            path('items/', views.get_items, name='get_items'),
            path('items/<int:item_id>/', views.ItemDetailView.as_view(), name='item_detail'),
        ]
        위의 예시를 참고해서 출력 형식에 맞게 urls.py코드를 출력해주세요.
        
    """

    try:
        # DeepSeek API를 호출하여 urls.py 코드 생성
        urls_code = call_deepseek_api(prompt)
        print(urls_code)

        # 생성된 코드 검증
        if "urlpatterns" not in urls_code or "path" not in urls_code:
            raise ValueError("생성된 urls.py 코드가 유효하지 않습니다.")
        
        return urls_code
    except Exception as e:
        raise Exception(f"Error generating Django urls from views: {e}")


def generate_docker_compose(project_dir, frontend_tech_stack, backend_tech_stack):
    """
    기술 스택에 맞는 docker-compose.yml 파일을 생성합니다.
    """
    docker_compose_content = """
version: '3.8'

services:
"""

    # 프론트엔드 서비스 추가
    if frontend_tech_stack:
        if "React" in frontend_tech_stack:
            docker_compose_content += """
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    volumes:
      - ./frontend:/app
    restart: always
"""

    # 백엔드 서비스 추가
    if backend_tech_stack:
        if "Django" in backend_tech_stack:
            docker_compose_content += """
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    environment:
      DJANGO_SETTINGS_MODULE: config.settings
    command: >
      sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
    restart: always
"""

    # 데이터베이스 서비스 추가 (예: PostgreSQL)
    if "PostgreSQL" in backend_tech_stack:
        docker_compose_content += """
  db:
    image: postgres:13
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
"""

    # 볼륨 정의 (데이터베이스 데이터 유지용)
    docker_compose_content += """
volumes:
  postgres_data:
"""

    # docker-compose.yml 파일 저장
    docker_compose_path = os.path.join(project_dir, "docker-compose.yml")
    with open(docker_compose_path, "w") as f:
        f.write(docker_compose_content.strip())

    return docker_compose_path

@shared_task
def merge_design_with_project(project_dir, erd_code, api_code, diagram_code, frontend_tech_stack, backend_tech_stack):
    try:
        os.makedirs(project_dir, exist_ok=True)

        # 프론트엔드 템플릿 복사
        if frontend_tech_stack:
            frontend_template_dir = find_matching_template(frontend_tech_stack, "frontend")
            if frontend_template_dir:
                if os.path.exists(os.path.join(project_dir, "frontend")):
                    shutil.rmtree(os.path.join(project_dir, "frontend"))
                shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"))
            else:
                raise Exception(f"프론트엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {frontend_tech_stack}")

        # 백엔드 템플릿 복사
        if backend_tech_stack:
            backend_template_dir = find_matching_template(backend_tech_stack, "backend")
            if not backend_template_dir:
                raise Exception("백엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다.")

            backend_dir = os.path.join(project_dir, "backend")
            if os.path.exists(backend_dir):
                shutil.rmtree(backend_dir)

            shutil.copytree(backend_template_dir, backend_dir)

            # Django 앱 생성 및 설정 (기존 코드)
            app_name = "generated_app"
            app_dir = os.path.join(backend_dir, app_name)
            os.chdir(backend_dir)
            subprocess.run(["python", "manage.py", "startapp", app_name], check=True)

            # models.py, views.py, urls.py 생성 (기존 코드)
            models_code = generate_models_from_erd(erd_code)
            models_path = os.path.join(app_dir, "models.py")
            with open(models_path, "w") as f:
                f.write(models_code)

            api_endpoints_code = generate_api_endpoints(erd_code, api_code, backend_tech_stack)
            api_endpoints_path = os.path.join(app_dir, "views.py")
            with open(api_endpoints_path, "w") as f:
                f.write(api_endpoints_code)

            urls_code = generate_urls_from_views(app_name, api_code)
            urls_path = os.path.join(app_dir, "urls.py")
            with open(urls_path, "w") as f:
                f.write(urls_code)

            # settings.py 및 urls.py 설정 (기존 코드)
            settings_path = os.path.join(backend_dir, "config", "settings.py")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings_content = f.read()

                if f"'{app_name}'" not in settings_content:
                    settings_content = settings_content.replace(
                        "INSTALLED_APPS = [",
                        f"INSTALLED_APPS = [\n    '{app_name}',"
                    )

                    with open(settings_path, "w") as f:
                        f.write(settings_content)

            project_urls_path = os.path.join(backend_dir, "config", "urls.py")
            if os.path.exists(project_urls_path):
                with open(project_urls_path, "r") as f:
                    project_urls_content = f.read()

                if f"path('api/', include('{app_name}.urls'))" not in project_urls_content:
                    project_urls_content = project_urls_content.replace(
                        "urlpatterns = [",
                        f"from django.urls import include\n\nurlpatterns = [\n    path('api/', include('{app_name}.urls')),"
                    )

                    with open(project_urls_path, "w") as f:
                        f.write(project_urls_content)

        # docker-compose.yml 파일 생성
        generate_docker_compose(project_dir, frontend_tech_stack, backend_tech_stack)

        # Swagger 문서 생성 (기존 코드)
        swagger_code = generate_swagger_from_api(api_code)
        swagger_path = os.path.join(project_dir, "swagger.json")
        with open(swagger_path, "w") as f:
            f.write(swagger_code)

        return project_dir
    except Exception as e:
        raise Exception(f"설계 결과물과 초기 디렉터리 합치기 중 오류 발생: {str(e)}")

@shared_task
def generate_project_structure(erd_code, api_code, diagram_code, project_dir):
    """
    설계 문서를 기반으로 프로젝트 구조를 생성합니다.
    """
    try:
        os.makedirs(project_dir, exist_ok=True)

        with open(os.path.join(project_dir, "erd.txt"), "w") as f:
            f.write(erd_code)

        with open(os.path.join(project_dir, "api.txt"), "w") as f:
            f.write(api_code)

        with open(os.path.join(project_dir, "diagram.txt"), "w") as f:
            f.write(diagram_code)

        return "프로젝트 구조 생성 완료"
    except Exception as e:
        return f"프로젝트 구조 생성 중 오류 발생: {str(e)}"

@shared_task
def push_to_github(project_dir, repo_name, user):
    """
    프로젝트 디렉터리를 GitHub에 푸시합니다.
    """
    try:
        github_username = user.username
        repo_url = f"https://github.com/{github_username}/{repo_name}.git"

        os.chdir(project_dir)
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
        subprocess.run(["git", "push", "-u", "origin", "master"], check=True)

        return repo_url
    except Exception as e:
        return f"GitHub 푸시 중 오류 발생: {str(e)}"

@shared_task
def setup_project_chain(document_id, repo_name, username, email, access_token, organization_name=None, private=False):
    try:
        document = Document.objects.get(id=document_id)
        erd_code = document.erd_code
        api_code = document.api_code
        diagram_code = document.diagram_code

        project_dir = os.path.join(settings.BASE_DIR, "temp", repo_name)

        frontend_tech_stack = ["React", "JavaScript", "Vite"]
        backend_tech_stack = ["Django", "PostgreSQL"]

        task_chain = chain(
            merge_design_with_project.s(
                project_dir, erd_code, api_code, diagram_code, frontend_tech_stack, backend_tech_stack
            ),
            copy_template_files.s(project_dir, frontend_tech_stack, backend_tech_stack),
            generate_project_structure.s(erd_code, api_code, diagram_code, project_dir),
            push_to_github.s(repo_name, username, email, access_token, organization_name, private)
        )

        result = task_chain.apply_async()

        return result.id
    except Exception as e:
        raise Exception(f"프로젝트 초기 설정 체인 작업 중 오류 발생: {e}")