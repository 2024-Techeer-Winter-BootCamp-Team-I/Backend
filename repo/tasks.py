from celery import shared_task
import shutil
import os
from git import Repo, GitCommandError
import logging
from github import Github, GithubException

logger = logging.getLogger(__name__)

@shared_task
def copy_and_push_to_github(project_dir, frontend_template_dir, backend_template_dir, repo_name, username, email, access_token, organization_name=None, private=False):
    """
    파일 복사 및 GitHub 레포지토리 생성 및 푸시를 수행하는 Celery 태스크
    """
    try:
        # 디렉터리 생성 (이미 존재하는 경우 무시)
        os.makedirs(project_dir, exist_ok=True)

        # 프론트엔드 템플릿 복사
        if frontend_template_dir and os.path.exists(frontend_template_dir):
            logger.info(f"프론트엔드 템플릿 복사: {frontend_template_dir} -> {project_dir}")
            shutil.copytree(frontend_template_dir, os.path.join(project_dir, "frontend"), dirs_exist_ok=True)
        else:
            logger.warning(f"프론트엔드 템플릿 디렉터리가 존재하지 않습니다: {frontend_template_dir}")

        # 백엔드 템플릿 복사
        if backend_template_dir and os.path.exists(backend_template_dir):
            logger.info(f"백엔드 템플릿 복사: {backend_template_dir} -> {project_dir}")
            shutil.copytree(backend_template_dir, os.path.join(project_dir, "backend"), dirs_exist_ok=True)
        else:
            logger.warning(f"백엔드 템플릿 디렉터리가 존재하지 않습니다: {backend_template_dir}")

        # GitHub API 클라이언트 초기화
        g = Github(access_token)

        # 레포지토리 생성
        if organization_name:
            org = g.get_organization(organization_name)
            repo = org.create_repo(repo_name, private=private)
        else:
            github_user = g.get_user()
            repo = github_user.create_repo(repo_name, private=private)

        # Git 저장소 초기화
        local_repo = Repo.init(project_dir)
        with local_repo.config_writer() as git_config:
            git_config.set_value("user", "name", username)
            git_config.set_value("user", "email", email)

        # 파일 추가 및 커밋
        local_repo.git.add(A=True)
        try:
            local_repo.git.commit(m="Initial commit")
        except GitCommandError as e:
            if "nothing to commit" in str(e):
                logger.info("변경 사항이 없어 커밋을 건너뜁니다.")
            else:
                raise e

        # main 브랜치 생성 및 체크아웃
        if 'main' not in local_repo.heads:
            local_repo.git.branch('main')
        local_repo.git.checkout('main')

        # 원격 저장소 설정
        remote_url = f"https://{access_token}@github.com/{username}/{repo.name}.git"
        if 'origin' not in local_repo.remotes:
            origin = local_repo.create_remote('origin', remote_url)
        else:
            origin = local_repo.remotes.origin
            origin.set_url(remote_url)

        # 푸시
        origin.push(refspec='main:main', force=True)
        logger.info("파일 푸시 완료")

        return repo.html_url

    except Exception as e:
        logger.error(f"파일 복사 및 푸시 중 오류 발생: {str(e)}", exc_info=True)
        raise e