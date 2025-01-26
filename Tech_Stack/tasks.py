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

def generate_models_from_erd(erd_code):
    """
    ERD 코드를 기반으로 Django 모델 코드를 생성합니다.
    """
    models_code = """from django.db import models

"""

    entities = {}
    entity_pattern = re.compile(r"(\w+)\s*\{([^}]+)\}")
    field_pattern = re.compile(r"(\w+)\s+(\w+)")

    for match in entity_pattern.finditer(erd_code):
        entity_name = match.group(1).strip()
        fields_block = match.group(2).strip()
        fields = []

        for line in fields_block.splitlines():
            line = line.strip()
            if line:
                field_match = field_pattern.match(line)
                if field_match:
                    field_name = field_match.group(1).strip()
                    field_type = field_match.group(2).strip()
                    fields.append((field_name, field_type))

        entities[entity_name] = fields

    for entity, fields in entities.items():
        models_code += f"""
class {entity}(models.Model):
"""
        # id 필드를 CharField로 정의 (Primary Key)
        # id 필드는 한 번만 정의되도록 수정
        models_code += f"    id = models.CharField(max_length=255, primary_key=True)\n"
        
        # 나머지 필드 추가
        for field_name, field_type in fields:
            # id 필드는 이미 정의되었으므로 중복으로 추가하지 않음
            if field_name.lower() != "id":  # id 필드는 이미 정의되었으므로 건너뜀
                if field_type == "string":
                    models_code += f"    {field_name} = models.CharField(max_length=255)\n"
                elif field_type == "timestamp" or field_type == "datetime":
                    models_code += f"    {field_name} = models.DateTimeField(auto_now_add=True)\n"
                elif field_type == "bool":
                    models_code += f"    {field_name} = models.BooleanField(default=False)\n"
                elif field_type == "int":
                    models_code += f"    {field_name} = models.IntegerField()\n"
                else:
                    models_code += f"    {field_name} = models.CharField(max_length=255)\n"
        models_code += "\n"

    return models_code

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

def generate_api_endpoints(api_code, backend_tech_stack):
    """
    API 코드를 기반으로 백엔드 기술 스택에 맞는 엔드포인트 코드를 생성합니다.
    """
    if "Django" in backend_tech_stack:
        try:
            # api_code에서 Markdown 코드 블록 제거
            api_code = clean_api_code(api_code)
            
            # api_code가 비어 있는지 확인
            if not api_code:
                raise ValueError("api_code가 비어 있습니다.")
            
            # api_code를 JSON 형식으로 파싱
            api_spec = json.loads(api_code)
            
            # paths에서 엔드포인트 정보 추출
            paths = api_spec.get("paths", {})
            
            # 동적으로 뷰 코드 생성
            views_code = """
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json

"""
            for endpoint, spec in paths.items():
                method = list(spec.keys())[0]  # 예: "post", "get"
                method_spec = spec[method]
                summary = method_spec.get("summary", "No summary provided.")
                description = method_spec.get("description", "No description provided.")
                parameters = method_spec.get("parameters", [])
                responses = method_spec.get("responses", {})

                # 뷰 클래스 이름 생성 (Python 네이밍 규칙에 맞게 수정)
                view_name = endpoint.replace("/", "_").replace("-", "_").strip("_").capitalize()
                # 중괄호 {} 제거 및 CamelCase로 변환
                view_name = re.sub(r'\{(\w+)\}', r'\1', view_name)  # {postid} -> postid
                view_name = ''.join([word.capitalize() for word in view_name.split('_')])  # postid -> Postid
                
                # 대문자와 대문자 사이에 언더스코어 추가
                view_name = re.sub(r'([A-Z])', r'_\1', view_name).strip('_')  # UsersUserid -> Users_Userid
                
                # 뷰 클래스 생성 (APIView 기반)
                views_code += f"""
class {view_name}(APIView):
    def {method}(self, request, *args, **kwargs):
        try:
            data = request.data  
            
            return Response({responses.get("200", {}).get("schema", {})}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({{"error": str(e)}}, status=status.HTTP_400_BAD_REQUEST)
"""
            return views_code.strip()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in api_code: {e}")
        except Exception as e:
            raise ValueError(f"Error generating API endpoints: {e}")
    else:
        raise ValueError("지원되지 않는 백엔드 기술 스택입니다.")

def generate_urls_from_views(app_name):
    """
    views.py에 정의된 API 엔드포인트를 기반으로 urls.py를 동적으로 생성합니다.
    """
    urls_code = f"""
from django.urls import path
from . import views

urlpatterns = [
"""
    
    # views.py에 정의된 뷰 클래스 이름을 기반으로 URL 패턴 생성
    views_code = """
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import json
"""
    
    # views.py 파일을 읽어서 뷰 클래스 이름 추출
    with open(f"{app_name}/views.py", "r") as f:
        views_content = f.read()
    
    # 뷰 클래스 이름 추출 (예: class GenerateImageview(APIView):)
    view_classes = re.findall(r"class\s+(\w+)\(APIView\):", views_content)
    
    for view_class in view_classes:
        # 뷰 클래스 이름에서 "View"를 제거하고 소문자로 변환하여 URL 패턴 생성
        endpoint = view_class.replace("View", "").lower()
        urls_code += f"    path('{endpoint}', views.{view_class}.as_view(), name='{endpoint}'),\n"
    
    urls_code += "]"
    
    return urls_code.strip()

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
            app_name = "app"
            app_dir = os.path.join(backend_dir, app_name)
            os.chdir(backend_dir)
            subprocess.run(["python", "manage.py", "startapp", app_name], check=True)

            # models.py, views.py, urls.py 생성 (기존 코드)
            models_code = generate_models_from_erd(erd_code)
            models_path = os.path.join(app_dir, "models.py")
            with open(models_path, "w") as f:
                f.write(models_code)

            api_endpoints_code = generate_api_endpoints(api_code, backend_tech_stack)
            api_endpoints_path = os.path.join(app_dir, "views.py")
            with open(api_endpoints_path, "w") as f:
                f.write(api_endpoints_code)

            urls_code = generate_urls_from_views(app_name)
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