pipeline {
    agent any

    environment {
        backend_repository = "sensesis/devsketch-backend1" // Docker Hub ID와 repository 이름
        DOCKERHUB_CREDENTIALS = credentials('docker-hub') // Jenkins에 등록해 놓은 Docker Hub credentials 이름
        IMAGE_TAG = "" // Docker image tag
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
        ENV_FILE = 'env-file'
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs() // 워크스페이스 청소
                git branch: 'develop', url: 'https://github.com/2024-Techeer-Winter-BootCamp-Team-I/Backend.git'
            }
        }

        stage('Copy .env') {
            steps {
                withCredentials([file(credentialsId: "${ENV_FILE}", variable: 'ENV_FILE_PATH')]) {
                    sh 'cp $ENV_FILE_PATH .env'
                    sh 'ls -la ${WORKSPACE}'
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    sh "docker --version"
                    sh "docker compose --version"
                }
            }
        }

        stage('Set Image Tag') {
            steps {
                script {
                    // Set image tag based on branch name
                    if (env.BRANCH_NAME == 'develop') {
                        IMAGE_TAG = "1.0.${BUILD_NUMBER}"
                    } else {
                        IMAGE_TAG = "0.0.${BUILD_NUMBER}"
                    }
                    echo "Image tag set to: ${IMAGE_TAG}"
                }
            }
        }

        stage('Building our image') {
            steps {
                script {
                    sh "docker build --memory=2g -t ${backend_repository}:${IMAGE_TAG} -f Dockerfile-dev ." // 메모리 사용을 2GB로 제한
                }
                slackSend message: "Build Started - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
            }
        }

        stage('Login'){
            steps{
                sh "echo ${DOCKERHUB_CREDENTIALS_PSW} | docker login -u $DOCKERHUB_CREDENTIALS_USR --password-stdin" // docker hub 로그인
            }
        }

        stage('Deploy our image') {
            steps {
                script {
                    sh "docker push ${backend_repository}:${IMAGE_TAG}" // docker push
                }
            }
        }

        stage('Cleaning up') {
            steps {
                sh "docker rmi ${backend_repository}:${IMAGE_TAG}" // docker image 제거
            }
        }
    }

    post {
        success {
            echo 'Build and deployment successful!'
            slackSend message: "Build deployed successfully - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        failure {
            echo 'Build or deployment failed.'
            slackSend failOnError: true, message: "Build failed  - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
    }
}