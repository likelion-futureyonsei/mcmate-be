"""스토리북 조회 API 회귀 테스트 (이슈 #8).

실행:  python ./manage.py test apps.storybooks
"""

import os
from decimal import Decimal
from unittest import mock

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.memories.models import Memory
from apps.products.models import Product, UserProduct

from .models import Chapter, GeneratedStory, Storybook, Unlock

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

    def test_열린_챕터는_스토리가_있고_잠긴_챕터는_null이다(self):
        """미해금 콘텐츠 노출 방지. 생성 스토리가 없으면 시드 본문이 폴백."""
        response = self.client.get(f"/api/v1/storybooks/{self.opened_sb.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        chapters = {c["chapter_no"]: c for c in response.data["chapters"]}
        self.assertEqual(chapters[1]["story"], "첫 이야기")
        self.assertTrue(chapters[1]["unlocked"])
        self.assertIsNone(chapters[2]["story"])       # 본문 숨김
        self.assertEqual(chapters[2]["title"], "다음")  # 제목은 보임
        self.assertFalse(chapters[2]["unlocked"])

    def test_없는_스토리북은_404다(self):
        response = self.client.get("/api/v1/storybooks/999999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GenerateTestBase(APITestCase):
    def setUp(self):
        self.me = User.objects.create_user(
            email="me@mcmate.dev", password=PASSWORD, nickname="나", agree_data=True
        )
        self.sb = Storybook.objects.create(scope="product", title="여정")
        self.ch = Chapter.objects.create(
            storybook=self.sb, chapter_no=1, title="시작", required_memories=1
        )
        product = Product.objects.create(
            name="반지갑", line="비세토스", pattern="visetos", color="cognac",
            product_code="T-G-001", capacity=10, storybook=self.sb,
        )
        self.mine = UserProduct.objects.create(owner=self.me, product=product, serial_no="SN-G-01")
        self.client.force_authenticate(self.me)

    def add_memory(self, note="성수에서"):
        return Memory.objects.create(
            owner=self.me, user_product=self.mine,
            lat=Decimal("37.5446"), lng=Decimal("127.0559"), place_name="성수동", note=note,
        )

    def unlock(self):
        Unlock.objects.get_or_create(user=self.me, chapter=self.ch)

    def generate(self, **payload):
        return self.client.post("/api/v1/generate", {"chapter_id": self.ch.id, **payload}, format="json")


@mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
class GenerateTests(GenerateTestBase):
    """POST /generate — 권(챕터)별 AI 스토리 생성"""

    @mock.patch("apps.storybooks.services.call_llm", return_value="생성된 이야기")
    def test_생성하면_본문을_돌려주고_저장된다(self, mocked):
        self.add_memory()
        self.unlock()

        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["body"], "생성된 이야기")
        self.assertEqual(response.data["chapter_no"], 1)
        self.assertEqual(GeneratedStory.objects.filter(user=self.me, chapter=self.ch).count(), 1)

    @mock.patch("apps.storybooks.services.call_llm", return_value="새 이야기")
    def test_재생성하면_덮어쓴다(self, mocked):
        self.add_memory()
        self.unlock()
        GeneratedStory.objects.create(user=self.me, chapter=self.ch, body="옛 이야기")

        self.generate()

        story = GeneratedStory.objects.get(user=self.me, chapter=self.ch)
        self.assertEqual(story.body, "새 이야기")
        self.assertEqual(GeneratedStory.objects.count(), 1)

    @mock.patch("apps.storybooks.services.call_llm", return_value="이야기")
    def test_프롬프트에_유저_기록과_권_정보가_들어간다(self, mocked):
        self.add_memory(note="낯선 길이 익숙해질 때까지")
        self.unlock()

        self.generate()

        prompt = mocked.call_args[0][0]
        self.assertIn("낯선 길이 익숙해질 때까지", prompt)
        self.assertIn("여정", prompt)
        self.assertIn("1권", prompt)

    @mock.patch("apps.storybooks.services.call_llm", return_value="이야기")
    def test_프롬프트에_브랜드_정보가_들어간다(self, mocked):
        self.add_memory()
        self.unlock()

        self.generate()

        prompt = mocked.call_args[0][0]
        self.assertIn("반지갑", prompt)
        self.assertIn("비세토스", prompt)

    def test_잠긴_챕터는_생성할_수_없다(self):
        self.add_memory()

        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("잠긴", response.data["message"])

    def test_관련_추억이_없으면_409다(self):
        self.unlock()

        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("추억", response.data["message"])

    def test_chapter_id_누락은_400이다(self):
        response = self.client.post("/api/v1/generate", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_없는_챕터는_404다(self):
        response = self.client.post("/api/v1/generate", {"chapter_id": 999999}, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch("apps.storybooks.services.call_llm", return_value="이야기")
    def test_생성_후_뷰어의_해당_권에_스토리가_보인다(self, mocked):
        self.add_memory()
        self.unlock()
        self.generate()

        response = self.client.get(f"/api/v1/storybooks/{self.sb.id}")

        chapters = {c["chapter_no"]: c for c in response.data["chapters"]}
        self.assertEqual(chapters[1]["story"], "이야기")

    def test_토큰_없이는_생성할_수_없다(self):
        self.client.force_authenticate(None)

        response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class GenerateWithoutKeyTests(GenerateTestBase):
    def test_키가_없으면_503이다(self):
        self.add_memory()
        self.unlock()
        env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}

        with mock.patch.dict(os.environ, env, clear=True):
            response = self.generate()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
