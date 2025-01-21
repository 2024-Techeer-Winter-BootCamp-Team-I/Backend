pipeline {
    agent any

    environment {
        backend_repository = "sensesis/devsketch-backend1" // Docker Hub ID와 repository 이름
        DOCKERHUB_CREDENTIALS = credentials('docker-hub') // Jenkins에 등록된 Docker Hub credentials
        IMAGE_TAG = "" // Docker image tag
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
        ENV_FILE = 'env-file'
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs() // 워크스페이스 청소
                // 브랜치를 동적으로 체크아웃
                git branch: env.BRANCH_NAME ?: 'develop', url: 'https://github.com/2024-Techeer-Winter-BootCamp-Team-I/Backend.git'
            }
        }

        stage('Copy .env') {
            steps {
                withCredentials([file(credentialsId: "${ENV_FILE}", variable: 'ENV_FILE_PATH')]) {
                    sh 'cp $ENV_FILE_PATH .env'
                    sh 'ls -la ${WORKSPACE}' // .env 파일 복사 후 디렉터리 확인
                }
            }
        }

        stage('Verify Docker Setup') {
            steps {
                script {
                    // Docker와 Docker Compose가 정상적으로 동작하는지 확인
                    sh "docker --version"
                    sh "docker compose --version"
                }
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    // 브랜치 이름에 따라 이미지 태그 설정
                    IMAGE_TAG = env.BRANCH_NAME == 'develop' ? "1.0.${BUILD_NUMBER}" : "0.0.${BUILD_NUMBER}"
                    echo "Image tag set to: ${IMAGE_TAG}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    // Docker 이미지 빌드
                    sh "docker build --memory=2g -t ${backend_repository}:${IMAGE_TAG} -f Dockerfile-dev ."
                }
            }
        }

        stage('Login to Docker Hub') {
            steps {
                script {
                    // Docker Hub 로그인
                    sh "echo ${DOCKERHUB_CREDENTIALS_PSW} | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin"
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    // Docker 이미지 푸시
                    sh "docker push ${backend_repository}:${IMAGE_TAG}"
                }
            }
        }

        stage('Clean Up Docker Images') {
            steps {
                script {
                    // 로컬 Docker 이미지 정리
                    sh "docker rmi ${backend_repository}:${IMAGE_TAG}"
                }
            }
        }
    }

    post {
        always {
            echo 'Build process completed.'
        }
        success {
            echo 'Build and deployment successful!'
        }
        failure {
            echo 'Build or deployment failed.'
        }
    }
}
