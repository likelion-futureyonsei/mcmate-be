import os

from apps.common.exceptions import DomainConflict, ServiceUnavailable
from apps.memories.models import Memory
from apps.memories.services import distance_m

from .models import GeneratedStory, Storybook

MEMORY_LIMIT = 20
MODEL = "gpt-4o-mini"


def collect_memories(user, storybook):
    if storybook.scope == Storybook.Scope.PRODUCT:
        qs = Memory.objects.filter(owner=user, user_product__product__storybook=storybook)
        return list(qs.order_by("created_at")[:MEMORY_LIMIT])

    places = list(storybook.places.all())
    picked = []
    for memory in Memory.objects.filter(owner=user).order_by("created_at"):
        if any(distance_m(memory.lat, memory.lng, p.lat, p.lng) <= p.radius for p in places):
            picked.append(memory)
            if len(picked) >= MEMORY_LIMIT:
                break
    return picked


def build_prompt(user, storybook, memories):
    records = "\n".join(
        f"- {m.created_at:%Y-%m-%d} {m.place_name or '어딘가'}: {m.note or '(글 없음)'}"
        for m in memories
    )
    chapters = ", ".join(storybook.chapters.values_list("title", flat=True))
    return (
        "너는 럭셔리 브랜드 MCM 의 스토리텔러다. "
        f"아래 사용자의 실제 기록을 바탕으로 '{storybook.title}' 스토리를 한국어로 써라.\n"
        f"사용자: {user.nickname}\n"
        f"스토리 뼈대(챕터): {chapters}\n"
        f"사용자의 기록:\n{records}\n"
        "조건: 3~4문단, 과장 없이 따뜻하게, 기록에 없는 사실은 지어내지 않는다."
    )


def call_llm(prompt):
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL, messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def generate_story(user, storybook):
    if not os.getenv("OPENAI_API_KEY"):
        raise ServiceUnavailable("AI 스토리 생성이 아직 설정되지 않았습니다.")

    memories = collect_memories(user, storybook)
    if not memories:
        raise DomainConflict("이 스토리북과 관련된 추억이 아직 없습니다. 추억을 먼저 담아 주세요.")

    body = call_llm(build_prompt(user, storybook, memories))
    story, _ = GeneratedStory.objects.update_or_create(
        user=user, storybook=storybook, defaults={"body": body}
    )
    return story
