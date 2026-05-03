from rest_framework.response import Response


def success_response(message: str, data=None, status: int = 200) -> Response:
    return Response(
        {"message": message, "data": data if data is not None else {}},
        status=status,
    )


def error_response(message: str, data=None, status: int = 400) -> Response:
    return Response(
        {"message": message, "data": data if data is not None else {}},
        status=status,
    )
