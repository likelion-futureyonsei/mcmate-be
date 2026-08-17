"""인증 API 회귀 테스트. 실행: python ./manage.py test apps.accounts"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User

PASSWORD = "Mcm!Memory2026"


class SignUpTests(APITestCase):
    """POST /users — 회원가입 (Collection URI)"""

    url = "/api/v1/users"

    def _payload(self, **overrides):
        payload = {
            "email": "pherd@team1.dev",
            "password": PASSWORD,
            "nickname": "퍼드",
            "birth": "1999-03-12",
            "phone": "010-1234-5678",
            "agree_data": True,
            "agree_marketing": False,
        }
        payload.update(overrides)
        return payload

    def test_회원가입은_201과_Location_헤더를_준다(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="pherd@team1.dev")
        self.assertEqual(response["Location"], f"/api/v1/users/{user.id}")
        self.assertEqual(response.data["id"], user.id)

    def test_비밀번호는_평문으로_저장되지_않는다(self):
        self.client.post(self.url, self._payload(), format="json")

        user = User.objects.get(email="pherd@team1.dev")
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_응답에_비밀번호가_들어가지_않는다(self):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertNotIn("password", response.data)

    def test_개인정보_미동의면_가입할_수_없다(self):
        response = self.client.post(self.url, self._payload(agree_data=False), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="pherd@team1.dev").exists())

    def test_중복_이메일은_400이다(self):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(self.url, self._payload(nickname="다른사람"), format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(email="pherd@team1.dev").count(), 1)

    def test_에러_본문은_message_키_하나뿐이다(self):
        """명세 0장: 에러는 {"message": "..."} 만. 상태코드를 본문에 중복하지 않는다."""
        response = self.client.post(self.url, self._payload(agree_data=False), format="json")

        self.assertEqual(list(response.data.keys()), ["message"])
        self.assertIsInstance(response.data["message"], str)


class TokenTests(APITestCase):
    """POST/DELETE /tokens, POST /tokens/refresh"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pherd@team1.dev", password=PASSWORD, nickname="퍼드", agree_data=True
        )

    def _login(self):
        return self.client.post(
            "/api/v1/tokens",
            {"email": "pherd@team1.dev", "password": PASSWORD},
            format="json",
        )

    def test_로그인은_토큰_두_개와_user_id를_준다(self):
        """프론트는 이 user_id 를 저장해 이후 ?owner={userID} 로 쓴다."""
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], self.user.id)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)

    def test_비밀번호가_틀리면_401이다(self):
        response = self.client.post(
            "/api/v1/tokens",
            {"email": "pherd@team1.dev", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_없는_계정과_틀린_비밀번호는_같은_응답이다(self):
        """어느 쪽이 틀렸는지 알려주면 이메일 존재 여부가 새어 나간다."""
        wrong_password = self.client.post(
            "/api/v1/tokens", {"email": "pherd@team1.dev", "password": "wrong"}, format="json"
        )
        no_account = self.client.post(
            "/api/v1/tokens", {"email": "nobody@team1.dev", "password": PASSWORD}, format="json"
        )

        self.assertEqual(wrong_password.status_code, no_account.status_code)
        self.assertEqual(wrong_password.data["message"], no_account.data["message"])

    def test_refresh로_새_access_token을_받는다(self):
        refresh = self._login().data["refresh_token"]

        response = self.client.post(
            "/api/v1/tokens/refresh", {"refresh_token": refresh}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_회전된_옛_refresh는_다시_쓸_수_없다(self):
        refresh = self._login().data["refresh_token"]
        self.client.post("/api/v1/tokens/refresh", {"refresh_token": refresh}, format="json")

        response = self.client.post(
            "/api/v1/tokens/refresh", {"refresh_token": refresh}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_망가진_refresh는_500이_아니라_401이다(self):
        """simplejwt 의 TokenError 는 DRF 예외가 아니라서 방치하면 500 으로 샌다."""
        response = self.client.post(
            "/api/v1/tokens/refresh", {"refresh_token": "garbage"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_누락은_명세_필드명으로_안내한다(self):
        """내부 이름(refresh)이 아니라 명세에 적힌 이름(refresh_token)이 나와야 한다."""
        response = self.client.post("/api/v1/tokens/refresh", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("refresh_token", response.data["message"])

    def test_에러_메시지에_내부_진단코드가_새지_않는다(self):
        response = self.client.post(
            "/api/v1/tokens/refresh", {"refresh_token": "garbage"}, format="json"
        )

        self.assertNotIn("code", response.data)
        self.assertNotIn("token_not_valid", response.data["message"])

    def test_로그아웃은_204이고_이후_refresh가_막힌다(self):
        login = self._login().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access_token']}")

        logout = self.client.delete(
            "/api/v1/tokens", {"refresh_token": login["refresh_token"]}, format="json"
        )

        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.client.credentials()
        retry = self.client.post(
            "/api/v1/tokens/refresh", {"refresh_token": login["refresh_token"]}, format="json"
        )
        self.assertEqual(retry.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_없이_로그아웃하면_400이다(self):
        login = self._login().data
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access_token']}")

        response = self.client.delete("/api/v1/tokens", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_로그인하지_않으면_로그아웃할_수_없다(self):
        response = self.client.delete("/api/v1/tokens", format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDetailTests(APITestCase):
    """GET / PATCH /users/:userID (Element URI)"""

    def setUp(self):
        self.me = User.objects.create_user(
            email="me@team1.dev",
            password=PASSWORD,
            nickname="나",
            phone="010-0000-0000",
            agree_data=True,
        )
        self.other = User.objects.create_user(
            email="other@team1.dev",
            password=PASSWORD,
            nickname="남",
            phone="010-9999-9999",
            agree_data=True,
        )
        self.client.force_authenticate(self.me)

    def test_본인_조회는_개인정보까지_보여준다(self):
        response = self.client.get(f"/api/v1/users/{self.me.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "me@team1.dev")
        self.assertIn("notify_memory", response.data)

    def test_타인_조회는_공개_정보만_보여준다(self):
        """명세: 본인 외에는 공개 정보만 반환. 캐릭터 뷰어에 필요한 만큼만."""
        response = self.client.get(f"/api/v1/users/{self.other.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"id", "nickname", "character"})
        self.assertNotIn("email", response.data)
        self.assertNotIn("phone", response.data)

    def test_토큰_없이는_조회할_수_없다(self):
        self.client.force_authenticate(None)

        response = self.client.get(f"/api/v1/users/{self.me.id}")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_없는_유저는_404다(self):
        response = self.client.get("/api/v1/users/999999")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_본인_알림_설정을_토글할_수_있다(self):
        response = self.client.patch(
            f"/api/v1/users/{self.me.id}", {"notify_ad": True}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.me.refresh_from_db()
        self.assertTrue(self.me.notify_ad)

    def test_타인_수정은_403이다(self):
        """URL 의 :userID 가 아니라 토큰의 유저 ID 로 판정한다."""
        response = self.client.patch(
            f"/api/v1/users/{self.other.id}", {"nickname": "해킹"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.other.refresh_from_db()
        self.assertEqual(self.other.nickname, "남")

    def test_이메일과_개인정보_동의는_수정할_수_없다(self):
        response = self.client.patch(
            f"/api/v1/users/{self.me.id}",
            {"email": "hacked@team1.dev", "agree_data": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.me.refresh_from_db()
        self.assertEqual(self.me.email, "me@team1.dev")
        self.assertTrue(self.me.agree_data)

    def test_지원하지_않는_메서드는_405다(self):
        response = self.client.delete(f"/api/v1/users/{self.me.id}")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(list(response.data.keys()), ["message"])
