pipeline {
    agent any

    environment {
        backend_repository = "sensesis/devsketch-backend" // Docker Hub ID와 repository 이름
        DOCKERHUB_CREDENTIALS = credentials('docker-hub') // Jenkins에 등록해 놓은 Docker Hub credentials 이름
        DOCKER_COMPOSE_FILE = 'docker-compose.yml'
        ENV_FILE = 'env-file'
    }

    stages {
        stage('Checkout') {
            steps {
                cleanWs() // 워크스페이스 청소
                checkout scm
            }
        }

        stage('Copy .env') {
            steps {
                withCredentials([file(credentialsId: ENV_FILE, variable: 'ENV_FILE_PATH')]) {
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
                    // 현재 브랜치 이름 출력 (디버깅용)
                    echo "Branch name: ${env.BRANCH_NAME}"

                    // Set image tag based on branch name
                    if (env.BRANCH_NAME == 'develop') {
                        env.IMAGE_TAG = "1.0.${BUILD_NUMBER}"
                    } else {
                        env.IMAGE_TAG = "0.0.${BUILD_NUMBER}"
                    }
                    echo "Image tag set to: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Building our image') {
            steps {
                script {
                    sh "docker build --memory=2g -t ${backend_repository}:${env.IMAGE_TAG} -f Dockerfile-dev ." // 메모리 사용을 2GB로 제한
                }
                slackSend message: "Build Started - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
            }
        }

        stage('Login') {
            steps {
                script {
                    docker.withRegistry('https://registry.hub.docker.com', 'docker-hub') {
                        // Docker Hub에 로그인됨
                        // 이후 docker 명령어는 인증된 상태에서 실행됨
                    }
                }
            }
        }

        stage('Deploy our image') {
            steps {
                script {
                    sh "docker push ${backend_repository}:${env.IMAGE_TAG}" // docker push
                }
            }
        }

        stage('Cleaning up') {
            steps {
                sh "docker rmi ${backend_repository}:${env.IMAGE_TAG}" // docker image 제거
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
