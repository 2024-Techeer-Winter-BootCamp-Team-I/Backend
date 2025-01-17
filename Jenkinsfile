pipeline {
    agent any

    environment {
        repository = "sensesis/devsketch-backend1"  //docker hub id와 repository 이름
        DOCKERHUB_CREDENTIALS = credentials('docker-hub') // jenkins에 등록해 놓은 docker hub credentials 이름
        IMAGE_TAG = "" // docker image tag
    }

    stages {
        stage('Checkout') {
            steps {
		            cleanWs() //워크스페이스 청소
                git branch: 'develop', url: "https://github.com/2024-Techeer-Winter-BootCamp-Team-I/Backend.git"
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
                    sh "docker build -t ${repository}:${IMAGE_TAG} ." // docker build
                }
                //slackSend message: "Build Started - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
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
                    sh "docker push ${repository}:${IMAGE_TAG}" // docker push
                }
            }
        }

        stage('Cleaning up') {
            steps {
                sh "docker rmi ${repository}:${IMAGE_TAG}" // docker image 제거
            }
        }
    }

    post {
        success {
            echo 'Build and deployment successful!'
            //slackSend message: "Build deployed successfully - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
        failure {
            echo 'Build or deployment failed.'
            //slackSend failOnError: true, message: "Build failed  - ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)"
        }
    }
}
