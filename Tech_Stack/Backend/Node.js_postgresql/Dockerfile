FROM node:18

WORKDIR /app

# 패키지 설치를 위해 package.json 및 package-lock.json 복사
COPY package.json package-lock.json ./

# 필요한 패키지 설치
RUN npm install

# 소스 코드 복사
COPY . .

# 환경 변수 설정 (PostgreSQL)
ENV DB_HOST=db
ENV DB_PORT=5432
ENV DB_USER=myuser
ENV DB_PASSWORD=mypassword
ENV DB_NAME=mydatabase

# 애플리케이션 실행
CMD ["npm", "start"]