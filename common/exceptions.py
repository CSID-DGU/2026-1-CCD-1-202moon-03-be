from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        # DRF 기본 응답을 { message, data } 포맷으로 통일
        original_data = response.data

        # detail 단일 메시지인 경우
        if isinstance(original_data, dict) and "detail" in original_data:
            message = str(original_data["detail"])
            data = {}
        # 필드 유효성 에러 dict인 경우
        elif isinstance(original_data, dict):
            message = "입력값이 올바르지 않습니다."
            data = original_data
        else:
            message = str(original_data)
            data = {}

        response.data = {
            "message": message,
            "data": data,
        }

    return response
