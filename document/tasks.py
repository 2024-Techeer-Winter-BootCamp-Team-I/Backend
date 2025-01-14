import os

import redis
from openai import OpenAI
from celery import shared_task

#Redis 클라이언트 생성
redis_client = redis.StrictRedis(host = "redis", port = 6379, decode_responses = True)

# DeepSeek API 설정
api_key = os.environ.get("DEEPSEEK_API_KEY")
base_url = os.environ.get("DEEPSEEK_API_URL")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=api_key, base_url=base_url)

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
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
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
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
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
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content
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
