import os
import redis
import requests
import subprocess
import json
from openai import OpenAI
from celery import shared_task
from django.conf import settings
import openai

# Redis 클라이언트 생성
redis_client = redis.StrictRedis(host="redis", port=6379, decode_responses=True)

openai_api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

# DeepSeek API 설정
#api_key = os.environ.get("DEEPSEEK_API_KEY")
#api_url = os.environ.get("DEEPSEEK_API_URL")

def call_openai_api(prompt):
    try:
        # ChatGPT 모델 호출
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,  # 응답의 최대 토큰 수
        )
        print(response)

        # 응답에서 메시지 내용 추출
        message_content = response.choices[0].message.content
        
        return message_content

    except openai.OpenAIError as e:
        raise Exception(f"OpenAI API 호출 실패: {str(e)}")
    

# def call_deepseek_api(prompt):
#     payload = {
#         "model": "deepseek-chat",
#         "messages": [{"role": "user", "content": prompt}],
#         "stream": False
#     }

#     header = {
#         "Content-Type": "application/json",
#         "Authorization": "Bearer " + api_key
#     }

#     response = requests.post(api_url, json=payload, headers=header)

#     if response.status_code == 200:
#         result = response.json()
#         return result["choices"][0]["message"]["content"]
#     else:
#         error_msg = response.json().get("error", "Unknown error occurred.")
#         raise Exception(f"DeepSeek API 호출 실패: {error_msg}")

@shared_task
def create_diagram(data):
    """
    주어진 데이터를 기반으로 Mermaid 형식의 시퀀스 다이어그램을 생성합니다.
    """
    channel = "task_updates"
    redis_client.publish(channel, "create_diagram 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 상세한 시퀀스 다이어그램을 Mermaid 형식으로 코드를 생성해주세요. 다음 지시사항을 정확히 따라주세요:

        1. **참여자(Actors) 정의**
        - 시스템에 참여하는 모든 참여자(Actors)를 식별하고, 각 참여자의 이름을 명확히 정의하세요.
        - 참여자 이름은 간결하고 직관적으로 작성하세요. (예: "User", "OrderSystem", "PaymentGateway")
        - 참여자 이름 뒤에 불필요한 접미사(예: "_모듈")를 붙이지 마세요.
        - 참여자는 되도록 많이 정의하세요.
        - **User는 actor를 사용하여 사람 모형으로 정의해주세요**.

        2. **메시지(Message) 정의**
        - 참여자 간에 주고받는 모든 메시지를 명확히 정의하세요.
        - 각 메시지는 발신자와 수신자를 명시하고, 메시지의 목적을 간략히 설명하세요.
        - 메시지는 되도록 많이 정의하세요.
        - 메세지는 한글로 작성해주세요.

        3. **흐름(Flow) 정의**
        - 메시지의 순서와 흐름을 명확히 정의하세요.
        - 조건부 흐름(예: if-else)이 있다면, 이를 명시하세요.

        4. **루프(Loop) 및 대안(Alternative) 정의**
        - 반복되는 흐름(루프)이나 대안적인 흐름이 있다면, 이를 명시하세요.

        5. **출력 형식**
        - 최종 시퀀스 다이어그램은 Mermaid 형식으로만 출력하세요.
        - 다른 부가 설명 없이 **오직 Mermaid 코드만** 출력하세요.

        **주의사항**:
        - 출력은 반드시 Mermaid 코드만 포함해야 합니다.
        - 추가 설명, 주석, 또는 다른 텍스트는 절대 포함하지 마세요.
        - 참여자 이름은 간결하고 직관적으로 작성하며, 불필요한 접미사(예: "_모듈")를 붙이지 마세요.
    """
    try:
        # call_openai_api를 사용하여 다이어그램 코드 생성
        diagram_code = call_openai_api(prompt)
        
        redis_client.publish(channel, "create_diagram 작업 완료")
        return diagram_code

    except Exception as e:
        redis_client.publish(channel, f"create_diagram 작업 실패: {e}")
        raise Exception(f"Error generating sequence diagram: {e}")

# @shared_task
# def create_diagram(data):
#     channel = "task_updates"
#     redis_client.publish(channel, "create_diagram 작업 시작")

#     prompt = f"""
#         {data}를 사용하여 체계적이고 상세한 시퀀스 다이어그램을 Mermaid 형식으로 코드를 생성해주세요. 다음 지시사항을 정확히 따라주세요:

#         1. **참여자(Actors) 정의**
#         - 시스템에 참여하는 모든 참여자(Actors)를 식별하고, 각 참여자의 이름을 명확히 정의하세요.
#         - 참여자 이름은 간결하고 직관적으로 작성하세요. (예: "User", "OrderSystem", "PaymentGateway")
#         - 참여자 이름 뒤에 불필요한 접미사(예: "_모듈")를 붙이지 마세요.
#         - 참여자는 되도록 많이 정의하세요.

#         2. **메시지(Message) 정의**
#         - 참여자 간에 주고받는 모든 메시지를 명확히 정의하세요.
#         - 각 메시지는 발신자와 수신자를 명시하고, 메시지의 목적을 간략히 설명하세요.
#         - 메세지는 되도록 많이 정의하세요.

#         3. **흐름(Flow) 정의**
#         - 메시지의 순서와 흐름을 명확히 정의하세요.
#         - 조건부 흐름(예: if-else)이 있다면, 이를 명시하세요.

#         4. **루프(Loop) 및 대안(Alternative) 정의**
#         - 반복되는 흐름(루프)이나 대안적인 흐름이 있다면, 이를 명시하세요.

#         5. **출력 형식**
#         - 최종 시퀀스 다이어그램은 Mermaid 형식으로만 출력하세요.
#         - 다른 부가 설명 없이 **오직 Mermaid 코드만** 출력하세요.

#         **주의사항**:
#         - 출력은 반드시 Mermaid 코드만 포함해야 합니다.
#         - 추가 설명, 주석, 또는 다른 텍스트는 절대 포함하지 마세요.
#         - 참여자 이름은 간결하고 직관적으로 작성하며, 불필요한 접미사(예: "_모듈")를 붙이지 마세요.
#         """
#     try:
#         result = call_deepseek_api(prompt)
#         redis_client.publish(channel, "create_diagram 작업 완료")
#         return result
#     except Exception as e:
#         redis_client.publish(channel, f"create_diagram 작업 실패: {e}")
#         raise

@shared_task
def create_erd(data):
    channel = "task_updates"
    redis_client.publish(channel, "create_erd 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 ERD를 Mermaid 형식으로 코드를 생성해주세요.
        다음 지시사항을 정확히 따라주세요:

        1. **엔티티와 필드**
        - 엔티티 간의 관계를 명확히 정의하세요.
        - 관계의 카디널리티(1:1, 1:N, M:N)를 명시하세요.
        - 외래 키(FK)를 사용하여 관계를 표현하세요. 외래 키는 관련된 엔티티의 기본 키(PK)를 참조해야 합니다.
        - 외래 키 필드 이름은 `[참조된 엔티티 이름]_id` 형식으로 작성하세요. (예: `user_id: integer`)
        - 엔티티와 필드는 되도록 많이 작성해주세요.
        
        2. **관계**
        - 엔티티 간의 관계를 명확히 정의하세요.
        - 관계의 카디널리티(1:1, 1:N, M:N)를 명시하세요.
        - 외래 키를 사용할 경우, 필드 이름에 `_id`를 붙여 명시하세요. (예: `user_id: integer`)

        3. **출력 형식**
        - 출력은 Mermaid 형식으로만 제공하세요.
        - 다른 부가 설명 없이 **오직 Mermaid 코드만** 출력하세요.
        
        **주의사항**:
        - 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        - 출력은 반드시 Mermaid 코드만 포함해야 합니다.
        - 추가 설명, 주석, 또는 다른 텍스트는 절대 포함하지 마세요.
    """
    try:
        # call_openai_api 함수 호출하여 Mermaid 코드 생성
        diagram_code = call_openai_api(prompt)

        # 작업 완료 알림
        redis_client.publish(channel, "create_erd 작업 완료")
        
        return diagram_code

    except Exception as e:
        # 작업 실패 알림
        redis_client.publish(channel, f"create_erd 작업 실패: {e}")
        raise

# @shared_task
# def create_erd(data):
#     channel = "task_updates"
#     redis_client.publish(channel, "create_erd 작업 시작")

#     prompt = f"""
        
#         {data}를 사용하여 체계적이고 ERD를 Mermaid 형식으로 코드를 생성해주세요.
#         다음 지시사항을 정확히 따라주세요:

#         1. **엔티티와 필드**
#         - 엔티티 간의 관계를 명확히 정의하세요.
#         - 관계의 카디널리티(1:1, 1:N, M:N)를 명시하세요.
#         - 외래 키(FK)를 사용하여 관계를 표현하세요. 외래 키는 관련된 엔티티의 기본 키(PK)를 참조해야 합니다.
#         - 외래 키 필드 이름은 `[참조된 엔티티 이름]_id` 형식으로 작성하세요. (예: `user_id: integer`)
        
#         2. **관계**
#         - 엔티티 간의 관계를 명확히 정의하세요.
#         - 관계의 카디널리티(1:1, 1:N, M:N)를 명시하세요.
#         - 외래 키를 사용할 경우, 필드 이름에 `_id`를 붙여 명시하세요. (예: `user_id: integer`)

#         3. **출력 형식**
#         - 출력은 Mermaid 형식으로만 제공하세요.
#         - 다른 부가 설명은 생략하고, Mermaid 코드만 출력하세요.
        
#         4. **추가 요구사항**
#         - 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
#     """
#     try:
#         result = call_deepseek_api(prompt)
#         redis_client.publish(channel, "create_erd 작업 완료")
#         return result
#     except Exception as e:
#         redis_client.publish(channel, f"create_erd 작업 실패: {e}")
#         raise


@shared_task
def create_api(data):
    channel = "task_updates"
    redis_client.publish(channel, "create_api 작업 시작")

    prompt = f"""
        {data}를 사용하여 체계적이고 API 명세서를 swagger.json 코드로 생성해주세요.
        또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
        또한, API 엔드포인트는 각 기능을 담당하는 섹션별로 분리되어 있어야 하며, 기본적인 CRUD 작업을 포함하도록 해주세요.
        또한, 다른 부가설명말고 "swagger.json 코드만" 출력해주세요.
        
        **출력 형식**:
        - 출력은 반드시 유효한 JSON 형식이어야 합니다.
        - JSON은 Swagger UI에서 바로 사용할 수 있도록 완전한 `swagger.json` 스펙을 따라야 합니다.
        - Swagger코드 안 description 안에는 한글로 해주세요.
        - 다른 부가 설명 없이 **오직 JSON 코드만** 출력하세요.
        - JSON은 유효해야 하며, Swagger UI에서 바로 렌더링될 수 있어야 합니다.
    """
    try:
        # call_openai_api 함수 호출하여 Swagger JSON 코드 생성
        swagger_json_code = call_openai_api(prompt)

        # 작업 완료 알림
        redis_client.publish(channel, "create_api 작업 완료")
        
        return swagger_json_code

    except Exception as e:
        # 작업 실패 알림
        redis_client.publish(channel, f"create_api 작업 실패: {e}")
        raise


# @shared_task
# def create_api(data):
#     channel = "task_updates"
#     redis_client.publish(channel, "create_api 작업 시작")

#     prompt = f"""
#         {data}를 사용하여 체계적이고 API 명세서를 swagger.json 코드로 생성해주세요.
#         또한, 실제 환경에서 바로 사용할 수 있도록 체계적으로 고도화 및 모듈화를 해주세요.
#         또한, 기본적인 crud를 포함해주세요.
#         또한, 다른 부가설명말고 "swagger.json 코드만" 출력해주세요.
        
#         **출력 형식**:
#         - 출력은 반드시 유효한 JSON 형식이어야 합니다.
#         - JSON은 Swagger UI에서 바로 사용할 수 있도록 완전한 `swagger.json` 스펙을 따라야 합니다.
#         - 다른 부가 설명 없이 **오직 JSON 코드만** 출력하세요.
#         - JSON은 유효해야 하며, Swagger UI에서 바로 렌더링될 수 있어야 합니다.
        
        
#     """
#     try:
#         result = call_deepseek_api(prompt)
#         redis_client.publish(channel, "create_api 작업 완료")
#         return result
#     except Exception as e:
#         redis_client.publish(channel, f"create_api 작업 실패: {e}")
#         raise

@shared_task
def collect_results(results):
    return {
        "diagram": results[0],
        "erd": results[1],
        "api": results[2],
    }