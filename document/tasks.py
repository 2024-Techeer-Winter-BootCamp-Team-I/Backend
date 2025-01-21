import os

import redis
import requests
from celery import shared_task

#Redis 클라이언트 생성
redis_client = redis.StrictRedis(host = "redis", port = 6379, decode_responses = True)

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

    response = requests.post(api_url, json = payload, headers = header)

    if response.status_code == 200:
        result = response.json()
        return result["choices"][0]["message"]["content"]

    else:
        error_msg = response.json().get("error", "Unknown error occurred.")
        raise Exception(f"DeepSeek API 호출 실패: {error_msg}")

@shared_task
def create_diagram(data):

    channel = "task_updates"
    redis_client.publish(channel, "create_diagram 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 시퀀스 다이어그램을 mermaid형식으로 코드를 생성해주세요.
        또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        또한, 다른 부가설명말고 "mermaid 코드만" 출력해주세요.
    """
    try:
        result = call_deepseek_api(prompt)
        redis_client.publish(channel, "create_diagram 작업 완료")
        return result

    except Exception as e:
        redis_client.publish(channel, f"create_diagram 작업 실패: {e}")
        raise


@shared_task
def create_erd(data):

    channel = "task_updates"
    redis_client.publish(channel, "create_diagram 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 ERD를 mermaid형식으로 코드를 생성해주세요.
        또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        또한, 다른 부가설명말고 "mermaid 코드만" 출력해주세요.
    """
    try:
        result = call_deepseek_api(prompt)
        redis_client.publish(channel, "create_diagram 작업 완료")
        return result

    except Exception as e:
        redis_client.publish(channel, f"create_erd 작업 실패: {e}")
        raise


@shared_task
def create_api(data):

    channel = "task_updates"
    redis_client.publish(channel, "create_diagram 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 API 명세서를 swagger.json 코드로 생성해주세요.
        또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        또한, 다른 부가설명말고 "swagger.json 코드만" 출력해주세요.
    """
    try:
        result = call_deepseek_api(prompt)
        redis_client.publish(channel, "create_diagram 작업 완료")
        return result

    except Exception as e:
        redis_client.publish(channel, f"create_api 작업 실패: {e}")
        raise


@shared_task
def collect_results(results):

    return {
        "diagram": results[0],
        "erd": results[1],
        "api": results[2],
    }


