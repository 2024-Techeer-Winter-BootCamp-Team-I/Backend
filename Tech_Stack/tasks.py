import os
import re
import shutil
import subprocess
import logging
from celery import shared_task
from django.conf import settings
from celery import chain
from .utils import find_matching_template  # utils 모듈에서 임포트
from django.core.management import call_command  # call_command 추가

# 로깅 설정
logger = logging.getLogger(__name__)

@shared_task
def copy_template_files(project_dir, frontend_template_dir, backend_template_dir):
    """
    프론트엔드 및 백엔드 템플릿 파일을 복사하는 Celery 태스크
    """
    try:
        # 프론트엔드 템플릿 복사
        if frontend_template_dir:
            if os.path.exists(os.path.join(project_dir, "frontend")):
                shutil.rmtree(os.path.join(project_dir, "frontend"))
            shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"))

        # 백엔드 템플릿 복사
        if backend_template_dir:
            if os.path.exists(os.path.join(project_dir, "backend")):
                shutil.rmtree(os.path.join(project_dir, "backend"))
            shutil.copytree(backend_template_dir, os.path.join(project_dir, "backend"))

        return True
    except Exception as e:
        logger.error(f"Error copying template files: {e}", exc_info=True)
        raise


def generate_models_from_erd(erd_code):
    """
    ERD 코드를 기반으로 Django 모델 코드를 생성합니다.
    """
    models_code = """
# Generated Django Models from ERD
from django.db import models

"""

    # ERD 코드에서 엔티티와 필드를 추출
    entities = {}
    current_entity = None

    # 엔티티 블록을 찾기 위한 정규 표현식
    entity_pattern = re.compile(r"(\w+)\s*\{([^}]+)\}")
    field_pattern = re.compile(r"(\w+)\s+(\w+)")

    # 엔티티 블록 찾기
    for match in entity_pattern.finditer(erd_code):
        entity_name = match.group(1).strip()
        fields_block = match.group(2).strip()
        fields = []

        # 필드 정보 추출
        for line in fields_block.splitlines():
            line = line.strip()
            if line:
                field_match = field_pattern.match(line)
                if field_match:
                    field_name = field_match.group(1).strip()
                    field_type = field_match.group(2).strip()
                    fields.append((field_name, field_type))

        entities[entity_name] = fields

    # 엔티티를 Django 모델로 변환
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
                # 알 수 없는 필드 타입인 경우 기본적으로 CharField로 처리
                models_code += f"    {field_name} = models.CharField(max_length=255)\n"
        models_code += "\n"

    logger.info(f"Generated models_code: {models_code}")
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
def merge_design_with_project(project_dir, erd_code, api_code, diagram_code, backend_tech_stack):
    try:
        # 디렉터리 생성
        os.makedirs(project_dir, exist_ok=True)

        # 백엔드 기술 스택에 따라 코드 생성
        if "Django" in backend_tech_stack:
            # 이미 존재하는 Django 템플릿 복사
            backend_template_dir = find_matching_template(backend_tech_stack, "backend")
            if not backend_template_dir:
                raise Exception("백엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다.")
            
            # 백엔드 디렉터리 생성
            backend_dir = os.path.join(project_dir, "backend")
            if os.path.exists(backend_dir):
                shutil.rmtree(backend_dir)  # 대상 디렉터리 삭제
            
            # 템플릿 복사
            shutil.copytree(backend_template_dir, backend_dir)

            # models.py 생성 (project_dir에 생성)
            models_code = generate_models_from_erd(erd_code)
            models_path = os.path.join(project_dir, "models.py")  # project_dir에 생성
            logger.info(f"Creating models.py at: {models_path}")
            try:
                with open(models_path, "w") as f:
                    f.write(models_code)
                logger.info(f"models.py 생성 완료: {models_path}")
                # 파일이 실제로 생성되었는지 확인
                if os.path.exists(models_path):
                    logger.info(f"models.py가 성공적으로 생성되었습니다: {models_path}")
                else:
                    logger.error(f"models.py가 생성되지 않았습니다: {models_path}")
            except Exception as e:
                logger.error(f"models.py 파일 생성 중 오류 발생: {str(e)}")
                raise Exception(f"models.py 파일 생성 중 오류 발생: {str(e)}")

            # views.py 생성 (project_dir에 생성)
            api_endpoints_code = generate_api_endpoints(api_code, backend_tech_stack)
            api_endpoints_path = os.path.join(project_dir, "views.py")  # project_dir에 생성
            logger.info(f"Creating views.py at: {api_endpoints_path}")
            try:
                with open(api_endpoints_path, "w") as f:
                    f.write(api_endpoints_code)
                logger.info(f"views.py 생성 완료: {api_endpoints_path}")
                # 파일이 실제로 생성되었는지 확인
                if os.path.exists(api_endpoints_path):
                    logger.info(f"views.py가 성공적으로 생성되었습니다: {api_endpoints_path}")
                else:
                    logger.error(f"views.py가 생성되지 않았습니다: {api_endpoints_path}")
            except Exception as e:
                logger.error(f"views.py 파일 생성 중 오류 발생: {str(e)}")
                raise Exception(f"views.py 파일 생성 중 오류 발생: {str(e)}")

        # Swagger 문서 생성 (project_dir에 생성)
        swagger_code = generate_swagger_from_api(api_code)
        swagger_path = os.path.join(project_dir, "swagger.json")
        logger.info(f"Creating swagger.json at: {swagger_path}")
        try:
            with open(swagger_path, "w") as f:
                f.write(swagger_code)
            logger.info(f"swagger.json 생성 완료: {swagger_path}")
        except Exception as e:
            logger.error(f"swagger.json 파일 생성 중 오류 발생: {str(e)}")
            raise Exception(f"swagger.json 파일 생성 중 오류 발생: {str(e)}")

        return project_dir
    except Exception as e:
        logger.error(f"설계 결과물과 초기 디렉터리 합치기 중 오류 발생: {str(e)}", exc_info=True)
        raise Exception(f"설계 결과물과 초기 디렉터리 합치기 중 오류 발생: {str(e)}")
    

@shared_task
def generate_project_structure(erd_code, api_code, diagram_code, project_dir):
    """
    설계 문서를 기반으로 프로젝트 구조를 생성합니다.
    """
    try:
        # 프로젝트 디렉터리 생성
        os.makedirs(project_dir, exist_ok=True)

        # ERD, API, 다이어그램 코드를 파일로 저장
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
        # GitHub 레포지토리 생성 및 푸시 로직
        github_username = user.username  # 사용자 이름 가져오기
        repo_url = f"https://github.com/{github_username}/{repo_name}.git"

        # Git 초기화 및 커밋, 푸시
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
    """
    프로젝트 초기 설정을 위한 체인 작업을 생성합니다.
    """
    try:
        # 설계 문서 조회 (예시: Document 모델에서 document_id로 조회)
        document = Document.objects.get(id=document_id)
        erd_code = document.erd_code
        api_code = document.api_code
        diagram_code = document.diagram_code

        # 프로젝트 디렉터리 경로 설정
        project_dir = os.path.join(settings.BASE_DIR, "temp", repo_name)

        # 사용자가 선택한 기술 스택 (예시: 프론트엔드와 백엔드 기술 스택)
        frontend_tech_stack = ["React", "JavaScript", "Vite"]  # 예시: 사용자가 선택한 프론트엔드 기술 스택
        backend_tech_stack = ["Django", "PostgreSQL"]  # 예시: 사용자가 선택한 백엔드 기술 스택

        # 프론트엔드 템플릿 디렉터리 설정
        frontend_template_dir = find_matching_template(frontend_tech_stack, "Frontend")
        if not frontend_template_dir:
            logger.error(f"프론트엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {frontend_tech_stack}")
            raise Exception(f"프론트엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {frontend_tech_stack}")

        # 백엔드 템플릿 디렉터리 설정
        backend_template_dir = find_matching_template(backend_tech_stack, "Backend")
        if not backend_template_dir:
            logger.error(f"백엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {backend_tech_stack}")
            raise Exception(f"백엔드 기술 스택에 맞는 템플릿을 찾을 수 없습니다: {backend_tech_stack}")

        # 체인 작업 생성
        task_chain = chain(
            merge_design_with_project.s(project_dir, erd_code, api_code, diagram_code, backend_tech_stack),  # 1. 설계 결과물과 프로젝트 합치기
            copy_template_files.s(project_dir, frontend_template_dir, backend_template_dir),  # 2. 템플릿 파일 복사
            generate_project_structure.s(erd_code, api_code, diagram_code, project_dir),  # 3. 프로젝트 구조 생성
            push_to_github.s(repo_name, username, email, access_token, organization_name, private)  # 4. GitHub에 푸시
        )

        # 체인 작업 실행
        result = task_chain.apply_async()

        return result.id
    except Exception as e:
        logger.error(f"프로젝트 초기 설정 체인 작업 중 오류 발생: {e}", exc_info=True)
        raise