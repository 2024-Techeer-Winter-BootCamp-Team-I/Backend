import os
import redis
import requests
import subprocess
import json
from openai import OpenAI
from celery import shared_task
from django.conf import settings

# Redis 클라이언트 생성
redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=True)

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

    response = requests.post(api_url, json=payload, headers=header)

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
        {data}를 사용하여 체계적이고 상세한 시퀀스 다이어그램을 Mermaid 형식으로 코드를 생성해주세요. 다음 지시사항을 정확히 따라주세요:

        1. **참여자(Actors) 정의**
        - 시스템에 참여하는 모든 참여자(Actors)를 식별하고, 각 참여자의 이름을 명확히 정의하세요.
        - 참여자는 시스템의 주요 구성 요소 또는 사용자일 수 있습니다.

        2. **메시지(Message) 정의**
        - 참여자 간에 주고받는 모든 메시지를 명확히 정의하세요.
        - 각 메시지는 발신자와 수신자를 명시하고, 메시지의 목적을 간략히 설명하세요.

        3. **흐름(Flow) 정의**
        - 메시지의 순서와 흐름을 명확히 정의하세요.
        - 조건부 흐름(예: if-else)이 있다면, 이를 명시하세요.

        4. **루프(Loop) 및 대안(Alternative) 정의**
        - 반복되는 흐름(루프)이나 대안적인 흐름이 있다면, 이를 명시하세요.

        5. **모듈화**
        - 다이어그램을 모듈화하여 각 부분이 독립적으로 이해될 수 있도록 구성하세요.

        6. **출력 형식**
        - 최종 시퀀스 다이어그램은 Mermaid 형식으로만 출력하세요.
        - 다른 부가 설명 없이 **오직 Mermaid 코드만** 출력하세요.

        **주의사항**:
        - 출력은 반드시 Mermaid 코드만 포함해야 합니다.
        - 추가 설명, 주석, 또는 다른 텍스트는 절대 포함하지 마세요.
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
    redis_client.publish(channel, "create_erd 작업 시작")

    prompt = f"""
        
        {data}를 사용하여 체계적이고 ERD를 Mermaid 형식으로 코드를 생성해주세요.
        다음 지시사항을 정확히 따라주세요:

        1. **엔티티와 필드**
        - 각 엔티티의 이름과 필드(속성)를 명시하세요.
        - 필드는 데이터 타입과 함께 작성하세요. (예: `id: integer`, `name: string`)
        - **외래 키(FK)는 관계가 명확히 정의되어야 할 때만 사용하세요.** 필요하지 않은 경우 생략하세요.

        2. **관계**
        - 엔티티 간의 관계를 명확히 정의하세요.
        - 관계의 카디널리티(1:1, 1:N, M:N)를 명시하세요.
        - 외래 키를 사용할 경우, 필드 이름에 `_id`를 붙여 명시하세요. (예: `user_id: integer`)

        3. **출력 형식**
        - 출력은 Mermaid 형식으로만 제공하세요.
        - 다른 부가 설명은 생략하고, Mermaid 코드만 출력하세요.
        
        4. **추가 요구사항**
        - 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
    """
    try:
        result = call_deepseek_api(prompt)
        redis_client.publish(channel, "create_erd 작업 완료")
        return result
    except Exception as e:
        redis_client.publish(channel, f"create_erd 작업 실패: {e}")
        raise

@shared_task
def create_api(data):
    channel = "task_updates"
    redis_client.publish(channel, "create_api 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 API 명세서를 swagger.json 코드로 생성해주세요.
        또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        또한, 다른 부가설명말고 "swagger.json 코드만" 출력해주세요.
    """
    try:
        result = call_deepseek_api(prompt)
        redis_client.publish(channel, "create_api 작업 완료")
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