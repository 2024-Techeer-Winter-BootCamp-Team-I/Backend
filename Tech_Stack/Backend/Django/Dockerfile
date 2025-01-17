# 베이스 이미지 설정
FROM python:3.10-slim

# 작업 디렉토리 생성
WORKDIR /app

# 요구 사항 파일 복사 및 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 소스 코드 복사
COPY . /app/

# Django 서버 실행 포트
EXPOSE 8000

# 명령어 실행
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]