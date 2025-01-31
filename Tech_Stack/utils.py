# import os

# def find_matching_template(tech_stack_name, project_type):
#     """
#     사용자가 입력한 기술 스택을 기반으로 적절한 템플릿을 찾습니다.
#     """
#     if project_type == 'frontend':
#         templates = [
#             "react-js-npm-vite",
#             "react-js-npm-webpack",
#             "react-ts-npm-vite",
#             "react-ts-npm-webpack",
#             "react-js-yarn-vite",
#             "react-js-yarn-webpack",
#             "react-ts-yarn-vite",
#             "react-ts-yarn-webpack",
#         ]
#     elif project_type == 'backend':
#         templates = [
#             "Django_postgresql",
#             "Django_mysql",
#             "Django_sqlite3",
#             "Node.js_postgresql",
#             "Node.js_mysql",
#         ]

#     # 기술 스택을 소문자로 변환
#     tech_stack_name = [tech.lower() for tech in tech_stack_name]

#     # 동의어 사전 
#     synonym_dict = {
#         "javascript": "js",
#         "typescript": "ts",
#         "nodejs": "node.js",
#     }

#     # 동의어 변환
#     tech_stack_name = [synonym_dict.get(tech, tech) for tech in tech_stack_name]

#     for template in templates:
#         template_lower = template.lower()
#         if all(tech in template_lower for tech in tech_stack_name):
#             return os.path.join("Tech_Stack", project_type.capitalize(), template)

#     return None
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
            "Django_sqlite3",
            "Node.js_postgresql",
            "Node.js_mysql",
        ]

    # 기술 스택을 소문자로 변환
    tech_stack_name = [tech.lower() for tech in tech_stack_name]

    # 동의어 사전
    synonym_dict = {
        "javascript": "js",
        "typescript": "ts",
        "nodejs": "node.js",
    }

    # 동의어 변환
    tech_stack_name = [synonym_dict.get(tech, tech) for tech in tech_stack_name]

    for template in templates:
        template_lower = template.lower()
        # 템플릿 이름을 소문자로 변환하고, 기술 스택이 모두 포함되어 있는지 확인
        if all(tech in template_lower for tech in tech_stack_name):
            return os.path.join("Tech_Stack", project_type.capitalize(), template)

    return None