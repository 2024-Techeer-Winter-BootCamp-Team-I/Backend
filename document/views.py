import json
import os

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view

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
@csrf_exempt
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
@csrf_exempt
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
    method='post',
    operation_summary="설계 생성 API",
    manual_parameters=[
        openapi.Parameter(
            'document_id',
            openapi.IN_PATH,
            description="생성할 문서의 ID",
            type=openapi.TYPE_STRING,
            required=True,
        ),
    ],
    responses={
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
@csrf_exempt
def dev_document(request, document_id):
    try:
        document = Document.objects.get(id=document_id)

    except Document.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "해당 문서를 찾을 수 없습니다."
        }, status=status.HTTP_404_NOT_FOUND)

    diagram_prompt = f"""
    {document.result}를 사용하여 체계적이고 시퀀스 다이어그램을 mermaid형식으로 코드를 생성해주세요.
    또한, 실제 환경에서 바로 사용할 수 있도록 쳬계적으로 고도화 및 모듈화를 해주세요.
    """

    erd_prompt = f"""
    {document.result}를 사용하여 체계적이고 erd를 mermaid형식으로 코드를 생성해주세요.
    또한, 실제 환경에서 바로 사용할 수 있도록 쳬계적으로 고도화 및 모듈화를 해주세요.
    """

    api_prompt = f"""
    {document.result}를 사용하여 체계적이고 api명세서를 swagger.json 코드로 생성해주세요.
    또한, 실제 환경에서 바로 사용할 수 있도록 쳬계적으로 고도화 및 모듈화를 해주세요.
    """

    try:
        diagram_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": diagram_prompt}]
        )

        erd_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": erd_prompt}]
        )

        api_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": api_prompt}]
        )

    except Exception:
        return JsonResponse({
            "status": "error",
            "message": "AI API와의 통신에 실패했습니다. 다시 시도해주세요."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        diagram_result = diagram_response.choices[0].message.content
        erd_result = erd_response.choices[0].message.content
        api_result = api_response.choices[0].message.content

    except (KeyError, IndexError):
        return JsonResponse({
            "status": "error",
            "message": "AI 응답 처리에 실패했습니다. 다시 시도해주세요."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        document.diagram_code = diagram_result
        document.erd_code = erd_result
        document.api_code = api_result

        document.save()

    except Exception:
        return JsonResponse({
            "status": "error",
            "message": "문서 저장 중 문제가 발생했습니다. 다시 시도해주세요."
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JsonResponse({
        "status": "success",
        "data": {
            "id": document.id,
            "diagram-code": diagram_result,
            "erd-code": erd_result,
            "api-code": api_result,
        }},
        status=status.HTTP_200_OK
    )








