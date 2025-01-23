# Generated Django Views from API
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def generate_image(request):
    if request.method == "POST":
        data = json.loads(request.body)
        prompt = data.get("text")
        return JsonResponse({"image_url": "http://example.com/generated-image.png"})
    return JsonResponse({"error": "Invalid request method"}, status=400)

@csrf_exempt
def send_mms(request):
    if request.method == "POST":
        image = request.FILES.get("image")
        phone_number = request.POST.get("phoneNumber")
        return JsonResponse({"status": "?? ??"})
    return JsonResponse({"error": "Invalid request method"}, status=400)