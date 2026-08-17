"""제품 API 회귀 테스트 (이슈 #6).

실행:  python ./manage.py test apps.products
"""

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.characters.models import Character
from apps.memories.models import Memory

from .models import Product, UserProduct

PASSWORD = "Mcm!Memory2026"


class ProductTestBase(APITestCase):
    def setUp(self):
        self.me = User.objects.create_user(
            email="me@mcmate.dev", password=PASSWORD, nickname="나", agree_data=True
        )
        self.other = User.objects.create_user(
            email="other@mcmate.dev", password=PASSWORD, nickname="남", agree_data=True
        )
        # 제품 마스터 3종 — 지갑(10) / 토트(20) / 백팩(30)
        self.wallet = Product.objects.create(
            name="비세토스 반지갑", line="비세토스", pattern="visetos",
            color="cognac", product_code="T-W-001", capacity=10,
        )
        self.tote = Product.objects.create(
            name="로레토스 토트백", line="로레토스", pattern="lauretos",
            color="silver", product_code="T-T-001", capacity=20,
        )
        self.backpack = Product.objects.create(
            name="슈타크 백팩", line="슈타크", pattern="visetos",
            color="black", product_code="T-B-001", capacity=30,
        )
        self.client.force_authenticate(self.me)


class ProductRegisterTests(ProductTestBase):
    """POST /products — 제품 등록"""

    url = "/api/v1/products"

    def test_등록은_201과_Location_헤더를_준다(self):
        response = self.client.post(
            self.url, {"product_id": self.wallet.id, "serial_no": "SN-0001"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        registered = UserProduct.objects.get(serial_no="SN-0001")
        self.assertEqual(response["Location"], f"/api/v1/products/{registered.id}")
        self.assertEqual(registered.owner, self.me)

    def test_등록_응답에_제품_정보와_빈_용량_게이지가_있다(self):
        response = self.client.post(
            self.url, {"product_id": self.wallet.id, "serial_no": "SN-0001"}, format="json"
        )

        self.assertEqual(response.data["product"]["name"], "비세토스 반지갑")
        self.assertEqual(response.data["capacity"], {"used": 0, "total": 10})
        self.assertEqual(response.data["memory_count"], 0)

    def test_내가_이미_등록한_시리얼은_409다(self):
        self.client.post(self.url, {"product_id": self.wallet.id, "serial_no": "SN-0001"}, format="json")

        response = self.client.post(
            self.url, {"product_id": self.wallet.id, "serial_no": "SN-0001"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("이미 등록한", response.data["message"])

    def test_타인_소유_시리얼은_409다(self):
        UserProduct.objects.create(owner=self.other, product=self.wallet, serial_no="SN-9999")

        response = self.client.post(
            self.url, {"product_id": self.wallet.id, "serial_no": "SN-9999"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("다른 사용자", response.data["message"])
        # 실패했어도 소유권은 그대로여야 한다
        self.assertEqual(UserProduct.objects.get(serial_no="SN-9999").owner, self.other)

    def test_없는_제품_id는_400이다(self):
        response = self.client.post(
            self.url, {"product_id": 999999, "serial_no": "SN-0001"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_토큰_없이는_등록할_수_없다(self):
        self.client.force_authenticate(None)

        response = self.client.post(
            self.url, {"product_id": self.wallet.id, "serial_no": "SN-0001"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProductListTests(ProductTestBase):
    """GET /products?owner={userID} — 보유 제품 목록"""

    def test_본인_목록에_용량_게이지와_추억_수가_나온다(self):
        mine = UserProduct.objects.create(owner=self.me, product=self.tote, serial_no="SN-0001")
        Memory.objects.create(
            owner=self.me, user_product=mine,
            lat=Decimal("37.5446"), lng=Decimal("127.0559"), place_name="성수동",
        )

        response = self.client.get(f"/api/v1/products?owner={self.me.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["capacity"], {"used": 1, "total": 20})
        self.assertEqual(response.data[0]["memory_count"], 1)

    def test_타인_목록은_403이다(self):
        """시리얼 번호가 담기므로 본인 외에는 열어주지 않는다."""
        UserProduct.objects.create(owner=self.other, product=self.tote, serial_no="SN-9999")

        response = self.client.get(f"/api/v1/products?owner={self.other.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_없이_호출하면_본인_목록이다(self):
        UserProduct.objects.create(owner=self.me, product=self.tote, serial_no="SN-0001")
        UserProduct.objects.create(owner=self.other, product=self.tote, serial_no="SN-9999")

        response = self.client.get("/api/v1/products")

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["serial_no"], "SN-0001")


class RecommendTests(ProductTestBase):
    """GET /recommend — 제품 추천 (Control Resource)"""

    def test_캐릭터_추천은_패턴_일치를_우선한다(self):
        character = Character.objects.create(
            owner=self.me, doll="rabbit", pattern="visetos", color="cognac"
        )

        response = self.client.get(f"/api/v1/recommend?character_id={character.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # visetos 인 지갑(패턴+색 일치)과 백팩(패턴 일치)이 로레토스 토트보다 앞서야 한다
        names = [item["name"] for item in response.data]
        self.assertEqual(names[0], "비세토스 반지갑")
        self.assertEqual(names[1], "슈타크 백팩")

    def test_없는_캐릭터는_404다(self):
        response = self.client.get("/api/v1/recommend?character_id=999999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_다음_여정_추천은_현재_제품을_제외하고_상위_용량을_준다(self):
        mine = UserProduct.objects.create(owner=self.me, product=self.wallet, serial_no="SN-0001")

        response = self.client.get(f"/api/v1/recommend?product_id={mine.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [item["name"] for item in response.data]
        self.assertNotIn("비세토스 반지갑", names)  # 지금 쓰는 제품은 추천하지 않는다
        self.assertTrue(all(item["capacity"] > 10 for item in response.data))

    def test_타인의_보유_제품으로는_추천받을_수_없다(self):
        others = UserProduct.objects.create(owner=self.other, product=self.wallet, serial_no="SN-9999")

        response = self.client.get(f"/api/v1/recommend?product_id={others.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_파라미터_없이_호출하면_400이다(self):
        response = self.client.get("/api/v1/recommend")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
