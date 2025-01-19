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

                            위 내용을 가지고 체계적인 문서화를 만들어주세요.
                            방식은 
                            Title: {title}
                            Content: {content}
                            Requirements: {requirements} 형식으로 체계적으로 다시 문서화 해주세요.

                            1.해당 기능명세에 부가적인 설명도 짧게추가해주세요. 
                            2.실제 현업자가 바로 사용할 수 있도록 쳬계적인 기능명세를 만들어주세요. 그리고 빠른 프롬프트를 위해 문서를 모듈화 해주세요.
                            3.바로 제출할 수 있도록 실제 문서 내용"만" 출력해주세요.
                        """

                review_result = call_deepseek_api(prompt)
                def event_stream():
                    try:
                        yield f"data: Review start.\n\n"
                        time.sleep(1)

                        for char in review_result:
                            yield f"data: {char}\n\n"
                            time.sleep(0)

                        yield f"data: Review completed.\n\n"
                    except Exception as e:
                        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

                document = Document.objects.create(
                    user_id=user,
                    title=title,
                    content=content,
                    requirements=requirements,
                    result=review_result
                )
                
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

                return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

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
                    yield f"data: Review start.\n\n"
                    time.sleep(1)

                    for char in review_result:
                        yield f"data: {char}\n\n"
                        time.sleep(0)

                    yield f"data: Review completed.\n\n"
                except Exception as e:
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"

            return StreamingHttpResponse(event_stream(), content_type="text/event-stream")

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

@swagger_auto_schema(
    method = 'post',
    operation_summary = "설계 생성 API",
    manual_parameters = [
        openapi.Parameter(
            'document_id',
            openapi.IN_PATH,
            description = "생성할 문서의 ID",
            type = openapi.TYPE_STRING,
            required = True,
        ),
    ],
    responses = {
        200: openapi.Response(
            description="문서 생성 성공",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                    "data": openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="문서 ID"),
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
            "message": "해당 문서를 찾을 수 없습니다."
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