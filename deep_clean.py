import os
import re

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return
        
    original = content
    
    # 1. Remove user_id from method signatures
    content = re.sub(r',\s*user_id:\s*uuid\.UUID', '', content)
    content = re.sub(r'user_id:\s*uuid\.UUID,\s*', '', content)
    content = re.sub(r'user_id:\s*uuid\.UUID', '', content)
    
    # 2. Remove user_id=user_id
    content = re.sub(r',\s*user_id=user_id', '', content)
    content = re.sub(r'user_id=user_id,\s*', '', content)
    content = re.sub(r'user_id=user_id', '', content)
    
    # 3. Remove current_user.id arguments
    content = re.sub(r',\s*current_user\.id', '', content)
    content = re.sub(r'current_user\.id,\s*', '', content)
    content = re.sub(r'current_user\.id', '', content)
    
    # 4. Remove ownership checks
    content = re.sub(r'if not resume or resume\.user_id != user_id:', 'if not resume:', content)
    content = re.sub(r'if not resume or resume\.user_id != current_user\.id:', 'if not resume:', content)
    
    # 5. Remove user_id from docstrings
    content = re.sub(r'\s*user_id: Authenticated user.*?UUID\.\n', '\n', content)
    content = re.sub(r'\s*user_id: UUID of the authenticated user\.\n', '\n', content)
    
    # 6. Remove specific JD router logger lines
    content = re.sub(r'f"for user \{current_user\.id\} — id=\{jd\.id\}"', 'f"id={jd.id}"', content)
    content = re.sub(r'jds = await jd_repo\.get_by_user\(current_user\.id\)', 'jds = await jd_repo.get_all()', content)
    
    # 7. Remove history router user_resumes
    content = re.sub(r'user_resumes = await resume_repo\.get_by_user\(current_user\.id\)', 'user_resumes = await resume_repo.get_all()', content)
    
    # 8. Remove any lingering auth imports again
    content = re.sub(r'from app\.services\.auth_service import get_current_active_user\n', '', content)
    content = re.sub(r'from app\.models\.user import User\n', '', content)
    content = re.sub(r',\s*current_user:\s*User\s*=\s*Depends\(get_current_active_user\)', '', content)
    content = re.sub(r'current_user:\s*User\s*=\s*Depends\(get_current_active_user\),\s*', '', content)
    
    # Fix f-string in orchestrator
    content = re.sub(r'f"resume=\{resume_id\}, user=\{user_id\}"', 'f"resume={resume_id}"', content)
    
    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk('app'):
    for file in files:
        if file.endswith('.py'):
            process_file(os.path.join(root, file))

