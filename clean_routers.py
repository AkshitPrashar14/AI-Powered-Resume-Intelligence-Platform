import os
import re
import glob

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    
    # Remove router dependencies
    content = re.sub(r',\s*current_user:\s*User\s*=\s*Depends\(get_current_active_user\)', '', content)
    content = re.sub(r'current_user:\s*User\s*=\s*Depends\(get_current_active_user\),\s*', '', content)
    content = re.sub(r'current_user:\s*User\s*=\s*Depends\(get_current_active_user\)', '', content)
    
    # Remove imports
    content = re.sub(r'from app\.api\.deps import.*?get_current_active_user.*?\n', '', content)
    content = re.sub(r'from app\.models\.user import User\n', '', content)
    content = re.sub(r'from app\.models import User\n', '', content)
    content = re.sub(r'from app\.services\.auth_service import get_current_active_user\n', '', content)
    
    # Remove user_id from service calls
    content = re.sub(r',\s*user_id=current_user\.id', '', content)
    content = re.sub(r'user_id=current_user\.id,\s*', '', content)
    content = re.sub(r'user_id=current_user\.id', '', content)
    
    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for f in glob.glob('app/api/routers/*.py'):
    if 'auth_router.py' not in f and 'health_router.py' not in f:
        process_file(f)

try:
    os.remove('app/api/routers/auth_router.py')
    print("Deleted auth_router.py")
except FileNotFoundError:
    pass

try:
    os.remove('app/api/deps.py')
    print("Deleted deps.py")
except FileNotFoundError:
    pass
