import os

def find_matching_template(tech_stack_name, project_type):
    """
    사용자가 입력한 기술 스택을 기반으로 적절한 템플릿을 찾습니다.
    """
    if project_type == 'frontend':
        templates = [
            "react-js-npm-vite",
            "react-js-npm-webpack",
            "react-ts-npm-vite",
            "react-ts-npm-webpack",
            "react-js-yarn-vite",
            "react-js-yarn-webpack",
            "react-ts-yarn-vite",
            "react-ts-yarn-webpack",
        ]
    elif project_type == 'backend':
        templates = [
            "Django_postgresql",
            "Django_mysql",
            "Node.js_postgresql",
            "Node.js_mysql",
        ]

    # 기술 스택을 소문자로 변환하여 비교
    tech_stack_name = [tech.lower() for tech in tech_stack_name]
    for template in templates:
        template_lower = template.lower()
        if all(tech in template_lower for tech in tech_stack_name):
            return os.path.join("Tech_Stack", project_type.capitalize(), template)

    return None