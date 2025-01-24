# Node.js 기반 이미지 사용
FROM node:16

# 작업 디렉터리 설정
WORKDIR /app

# package.json 및 package-lock.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 소스 코드 복사
COPY . .

# 3000 포트 노출
EXPOSE 3000

# 개발 서버 실행
CMD ["npm", "start"]