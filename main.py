import os
import sys
from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        # 从环境变量获取端口号，默认为 8001
        port = 9001
        execute_from_command_line(["manage.py", "runserver", port])
    except Exception as e:
        print(f"启动服务器时出错: {str(e)}")
        sys.exit(1)