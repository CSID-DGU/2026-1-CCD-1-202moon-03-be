#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django를 찾을 수 없습니다. pip install -r requirements.txt 를 먼저 실행하세요.") from exc
    execute_from_command_line(sys.argv)
