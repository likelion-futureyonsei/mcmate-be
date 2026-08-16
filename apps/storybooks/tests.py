"""스토리북 조회 API 회귀 테스트 (이슈 #8).

실행:  python ./manage.py test apps.storybooks
"""

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User

from .models import Chapter, Storybook, Unlock

PASSWORD = "Mcm!Memory2026"


class StorybookTestBase(APITestCase):
    def setUp(self):
        self.me = User.objects.create_user(
            email="me@mcmate.dev", password=PASSWORD, nickname="나", agree_data=True
        )
        # 스토리북 2권 — 하나는 챕터 2개 중 1개 해금, 하나는 미해금
        self.opened_sb = Storybook.objects.create(scope="product", title="여정")
        self.ch1 = Chapter.objects.create(
            storybook=self.opened_sb, chapter_no=1, title="시작", body="첫 이야기", required_memories=1
        )
        self.ch2 = Chapter.objects.create(
            storybook=self.opened_sb, chapter_no=2, title="다음", body="숨겨진 이야기", required_memories=3
        )
        self.locked_sb = Storybook.objects.create(scope="place", title="성수")
        Chapter.objects.create(
            storybook=self.locked_sb, chapter_no=1, title="도착", body="장소 이야기", required_memories=1
        )
        Unlock.objects.create(user=self.me, chapter=self.ch1)
        self.client.force_authenticate(self.me)


class StorybookListTests(StorybookTestBase):
    """GET /storybooks?owner={userID}"""

    def test_미해금_스토리북도_전체_목록에_포함된다(self):
        """도감 화면에서 미획득 항목을 흐리게 표시해야 하므로 전체 반환 (명세 5장)."""
        response = self.client.get(f"/api/v1/storybooks?owner={self.me.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_잠금_여부와_최신_챕터가_명세_형식으로_나온다(self):
        response = self.client.get(f"/api/v1/storybooks?owner={self.me.id}")

        by_id = {item["id"]: item for item in response.data}
        opened = by_id[self.opened_sb.id]
        locked = by_id[self.locked_sb.id]
        self.assertTrue(opened["unlocked"])
        self.assertEqual(opened["latest_chapter"], 1)
        self.assertFalse(locked["unlocked"])
        self.assertIsNone(locked["latest_chapter"])

    def test_토큰_없이는_볼_수_없다(self):
        self.client.force_authenticate(None)

        response = self.client.get("/api/v1/storybooks")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class StorybookViewerTests(StorybookTestBase):
    """GET /storybooks/:storybookID"""

    def test_열린_챕터는_본문이_있고_잠긴_챕터는_null이다(self):
        """미해금 콘텐츠 노출 방지 — 보안 합의 사항."""
        response = self.client.get(f"/api/v1/storybooks/{self.opened_sb.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chapters = {c["chapter_no"]: c for c in response.data["chapters"]}
        self.assertEqual(chapters[1]["body"], "첫 이야기")
        self.assertTrue(chapters[1]["unlocked"])
        self.assertIsNone(chapters[2]["body"])       # 본문 숨김
        self.assertEqual(chapters[2]["title"], "다음")  # 제목은 보임
        self.assertFalse(chapters[2]["unlocked"])

    def test_없는_스토리북은_404다(self):
        response = self.client.get("/api/v1/storybooks/999999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
