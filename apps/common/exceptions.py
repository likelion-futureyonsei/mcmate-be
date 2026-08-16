import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainConflict(APIException):
    """409 Conflict. 명세상 "다음 행동 안내"(links)를 함께 실어 보낼 수 있다.

    예) 추억구슬 용량이 가득 찼을 때 -> 메시지 + 다음 제품 추천 링크
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "요청을 처리할 수 없는 상태입니다."

    def __init__(self, detail=None, links=None):
        super().__init__(detail)
        self.links = links or []


# 사용자에게 보여주면 안 되는 내부 진단용 키. 라이브러리들이 에러에 끼워 넣는다.
_INTERNAL_KEYS = frozenset({"code", "messages"})


def _flatten(detail) -> str:
    """DRF 의 중첩된 에러 구조를 사람이 읽는 한 문장으로 눌러 담는다."""
    if isinstance(detail, dict):
        # DRF·simplejwt 예외는 {"detail": ..., "code": ..., "messages": [...]} 모양이다.
        # 사람이 읽을 문장은 detail 뿐이고 나머지는 내부용이므로 버린다.
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
    """명세 0장: 에러 본문은 {"message": "..."} 만. 상태코드를 본문에 중복하지 않는다."""
    response = drf_exception_handler(exc, context)

    if response is None:
        # 명세: 5XX 는 사용자에게 그대로 리턴하지 않는다. 서버가 삼키고 로그로만 남긴다.
        logger.exception("처리되지 않은 예외", exc_info=exc)
        return Response(
            {"message": "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    payload = {"message": _flatten(response.data)}
    if links := getattr(exc, "links", None):
        payload["links"] = links
    response.data = payload
    return response
