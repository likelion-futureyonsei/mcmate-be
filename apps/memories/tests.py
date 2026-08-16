"""코어 API 회귀 테스트 (이슈 #7) — 용량 체크와 스토리북 해금.

실행:  python ./manage.py test apps.memories
"""

import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.products.models import Product, UserProduct
from apps.storybooks.models import Chapter, Storybook, Unlock

from .models import Memory, Place

PASSWORD = "Mcm!Memory2026"

# 성수 좌표 (명세 8장 예시). 반경 200m 밖 테스트용으로 북쪽으로 크게 벗어난 좌표도 준비.
SEONGSU = {"lat": "37.5446", "lng": "127.0559"}
FAR_AWAY = {"lat": "37.6446", "lng": "127.0559"}  # 약 11km 북쪽


class MemoryTestBase(APITestCase):
    def setUp(self):
        self.me = User.objects.create_user(
            email="me@mcmate.dev", password=PASSWORD, nickname="나", agree_data=True
        )
        self.other = User.objects.create_user(
            email="other@mcmate.dev", password=PASSWORD, nickname="남", agree_data=True
        )

        # 제품 스토리북: 1개 담으면 1챕터, 2개 담으면 2챕터
        self.product_sb = Storybook.objects.create(scope="product", title="여정")
        Chapter.objects.create(storybook=self.product_sb, chapter_no=1, title="시작", required_memories=1)
        Chapter.objects.create(storybook=self.product_sb, chapter_no=2, title="둘", required_memories=2)

        # 장소 스토리북: 성수 반경 200m 안에서 1개 쓰면 1챕터
        self.place_sb = Storybook.objects.create(scope="place", title="성수")
        Chapter.objects.create(storybook=self.place_sb, chapter_no=1, title="도착", required_memories=1)
        self.place = Place.objects.create(
            type="store", name="MCM 성수",
            lat=Decimal(SEONGSU["lat"]), lng=Decimal(SEONGSU["lng"]),
            radius=200, storybook=self.place_sb,
        )

        # 용량 2짜리 작은 제품 — 용량 초과(409) 테스트를 짧게 하기 위함
        self.product = Product.objects.create(
            name="미니 파우치", line="비세토스", pattern="visetos", color="cognac",
            product_code="T-P-001", capacity=2, storybook=self.product_sb,
        )
        self.mine = UserProduct.objects.create(
            owner=self.me, product=self.product, serial_no="SN-0001"
        )
        self.client.force_authenticate(self.me)

    def write_memory(self, **overrides):
        payload = {
            "user_product_id": self.mine.id,
            "place_name": "성수동",
            "note": "낯선 길이 익숙해질 때까지",
            "visibility": "public",
            **SEONGSU,
        }
        payload.update(overrides)
        return self.client.post("/api/v1/memories", payload, format="json")


class MemoryCreateTests(MemoryTestBase):
    """POST /memories — 생성과 응답 형태 (명세 8장)"""

    def test_작성은_201과_Location_헤더를_준다(self):
        response = self.write_memory()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        memory = Memory.objects.get()
        self.assertEqual(response["Location"], f"/api/v1/memories/{memory.id}")
        self.assertEqual(memory.owner, self.me)

    def test_응답에_용량_게이지가_있다(self):
        response = self.write_memory()

        self.assertEqual(response.data["capacity"], {"used": 1, "total": 2})

    def test_타인의_보유_제품에는_담을_수_없다(self):
        others = UserProduct.objects.create(
            owner=self.other, product=self.product, serial_no="SN-9999"
        )

        response = self.write_memory(user_product_id=others.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Memory.objects.count(), 0)

    def test_토큰_없이는_작성할_수_없다(self):
        self.client.force_authenticate(None)

        response = self.write_memory()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CapacityTests(MemoryTestBase):
    """서버 로직 ① — 용량 체크"""

    def test_용량이_가득_차면_409와_다음_여정_추천_links를_준다(self):
        self.write_memory()
        self.write_memory()  # capacity 2 소진

        response = self.write_memory()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("가득", response.data["message"])
        links = response.data["links"]
        self.assertEqual(links[0]["rel"], "next-journey")
        self.assertIn(f"product_id={self.mine.id}", links[0]["href"])
        self.assertEqual(Memory.objects.count(), 2)  # 세 번째는 저장되지 않아야 한다


class UnlockTests(MemoryTestBase):
    """서버 로직 ②③ — 스토리북 해금"""

    def test_첫_작성으로_제품_챕터1이_열린다(self):
        response = self.write_memory(**FAR_AWAY)  # 장소 해금과 분리해 제품 해금만 본다

        unlocked = response.data["unlocked"]
        self.assertEqual(
            unlocked,
            [{"storybook_id": self.product_sb.id, "chapter_no": 1, "reason": "memory_count"}],
        )
        self.assertEqual(response.data["links"][0]["rel"], "unlocked-chapter")
        self.assertTrue(
            Unlock.objects.filter(user=self.me, chapter__chapter_no=1).exists()
        )

    def test_이미_열린_챕터는_다시_보고되지_않는다(self):
        self.write_memory(**FAR_AWAY)

        response = self.write_memory(**FAR_AWAY)  # 두 번째 -> 챕터2만 새로 열려야 한다

        chapter_nos = [u["chapter_no"] for u in response.data["unlocked"] if u["storybook_id"] == self.product_sb.id]
        self.assertEqual(chapter_nos, [2])

    def test_특별_장소_반경_안이면_장소_스토리북이_열린다(self):
        response = self.write_memory()  # 성수 좌표 그대로

        reasons = {(u["storybook_id"], u["reason"]) for u in response.data["unlocked"]}
        self.assertIn((self.place_sb.id, "place_visit"), reasons)

    def test_반경_밖이면_장소_해금이_없다(self):
        response = self.write_memory(**FAR_AWAY)

        storybook_ids = {u["storybook_id"] for u in response.data["unlocked"]}
        self.assertNotIn(self.place_sb.id, storybook_ids)


class MemoryReadTests(MemoryTestBase):
    """GET /memories, GET /memories/:memoryID — 조회 (이슈 #8)"""

    def setUp(self):
        super().setUp()
        self.product.capacity = 100  # 조회 테스트에서 용량에 걸리지 않게
        self.product.save()
        others_product = UserProduct.objects.create(
            owner=self.other, product=self.product, serial_no="SN-9999"
        )
        self.my_public = Memory.objects.create(
            owner=self.me, user_product=self.mine, visibility="public",
            lat=Decimal(SEONGSU["lat"]), lng=Decimal(SEONGSU["lng"]), place_name="성수",
        )
        self.my_private = Memory.objects.create(
            owner=self.me, user_product=self.mine, visibility="private",
            lat=Decimal(FAR_AWAY["lat"]), lng=Decimal(FAR_AWAY["lng"]), place_name="멀리",
        )
        self.others_public = Memory.objects.create(
            owner=self.other, user_product=others_product, visibility="public",
            lat=Decimal(SEONGSU["lat"]), lng=Decimal(SEONGSU["lng"]), place_name="성수",
        )
        self.others_private = Memory.objects.create(
            owner=self.other, user_product=others_product, visibility="private",
            lat=Decimal(SEONGSU["lat"]), lng=Decimal(SEONGSU["lng"]), place_name="성수",
        )

    def test_목록에_타인의_비공개는_보이지_않는다(self):
        response = self.client.get("/api/v1/memories")

        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.my_public.id, self.my_private.id, self.others_public.id})

    def test_owner_필터는_그_유저의_공개_추억만_준다(self):
        response = self.client.get(f"/api/v1/memories?owner={self.other.id}")

        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.others_public.id})

    def test_product_id_필터가_동작한다(self):
        response = self.client.get(f"/api/v1/memories?product_id={self.mine.id}")

        ids = {item["id"] for item in response.data}
        self.assertEqual(ids, {self.my_public.id, self.my_private.id})

    def test_지도_반경_필터가_동작한다(self):
        response = self.client.get(
            f"/api/v1/memories?lat={SEONGSU['lat']}&lng={SEONGSU['lng']}&radius=500"
        )

        ids = {item["id"] for item in response.data}
        # 성수 좌표의 것만 — 11km 밖(my_private)은 제외
        self.assertEqual(ids, {self.my_public.id, self.others_public.id})

    def test_반경_필터_값이_숫자가_아니면_400이다(self):
        response = self.client.get("/api/v1/memories?lat=abc&lng=127&radius=500")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_상세는_owner를_포함한다(self):
        response = self.client.get(f"/api/v1/memories/{self.others_public.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["owner"], self.other.id)

    def test_타인의_비공개_상세는_403이다(self):
        response = self.client.get(f"/api/v1/memories/{self.others_private.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_내_비공개_상세는_보인다(self):
        response = self.client.get(f"/api/v1/memories/{self.my_private.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UploadTests(APITestCase):
    """POST /upload — 사진 업로드 (Control Resource)"""

    def setUp(self):
        self.me = User.objects.create_user(
            email="me@mcmate.dev", password=PASSWORD, nickname="나", agree_data=True
        )
        self.client.force_authenticate(self.me)

    def test_업로드하면_key와_url을_받는다(self):
        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp):
                file = SimpleUploadedFile("photo.jpg", b"fake-image-bytes", "image/jpeg")

                response = self.client.post("/api/v1/upload", {"file": file}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["key"].startswith("memories/"))
        self.assertTrue(response.data["key"].endswith(".jpg"))
        self.assertIn("url", response.data)

    def test_파일_없이_호출하면_400이다(self):
        response = self.client.post("/api/v1/upload", {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_토큰_없이는_업로드할_수_없다(self):
        self.client.force_authenticate(None)

        response = self.client.post("/api/v1/upload", {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
