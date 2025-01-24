# Node.js 기반 이미지 사용
FROM node:16 AS build

# 작업 디렉터리 설정
WORKDIR /app

# package.json 및 package-lock.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 소스 코드 복사
COPY . .

# 프로젝트 빌드
RUN npm run build

# Nginx 기반 이미지 사용 (빌드 결과물을 서빙하기 위해)
FROM nginx:alpine

# 빌드 결과물을 Nginx의 기본 서빙 디렉터리로 복사
COPY --from=build /app/dist /usr/share/nginx/html

# 80 포트 노출
EXPOSE 80

# Nginx 실행
CMD ["nginx", "-g", "daemon off;"]