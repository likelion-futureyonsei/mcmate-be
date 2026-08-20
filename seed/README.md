# 시드 데이터

관리자 화면에서 손으로 입력하는 대신, 파일로 한 번에 넣는다.

## 사용법 (순서 중요 — 스토리북을 제품·장소가 참조한다)

```sh
python ./manage.py loaddata seed/01_storybooks.json seed/02_products.json seed/03_places.json
```

다시 실행하면 같은 pk 를 덮어쓴다. 값을 고치고 재실행하면 갱신된다.

## 들어 있는 것

| 파일 | 내용 |
| --- | --- |
| `01_storybooks.json` | 스토리북 4권 (제품 2 + 장소 2), 챕터 11개 |
| `02_products.json` | 제품 마스터 6개 — 하이파이 시안 "나의 제품" 화면과 1:1 (id 1~6) |
| `03_places.json` | 특별 장소 2곳 — 성수(명세 8장 예시 좌표), 명동 |

## ⚠️ 회의(#11)에서 확정되면 고칠 값

현재는 **명세서의 제안값**으로 채워져 있다.

| 항목 | 현재 값 | 위치 |
| --- | --- | --- |
| 제품 용량 | 시안 게이지 기준 50/50/100/30/50/50 | `02` 의 `capacity` |
| 장소 인식 반경 | 200m | `03` 의 `radius` |
| 챕터 해금 조건 | 0/3/5/10 (제품), 0/2 (장소) | `01` 의 `required_memories` |
| 챕터 본문 | `[본문 placeholder]` | `01` 의 `body` — LLM 생성 후 교체 |

## 매칭 규칙 (GET /recommend 가 쓴다)

제품의 `pattern` / `color` 값은 캐릭터 선택지와 **같은 토큰**을 쓴다.
- pattern: `visetos` `lauretos` `cubic_monogram`
- color: `cognac` `black` `white` `silver` `pink`

캐릭터 외형과 제품을 문자열 일치로 바로 매칭할 수 있다.
