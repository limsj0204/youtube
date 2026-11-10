# 단어해체소: 영상 자동 제작 파이프라인

대본(YAML) 하나로 **롱폼 영상, 홍보용 쇼츠, 썸네일, 설명란(챕터와 출처 포함)**을 한 번에 만듭니다.

```
대본 YAML ─┬─ 음성 합성(TTS) ── 문장별 타이밍 계산
           ├─ 장면 렌더링 (단어 카드, 지도 항로, 연표, 여러 설 비교 …) + 자막
           └─ ffmpeg 합성 → mp4  /  썸네일 png  /  description.txt
```

## 설치

```bash
./setup.sh
```

ffmpeg, 한글 폰트(Noto CJK, 나눔), 파이썬 패키지, 무료 한국어 음성 모델(KSS VITS)을 설치합니다.

## 사용법

```bash
# 롱폼 (1920x1080)
python3 -m ytmaker.build episodes/001_portuguese_words/script.yaml

# 쇼츠 (1080x1920)
python3 -m ytmaker.build episodes/001_portuguese_words/script.yaml --short

# 렌더링 전에 장면별 화면만 PNG로 빠르게 확인
python3 -m ytmaker.build episodes/001_portuguese_words/script.yaml --preview
```

결과물은 `output/<에피소드>/` 에 생깁니다.

## 새 에피소드 만들기

1. `episodes/001_portuguese_words/script.yaml` 을 복사합니다.
2. `say:` 문장을 고칩니다. 숫자와 로마자는 음성용으로 한글로 풀어 쓰고, 화면 자막은 `sub:` 로 따로 적습니다.
3. `--preview` 로 화면을 확인한 다음 렌더링합니다.
4. **업로드 전에 `fact_check` 목록과 출처를 직접 확인합니다.** 어원은 근거 없는 민간어원이 많은 분야라서 이 단계가 채널의 신뢰도를 좌우합니다.

### 장면 종류

| type | 용도 |
|---|---|
| `hook` | 큰 글자 하나와 지워지는 후보들로 시작하는 도입부 |
| `title`, `chapter` | 제목 카드, 챕터 카드 (`chapter:` 값이 설명란 챕터가 됨) |
| `chain` | 어원 사슬: pão → パン → 빵 |
| `map` | 실제 세계지도 위에 항로와 전파 경로 애니메이션 |
| `timeline` | 연표 |
| `theories` | 정설이 없을 때 여러 설을 나란히 보여주고 '정설 없음' 도장 |
| `summary`, `sources`, `cta` | 정리, 참고 자료, 쇼츠에서 본편으로 유도 |
| `tableau` | 그림 여러 장을 배치해 상황을 보여주는 장면 (밀려 들어오기, 떠다니기, 확대 등 움직임) |

실제 사진·로고는 `assets/photos/`에 두고 `photo:파일.jpg`(흰 테두리 액자), `logo:이름`(흰 판 위, SVG·PNG)으로 씁니다. tableau 그림에 `credit:`을 적으면 그림 아래에 작은 출처가 나옵니다. 출처와 라이선스는 `assets/photos/SOURCE.txt`와 대본의 `credits`에 함께 적습니다.

`at`, `reveal`, `start`, `end` 값은 **몇 번째 문장(0부터)에서 등장할지**를 뜻합니다. 소수도 쓸 수 있습니다(1.5 = 1번 문장의 중간).

### 스타일(테마)

대본 맨 위에 `theme: dictionary`처럼 적거나, 만들 때 `--theme pop`을 붙입니다.

| 테마 | 느낌 |
|---|---|
| `midnight` | 짙은 남색, 호박색 (처음 버전) |
| `dictionary` | 누런 종이, 먹색 명조체, 붉은 도장 |
| `magazine` | 흰 바탕, 굵은 고딕, 빨강 한 색 |
| `magazine_dark` | 매거진의 흑백 반전 (검정 바탕, 흰 글씨) |
| `pop` | 노란 바탕, 굵은 검정 테두리, 딱딱한 그림자 |
| `chalk` | 칠판, 손글씨 |
| `blueprint` | 파란 모눈종이, 고정폭 글씨 |

테마 폰트에 없는 글자(일본어 가나, ã 같은 악센트 문자, 화살표)는 자동으로 Noto 폰트로 대신 그립니다.
색과 폰트는 `ytmaker/themes.py`에서 고칩니다.

### 그림 넣기

대본에서 그림은 이름으로 부릅니다.

| 이름 | 위치 | 출처 |
|---|---|---|
| `icon:bread` | `assets/icons/bread.svg` | [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) (MIT) |
| `flag:pt` | `assets/flags/pt.svg` | Wikimedia Commons 국기 (퍼블릭 도메인, 공식 비율 3:2) |
| `custom:carrack` | `assets/custom/carrack.svg` | 이 저장소에서 직접 그림 (16세기 범선, 카스텔라) |
| `episodes/.../img/a.png` | 그 경로 그대로 | AI 생성 이미지 등 직접 넣는 그림 |

- 어원 카드: `flag:` 또는 `badge:` 로 언어 옆에 국기나 아이콘 표시
- 지도: 항로의 `head:` 로 배나 빵이 항로를 따라 이동, 핀의 `icon:` 으로 이름표에 아이콘
- 제목, 챕터, 연표, 정리 장면: `icon:` 으로 그림 추가
- **국기는 시대에 맞을 때만** 씁니다. 16세기 항로의 경유지(고아, 믈라카, 마카오)는 당시 포르투갈 거점이었으므로 지금의 국기 대신 아이콘을 씁니다.

## 업그레이드 포인트

- **음성 (중요)**: 기본 음성은 KSS 데이터셋으로 학습한 모델이고, KSS는 **비상업 라이선스(CC BY-NC-SA 4.0)**입니다. 시험 제작용으로만 쓰고, 수익화 채널에는 상업적 이용이 허용된 TTS로 바꿔야 합니다. 품질도 기본 수준입니다. `ytmaker/tts.py` 의 `synthesize()` 만 바꾸면 일레븐랩스, 타입캐스트, 클로바 보이스 같은 상용 TTS로 교체할 수 있습니다.
- **대본 초안 자동화**: 단어 목록과 사전 자료를 LLM에 넣어 이 YAML 형식으로 초안을 받는 단계를 추가할 수 있습니다. 사람은 사실 확인만 하면 됩니다.
- **배경음악**: 아직 없습니다. 저작권이 해결된 음원을 `-i bgm.mp3` 로 낮은 볼륨으로 섞으면 됩니다.

## 사용한 자료

- 지도: Natural Earth (퍼블릭 도메인), [world-atlas](https://github.com/topojson/world-atlas) (ISC)
- 음성 모델: [Mimic 3 KSS](https://github.com/MycroftAI/mimic3-voices), sherpa-onnx 변환본
