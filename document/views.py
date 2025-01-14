import json
import os
import certifi
from celery import chord

from django.http import JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .tasks import create_diagram, collect_results, create_erd, create_api, redis_client

import document
from document.models import Document
from document.serializers import CreateDocumentSerializer

# Create your views here.
client = OpenAI(api_key=os.environ.get("DEEPSEEK_API_KEY"), base_url=os.environ.get("DEEPSEEK_API_URL"))
@swagger_auto_schema(
    method = 'post',
    operation_summary = '문서 생성 API',
    request_body = CreateDocumentSerializer
)
@api_view(["POST"])
def create_document(request):

    serializer = CreateDocumentSerializer(data=request.data)

    if serializer.is_valid():
        try:
            title = serializer.validated_data.get("title")
            content = serializer.validated_data.get("content")
            requirements = serializer.validated_data.get("requirements", "No requirements provided")

            prompt = f"""
                        Title: {title}
                        Content: {content}
                        requirements: {requirements}

                        위 내용을 가지고 쳬계적인 문서화를 만들어주세요.
                        방식은 
                        Title: {title}
                        Content: {content}
                        requirements: {requirements} 형식으로 체계적으로 다시 문서화 해주세요.
                        """

            messages = [{"role": "user", "content": prompt}]
            response = client.chat.completions.create(
                model = "deepseek-chat",
                messages = messages)

            result = response.choices[0].message.content

            document = Document.objects.create(
                title = title,
                content = content,
                requirements = requirements,
                result = result)

            return JsonResponse({
                "status": "success",
                "data": {
                    "id": document.id,
                    "response": result
                }},
                status = status.HTTP_200_OK)

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)},
                status = status.HTTP_500_INTERNAL_SERVER_ERROR)

    else:
        return JsonResponse({
            "status": "error",
            "errors": serializer.errors},
            status = status.HTTP_400_BAD_REQUEST)


@swagger_auto_schema(
    method='post',
    operation_summary="문서 수정 API",
    manual_parameters=[
        openapi.Parameter(
            'document_id',
            openapi.IN_PATH,
            description="수정할 문서의 ID",
            type=openapi.TYPE_STRING,
            required=True,
        ),
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'prompt': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="추가 요청 내용을 포함한 프롬프트"
            ),
        },
        required=['prompt']
    ),
    responses={
        200: openapi.Response(
            description="문서 수정 성공",
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
def update_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "해당 문서를 찾을 수 없습니다."
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        body = json.loads(request.body)
        prompt_input = body.get("prompt")

        if not prompt_input:
            return JsonResponse({
                "status": "error",
                "message": "prompt 필드는 필수입니다."
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": "유효하지 않는 JSON 형식입니다."
        }, status=status.HTTP_400_BAD_REQUEST)

    prompt = f"""

        기존 문서:
            Title: {document.title}
            Content: {document.content}
            requirements: {document.requirements}

            추가 요청:
                {prompt_input}
            위 내용을 기반으로 업데이트된 문서화 결과를 생성해주세요.    
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}])

        result = response.choices[0].message.content

        document.result = result
        document.save()

        return JsonResponse({
            "status": "success",
            "data": {
                "id": document.id,
                "response": document.result
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"AI 호출 실패: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@swagger_auto_schema(
    method = 'get',
    operation_summary = "문서 조회 API",
    manual_parameters = [
        openapi.Parameter(
            'document_id',
            openapi.IN_PATH,
            description = "조회할 문서의 ID",
            type = openapi.TYPE_STRING,
            required = True,
        ),
    ],
    responses = {
        200: openapi.Response(
            description="문서 조회 성공",
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
@api_view(["GET"])
def search_document(request, document_id):
    try:
        document = Document.objects.get(id = document_id)

    except Document.DoesNotExist:
        return JsonResponse(
            {
            "status": "error",
            "message": "해당 문서를 찾을 수 없습니다."
            }, status=status.HTTP_404_NOT_FOUND
        )

    try:
        return JsonResponse(
            {
                "status": "success",
                "id": document.id,
                "response": document.result,
            }, status = status.HTTP_200_OK
        )

    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status = status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
def dev_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id)

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
        redis_client.publish("task_updetes", f"Document {document_id} 작업 완료")

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


# SSL 인증서 파일 경로 설정
os.environ["SSL_CERT_FILE"] = certifi.where()