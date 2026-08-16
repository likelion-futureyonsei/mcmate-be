from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class HeaderLimitOffsetPagination(LimitOffsetPagination):
    """명세 0장의 두 줄을 동시에 지키기 위한 페이지네이션.

    - "응답 본문은 봉투 없이 리소스 JSON 그대로" -> 본문은 그냥 배열
    - "목록 조회는 offset / limit 페이징"        -> 총 개수와 앞뒤 링크는 헤더로

    총 개수는 `X-Total-Count`, 앞뒤 페이지는 RFC 5988 `Link` 헤더로 내려준다.
    프론트는 헤더만 읽으면 되고 본문 파싱 코드는 바뀌지 않는다.
    """

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
