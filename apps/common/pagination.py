from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class HeaderLimitOffsetPagination(LimitOffsetPagination):
    """본문은 봉투 없는 배열, 총 개수·앞뒤 링크는 X-Total-Count / Link 헤더로 (명세 0장)."""

    default_limit = 20
    max_limit = 100
    limit_query_param = "limit"
    offset_query_param = "offset"

    def get_paginated_response(self, data):
        headers = {"X-Total-Count": str(self.count)}

        links = []
        if next_url := self.get_next_link():
            links.append(f'<{next_url}>; rel="next"')
        if prev_url := self.get_previous_link():
            links.append(f'<{prev_url}>; rel="prev"')
        if links:
            headers["Link"] = ", ".join(links)

        return Response(data, headers=headers)
