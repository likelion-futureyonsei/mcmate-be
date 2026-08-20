from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.exceptions import DomainConflict

from .models import Chapter, GeneratedStory, Storybook, Unlock
from .services import generate_chapter_story


class StorybookListView(APIView):
    def get(self, request):
        owner_id = request.query_params.get("owner") or request.user.id

        # 유저의 해금 이력에서 스토리북별 최신(최대) 챕터 번호를 뽑는다
        latest: dict[int, int] = {}
        for unlock in Unlock.objects.filter(user_id=owner_id).select_related("chapter"):
            sb_id = unlock.chapter.storybook_id
            latest[sb_id] = max(latest.get(sb_id, 0), unlock.chapter.chapter_no)

        return Response(
            [
                {
                    "id": sb.id,
                    "scope": sb.scope,
                    "title": sb.title,
                    "cover_url": sb.cover_url,
                    "unlocked": sb.id in latest,
                    "latest_chapter": latest.get(sb.id),
                }
                for sb in Storybook.objects.all()
            ]
        )


class StorybookDetailView(APIView):
    def get(self, request, pk):
        try:
            storybook = Storybook.objects.prefetch_related("chapters").get(pk=pk)
        except Storybook.DoesNotExist:
            raise NotFound("스토리북을 찾을 수 없습니다.")

        opened = set(
            Unlock.objects.filter(user=request.user, chapter__storybook=storybook)
            .values_list("chapter_id", flat=True)
        )
        # 권별 내 생성 스토리. 없으면 시드 본문이 폴백이다
        stories = dict(
            GeneratedStory.objects.filter(user=request.user, chapter__storybook=storybook)
            .values_list("chapter_id", "body")
        )

        return Response(
            {
                "id": storybook.id,
                "scope": storybook.scope,
                "title": storybook.title,
                "cover_url": storybook.cover_url,
                "chapters": [
                    {
                        "id": chapter.id,
                        "chapter_no": chapter.chapter_no,
                        "title": chapter.title,
                        "required_memories": chapter.required_memories,
                        "unlocked": chapter.id in opened,
                        "story": (
                            stories.get(chapter.id) or chapter.body or None
                            if chapter.id in opened
                            else None
                        ),
                    }
                    for chapter in storybook.chapters.all()
                ],
            }
        )


class GenerateView(APIView):
    def post(self, request):
        chapter_id = request.data.get("chapter_id")
        if not chapter_id:
            raise ValidationError("chapter_id 는 필수 항목입니다.")
        try:
            chapter = Chapter.objects.select_related("storybook").get(pk=chapter_id)
        except (Chapter.DoesNotExist, ValueError):
            raise NotFound("챕터를 찾을 수 없습니다.")
        if not Unlock.objects.filter(user=request.user, chapter=chapter).exists():
            raise DomainConflict("아직 잠긴 챕터입니다. 추억을 담아 해금해 주세요.")

        story = generate_chapter_story(request.user, chapter)
        return Response(
            {
                "storybook_id": chapter.storybook_id,
                "chapter_id": chapter.id,
                "chapter_no": chapter.chapter_no,
                "title": chapter.title,
                "body": story.body,
            }
        )
