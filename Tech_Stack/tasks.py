import os
import re
import shutil
import subprocess
from celery import shared_task
from django.conf import settings
from celery import chain
from .utils import find_matching_template
from django.core.management import call_command


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
    models_code = """
# Generated Django Models from ERD
from django.db import models

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
        for field_name, field_type in fields:
            if field_type == "string":
                models_code += f"    {field_name} = models.CharField(max_length=255)\n"
            elif field_type == "timestamp":
                models_code += f"    {field_name} = models.DateTimeField(auto_now_add=True)\n"
            elif field_type == "bool":
                models_code += f"    {field_name} = models.BooleanField(default=False)\n"
            elif field_type == "int":
                models_code += f"    {field_name} = models.IntegerField()\n"
            else:
                models_code += f"    {field_name} = models.CharField(max_length=255)\n"
        models_code += "\n"

    return models_code


def generate_api_endpoints(api_code, backend_tech_stack):
    """
    API 코드를 기반으로 백엔드 기술 스택에 맞는 엔드포인트 코드를 생성합니다.
    """
    if "Django" in backend_tech_stack:
        return f"""
        # Generated Django Views from API
        from django.http import JsonResponse
        from django.views.decorators.csrf import csrf_exempt
        import json

        @csrf_exempt
        def generate_image(request):
            if request.method == "POST":
                data = json.loads(request.body)
                prompt = data.get("text")
                return JsonResponse({{"image_url": "http://example.com/generated-image.png"}})
            return JsonResponse({{"error": "Invalid request method"}}, status=400)

        @csrf_exempt
        def send_mms(request):
            if request.method == "POST":
                image = request.FILES.get("image")
                phone_number = request.POST.get("phoneNumber")
                return JsonResponse({{"status": "?? ??"}})
            return JsonResponse({{"error": "Invalid request method"}}, status=400)
        """
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
def merge_design_with_project(project_dir, erd_code, api_code, diagram_code, frontend_tech_stack, backend_tech_stack):
    try:
        os.makedirs(project_dir, exist_ok=True)

        if frontend_tech_stack:
            frontend_template_dir = find_matching_template(frontend_tech_stack, "frontend")
            if frontend_template_dir:
                if os.path.exists(os.path.join(project_dir, "frontend")):
                    shutil.rmtree(os.path.join(project_dir, "frontend"))
                shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"))
            else:
                raise Exception(f"프론트엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {frontend_tech_stack}")

        if backend_tech_stack:
            backend_template_dir = find_matching_template(backend_tech_stack, "backend")
            if not backend_template_dir:
                raise Exception("백엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다.")

            backend_dir = os.path.join(project_dir, "backend")
            if os.path.exists(backend_dir):
                shutil.rmtree(backend_dir)

            shutil.copytree(backend_template_dir, backend_dir)

            app_name = "generated_app"
            app_dir = os.path.join(backend_dir, app_name)

            os.chdir(backend_dir)
            subprocess.run(["python", "manage.py", "startapp", app_name], check=True)

            if not os.path.exists(app_dir):
                raise Exception(f"앱 디렉터리가 생성되지 않았습니다: {app_dir}")

            models_code = generate_models_from_erd(erd_code)
            models_path = os.path.join(app_dir, "models.py")
            with open(models_path, "w") as f:
                f.write(models_code)

            api_endpoints_code = generate_api_endpoints(api_code, backend_tech_stack)
            api_endpoints_path = os.path.join(app_dir, "views.py")
            with open(api_endpoints_path, "w") as f:
                f.write(api_endpoints_code)

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