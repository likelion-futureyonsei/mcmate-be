from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class HeaderLimitOffsetPagination(LimitOffsetPagination):
    """본문은 배열 그대로 두고 총 개수는 X-Total-Count 헤더로 내린다."""

    default_limit = 20
    max_limit = 100
    limit_query_param = "limit"
    offset_query_param = "offset"

    def get_paginated_response(self, data):
        return Response(data, headers={"X-Total-Count": str(self.count)})
