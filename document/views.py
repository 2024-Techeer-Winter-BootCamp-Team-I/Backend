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
                        Description: {requirements}

                        위 내용을 가지고 쳬계적인 문서화를 만들어주세요.
                        방식은 
                        Title: {title}
                        Content: {content}
                        Description: {requirements} 형식으로 체계적으로 다시 문서화 해주세요.
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



