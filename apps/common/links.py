"""명세 0장 "다음 행동 안내"(links[]) 를 만드는 헬퍼.

해금·구매 제안처럼 후속 동작이 있는 응답은 아래 형태를 따른다.
    {"rel": ..., "href": ..., "method": ..., "description": ...}
"""


def link(rel: str, href: str, description: str, method: str = "GET") -> dict:
    return {"rel": rel, "href": href, "method": method, "description": description}


def unlocked_chapter_link(storybook_id: int) -> dict:
    return link(
        "unlocked-chapter",
        f"/storybooks/{storybook_id}",
        "방금 열린 스토리북 챕터 읽기",
    )


def next_journey_link(user_product_id: int) -> dict:
    return link(
        "next-journey",
        f"/recommend?product_id={user_product_id}",
        "다음 여정을 함께할 제품 추천",
    )
