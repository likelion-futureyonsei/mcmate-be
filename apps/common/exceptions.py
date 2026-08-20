import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "일시적으로 사용할 수 없는 기능입니다."


class DomainConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "요청을 처리할 수 없는 상태입니다."


# 내부 진단용 키 — 사용자 메시지에서 제외
_INTERNAL_KEYS = frozenset({"code", "messages"})


def _flatten(detail) -> str:
    """중첩된 DRF 에러 구조를 한 문장으로 요약한다."""
    if isinstance(detail, dict):
        if "detail" in detail:
            return _flatten(detail["detail"])
        parts = []
        for field, value in detail.items():
            if field in _INTERNAL_KEYS:
                continue
            text = _flatten(value)
            parts.append(text if field == "non_field_errors" else f"{field}: {text}")
        return " ".join(parts)
    if isinstance(detail, (list, tuple)):
        return " ".join(_flatten(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    """에러 본문을 {"message": "..."} 로 통일한다. 5XX 는 로그로만 남긴다 (명세 0장)."""
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.exception("처리되지 않은 예외", exc_info=exc)
        return Response(
            {"message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    response.data = {"message": _flatten(response.data)}
    return response
