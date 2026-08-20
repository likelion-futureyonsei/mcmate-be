import math

from apps.storybooks.models import Unlock

from .models import Memory, Place

EARTH_RADIUS_M = 6_371_000


def distance_m(lat1, lng1, lat2, lng2) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, map(float, (lat1, lng1, lat2, lng2)))
    d_lat, d_lng = lat2 - lat1, lng2 - lng1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _unlock(user, chapter, reason: str, unlocked: list) -> None:
    _, created = Unlock.objects.get_or_create(user=user, chapter=chapter)
    if created:
        unlocked.append(
            {
                "storybook_id": chapter.storybook_id,
                "chapter_no": chapter.chapter_no,
                "reason": reason,
            }
        )


def process_unlocks(memory: Memory) -> list[dict]:
    user = memory.owner
    unlocked: list[dict] = []

    # 작성 수 기준 제품 스토리북 해금
    product_storybook = memory.user_product.product.storybook
    if product_storybook is not None:
        count = memory.user_product.memories.count()
        for chapter in product_storybook.chapters.filter(required_memories__lte=count):
            _unlock(user, chapter, "memory_count", unlocked)

    # 특별 장소 좌표 매칭 (places 는 시드 수준이라 전수 순회로 충분)
    for place in Place.objects.select_related("storybook"):
        if distance_m(memory.lat, memory.lng, place.lat, place.lng) > place.radius:
            continue
        # 이 장소 반경 안에서 쓴 추억 수로 챕터 단계를 판정한다 (첫 방문 작성 = 1개)
        visits = sum(
            1
            for m in Memory.objects.filter(owner=user).only("lat", "lng")
            if distance_m(m.lat, m.lng, place.lat, place.lng) <= place.radius
        )
        for chapter in place.storybook.chapters.filter(required_memories__lte=visits):
            _unlock(user, chapter, "place_visit", unlocked)

    return unlocked


def matched_place_storybooks(memory):
    return [
        place.storybook
        for place in Place.objects.select_related("storybook")
        if distance_m(memory.lat, memory.lng, place.lat, place.lng) <= place.radius
    ]
