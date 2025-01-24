import os
import time

import certifi
import openai
import requests
from celery import chord

from django.http import JsonResponse, StreamingHttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config import settings
from .tasks import create_diagram, collect_results, create_erd, create_api, redis_client

from document.models import Document
from document.serializers import CreateDocumentSerializer, UpdateDocumentSerializer
from Tech_Stack.tasks import generate_project_structure, push_to_github

from login.models import Project

openai.api_key = os.environ.get("DEEPSEEK_API_KEY")
openai.api_base = os.environ.get("DEEPSEEK_API_URL")

@swagger_auto_schema(
    methods=['POST'],
    operation_summary="문서 생성 API",
    request_body=CreateDocumentSerializer,
    responses={
        201: "문서 생성 성공",
        400: "Bad Request",
        500: "Internal Server Error",
    }
)
@swagger_auto_schema(
    methods=['GET'],
    operation_summary="사용자 전체 문서 조회 API",
    responses={
        200: openapi.Response(
            description="문서 리스트 조회 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                    "data": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="문서 ID"),
                                "title": openapi.Schema(type=openapi.TYPE_STRING, description="문서 제목"),
                                "response": openapi.Schema(type=openapi.TYPE_STRING, description="AI 처리 결과"),
                            },
                        ),
                    ),
                },
            ),
        ),
        500: "Internal Server Error",
    },
)
@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def documents(request):
    user = request.user

    if request.method == "POST":
        # 문서 생성 로직
        serializer = CreateDocumentSerializer(data=request.data)

        if serializer.is_valid():
            try:
                title = serializer.validated_data.get("title")
                content = serializer.validated_data.get("content")
                requirements = serializer.validated_data.get("requirements", "No requirements provided")

                # DeepSeek API 호출을 위한 프롬프트 생성
                prompt = f"""
                    Title: {title}
                    Content: {content}
                    Requirements: {requirements}

                    위 내용을 바탕으로 체계적인 기능명세서를 작성해주세요. 다음 지시사항을 정확히 따라주세요:

                    1. **문서 구조**
                        - 문서는 다음과 같은 섹션으로 구성되어야 합니다:
                        1. **시스템 목적**: 프로젝트의 목적과 주요 기능을 간략히 설명하세요.
                        2. **기능 요구사항**: 사용자 요구사항을 기반으로 상세한 기능 목록을 작성하세요. 각 기능은 사용자 스토리 형식(예: "사용자는 [X]를 할 수 있어야 한다")으로 작성하세요.

                    2. **상세 설명**
                        - 각 섹션은 명확하고 간결하게 작성되어야 합니다.

                    3. **모듈화**
                        - 문서를 모듈화하여 각 섹션이 독립적으로 이해될 수 있도록 하세요.
                        - 각 모듈은 간단한 설명과 함께 명확하게 구분되어야 합니다.

                    4. **출력 형식**
                        - 최종 문서는 바로 제출할 수 있는 형태로 작성되어야 합니다.
                        - 출력은 마크다운 형식이 아닌 빠르게 출력되도록 문서로만 해주세요.(#,** 등 제외)
                        - 불필요한 설명이나 서론은 생략하고, 실제 문서 내용만 출력하세요.

                    5. **추가 요구사항**
                        - 현업에서 바로 사용할 수 있도록 전문적이고 실용적인 언어를 사용하세요.
                        - 가능한 한 구체적이고 명확하게 작성하세요.
                        - 마지막 요약은 빼주세요.
                        
                        **출력 예시**
                        시스템 목적:
                        - 비즈니스 목적: 사용자가 상품을 쉽게 조회하고 주문할 수 있도록 하는 것입니다.
                        - 기술적 목적: 안정적이고 확장 가능한 온라인 쇼핑몰 시스템을 구축하는 것입니다.

                        기능 요구사항:
                        1. 사용자는 상품을 조회할 수 있어야 한다. (우선순위: 높음)
                        2. 사용자는 상품을 주문할 수 있어야 한다. (우선순위: 높음)
                        3. 사용자는 주문 내역을 조회할 수 있어야 한다. (우선순위: 중간)

                        시나리오:
                        1. 사용자가 로그인 페이지에 접속합니다.
                        2. 이메일과 비밀번호를 입력합니다.
                        3. 로그인 버튼을 클릭합니다.
                        4. 시스템은 사용자 정보를 검증하고 로그인을 승인합니다.

                        비기능 요구사항:
                        - 시스템은 초당 100개의 요청을 처리할 수 있어야 합니다.
                        - 사용자 데이터는 암호화되어 저장되어야 합니다.

                        모듈화:
                        - 로그인 모듈: 입력 - 이메일, 비밀번호 / 출력 - 사용자 정보, 토큰
                        - 상품 조회 모듈: 입력 - 검색어 / 출력 - 상품 목록
                        - 주문 모듈: 입력 - 상품 ID, 수량 / 출력 - 주문 번호, 결제 정보
                        
                        위의 출력 예시는 쇼핑몰 예시입니다. 사용자가 입력한 정보를 바탕으로 예시를 참고하여 출력해주세요.
                    """

                review_result = call_deepseek_api(prompt)

                document = Document.objects.create(
                    user_id=user,
                    title=title,
                    content=content,
                    requirements=requirements,
                    result=review_result
                )

                document_id = document.id
                
                # Project 모델에 사용자 및 프로젝트 이름 저장
                project_name = title  # 프로젝트 이름을 title로 저장
                project, created = Project.objects.get_or_create(
                    user=user,
                    name=project_name,
                )

                if created:
                    print(f"프로젝트 '{project_name}'이(가) 생성되었습니다.")
                else:
                    print(f"기존 프로젝트 '{project_name}'을(를) 사용합니다.")

                def event_stream():
                    try:
                        for char in review_result:
                            yield f"data: {{\"content\": \"{char}\"}}\n\n"

                            time.sleep(0.01)

                    except Exception as e:
                        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

                response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
                response["X-Document-ID"] = str(document_id)
                return response

            except Exception as e:
                return JsonResponse({
                    "status": "error",
                    "message": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        else:
            return JsonResponse({
                "status": "error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "GET":
        # 문서 조회 로직
        try:
            documents = Document.objects.filter(user_id=user)

            document_list = [
                {
                    "id": document.id,
                    "title": document.title,
                    "response": document.result,
                }
                for document in documents
            ]

            return JsonResponse({
                "status": "success",
                "data": document_list,
            }, status=200)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e),
            }, status=500)

#----------------------------------------------------------

@swagger_auto_schema(
    method='put',
    operation_summary="문서 수정 API",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'prompt': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="추가 요청 내용을 포함한 프롬프트"
            ),
        },
        required=['prompt']  # prompt는 필수 항목
    ),
    responses={
        200: openapi.Response(description="문서 수정 성공"),
        400: "Bad Request",
        404: "Document Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_document(request, document_id):
    serializer = UpdateDocumentSerializer(data = request.data)

    if serializer.is_valid():
        try:
            # 사용자 정보 확인
            user = request.user
            document = Document.objects.get(id = document_id, user_id = user)

            prompt_input = serializer.validated_data.get("prompt")

            # DeepSeek API 호출을 위한 프롬프트 생성
            prompt = f"""
                            Title: {document.title}
                            Content: {document.content}
                            Requirements: {document.requirements}

                            위추가 요청:
                            {prompt_input}
                        1.기존 문서를 기준으로 추가 요청한 정보를 추가하여 체계적으로 다시 문서화 해주세요.
                        2.해당 기능명세에 부가적인 설명도 추가해주세요. 
                        3.실제 현업자가 바로 사용할 수 있도록 쳬계적인 기능명세를 만들어주세요. 그리고 빠른 프롬프트를 위해 해당 문서를 모듈화 해주세요.
                        4.바로 제출할 수 있도록 실제 문서 내용"만" 출력해주세요.
                        """

            # DeepSeek API 호출 후 Document 저장
            review_result = call_deepseek_api(prompt)

            document.result = review_result
            document.save()

            def event_stream():
                try:
                    for char in review_result:
                        yield f"data: {{\"content\": \"{char}\"}}\n\n"

                        time.sleep(0.01)

                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

            response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
            response["X-Document-ID"] = str(document_id)
            return response

        except Document.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "문서를 찾을 수 없습니다."
            }, status=404)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)

    else:
        return JsonResponse({
            "status": "error",
            "errors": serializer.errors
        }, status=400)

#----------------------------------------------------------

@swagger_auto_schema(
    method = 'post',
    operation_summary = "설계 생성 API",
    manual_parameters = [
        openapi.Parameter(
            'document_id',
            openapi.IN_PATH,
            description = "생성할 설계 문서의 ID",
            type = openapi.TYPE_STRING,
            required = True,
        ),
    ],
    responses = {
        200: openapi.Response(
            description="설계 생성 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                    "data": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="설계 문서 ID"),
                            "response": openapi.Schema(type=openapi.TYPE_STRING, description="AI 처리 결과"),
                        },
                    ),
                },
            ),
        ),
        400: "Bad Request",
        404: "Document Not Found",
        500: "Internal Server Error",
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def dev_document(request, document_id):
    try:
        user = request.user
        document = Document.objects.get(id=document_id, user_id = user)

    except Document.DoesNotExist:
        return Response({
            "status": "error",
            "message": "해당 설계 문서를 찾을 수 없습니다."
        }, status=status.HTTP_404_NOT_FOUND)

    # chord 병렬 작업 실행(모두 완료되면 콜백)
    task_chord = chord(
        [
            create_diagram.s(document.result),
            create_erd.s(document.result),
            create_api.s(document.result),
        ]
    )(collect_results.s())

    try:
        final_result = task_chord.get(timeout = 120)

        try:
            redis_client.publish("task_updates", f"Document {document_id} 작업 완료")
        except Exception as e:
            print(f"Redis publish 실패: {str(e)}")

    except Exception as e:
        redis_client.publish("task_updates", f"Document {document_id} 작업 실패: {str(e)}")
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    document.diagram_code = final_result["diagram"]
    document.erd_code = final_result["erd"]
    document.api_code = final_result["api"]
    document.save()

    return Response({
        "status": "success",
        "data": final_result,
    }, status = status.HTTP_200_OK)

#----------------------------------------------------------

def call_deepseek_api(prompt):
    api_url = "https://api.deepseek.com/v1/chat/completions"
    api_key = settings.DEEPSEEK_API_KEY

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": False
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.post(api_url, json=payload, headers=headers)

    if response.status_code == 200:
        review_result = response.json()
        return review_result['choices'][0]['message']['content']
    else:
        error_msg = response.json().get("error", "Unknown error occurred.")
        raise Exception(f"DeepSeek API failed: {error_msg}")

# SSL 인증서 파일 경로 설정
os.environ["SSL_CERT_FILE"] = certifi.where()

#----------------------------------------------------------

@swagger_auto_schema(
    method='post',
    operation_summary="설계 파트 저장 API",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "parts": openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["diagram", "erd", "api"]  # 가능한 값 지정
                ),
                description="저장할 파트들 (diagram, erd, api 중 하나 이상)"
            ),
        },
        required=["parts"]  # parts는 필수 항목
    ),
    responses={
        200: openapi.Response(
            description="저장 성공",
            examples={
                "application/json": {
                    "status": "success",
                    "message": "diagram, erd 저장 완료"
                }
            }
        ),
        400: openapi.Response(
            description="잘못된 요청",
            examples={
                "application/json": {
                    "status": "error",
                    "message": "Invalid parts specified."
                }
            }
        ),
        404: openapi.Response(
            description="설계 문서가 없음",
            examples={
                "application/json": {
                    "status": "error",
                    "message": "설계 문서를 찾을 수 없습니다."
                }
            }
        ),
    }
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def save_document_part(request, document_id):
    try:
        document = Document.objects.get(id=document_id, user_id=request.user)
        parts = request.data.get("parts", [])  # ["diagram", "erd", "api"]

        # parts가 배열인지 확인
        if not isinstance(parts, list):
            return JsonResponse({
                "status": "error",
                "message": "parts는 리스트여야 합니다."
            }, status=400)

        valid_parts = {"diagram", "erd", "api"}
        invalid_parts = [part for part in parts if part not in valid_parts]

        # 유효하지 않은 값이 있으면 에러 반환
        if invalid_parts:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid parts specified: {', '.join(invalid_parts)}"
            }, status=400)

        # 각각의 파트를 저장
        if "diagram" in parts:
            document.is_diagram_saved = True
        if "erd" in parts:
            document.is_erd_saved = True
        if "api" in parts:
            document.is_api_saved = True

        document.save()

        return JsonResponse({
            "status": "success",
            "message": f"{', '.join(parts)} 저장 완료"
        }, status=200)

    except Document.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "설계 문서를 찾을 수 없습니다."
        }, status=404)

#----------------------------------------------------------

@api_view(['POST'])
def setup_project(request, document_id):
    """
    설계 문서를 기반으로 프로젝트를 초기 세팅하고 GitHub에 푸시합니다.
    """
    try:
        # 설계 문서 조회
        document = Document.objects.get(id=document_id)

        # 프로젝트 디렉터리 경로 설정
        project_dir = os.path.join(settings.BASE_DIR, "projects", document.title)

        # 초기 프로젝트 구조 생성
        generate_project_structure.delay(
            erd_code=document.erd_code,
            api_code=document.api_code,
            diagram_code=document.diagram_code,
            project_dir=project_dir
        ).get()

        # GitHub 레포지토리 생성 및 파일 푸시
        repo_url = push_to_github.delay(
            project_dir=project_dir,
            repo_name=document.title,
            user=document.user_id
        ).get()

        return Response({
            "status": "success",
            "repo_url": repo_url,
            "message": "프로젝트 초기 세팅 및 GitHub 푸시가 완료되었습니다."
        }, status=status.HTTP_201_CREATED)

    except Document.DoesNotExist:
        return Response({
            "status": "error",
            "message": "설계 문서를 찾을 수 없습니다."
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        return Response({
            "status": "error",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)