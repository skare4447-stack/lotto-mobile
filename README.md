# 커피아자씨 로또 AI - 모바일(안드로이드) 버전

PC버전(lotto_project)의 통계/AI 엔진(`db/`, `algorithms/`, `api/`)을 그대로 재사용하고,
화면(UI)만 안드로이드용으로 새로 만든 버전입니다. (PyQt6는 모바일 빌드가 안 되기 때문에
Kivy + KivyMD로 새로 작성했습니다.) 플레이스토어(구글 안드로이드) 배포를 목표로 합니다.

## 구성

- `main.py` : 앱 진입점. 하단 탭바 5개(번호생성/고급생성/내조합/판매점/당첨결과) 구성.
- `db/`, `algorithms/`, `api/` : PC버전과 동일한 로직 (엔진은 그대로 재사용, DB 저장 경로만
  안드로이드 앱 전용 저장소를 쓰도록 `db/database.py`에서 분기 처리됨)
- `screens/` : 안드로이드 화면들
  - `generate_screen.py` : AI 자동생성 / 직접 선택
  - `advanced_screen.py` : 휠링 시스템 / 핫콜드 그리드 / 패턴 마스크 필터
  - `my_combos_screen.py` : 저장한 조합 관리
  - `store_screen.py` : 판매점 찾기 (GPS 내 위치 기준 + 시/도-구/군 수동 검색)
  - `dashboard_screen.py` : 당첨결과·패턴 + 실시간 동기화
  - `widgets_common.py` : 공용 위젯 (번호 그리드, 로또볼, 탭 버튼 등 - 가벼운 커스텀 렌더링 사용)
  - `toast.py` : 알림 팝업
- `assets/` : 앱 아이콘, 스플래시 이미지, 한글 폰트(나눔고딕 - 한글 표시를 위해 번들 필요)
- `buildozer.spec` : 안드로이드 APK 빌드 설정
- `.github/workflows/build-apk.yml` : GitHub Actions로 APK 자동 빌드하는 워크플로우

## 실행 (개발 PC에서 미리보기)

```
pip install kivy kivymd
LOTTO_DESKTOP_PREVIEW=1 python main.py
```

`LOTTO_DESKTOP_PREVIEW=1`을 주면 폰 화면 비율(420x780)의 창으로 뜹니다. 실제 폰 GPS는
데스크톱에서 동작하지 않으니, "내 위치로 검색" 버튼은 폰에서만 정상 동작합니다.

## APK 빌드하기 (중요 - 반드시 읽어주세요)

APK를 실제로 컴파일하려면 안드로이드 SDK/NDK를 구글 서버에서 내려받아야 하는데,
이 파일들이 용량이 크고(수백MB~1GB+) 첫 빌드에 시간이 꽤 걸립니다. 방법은 3가지입니다.

### 방법 1) GitHub Actions로 자동 빌드 (추천 - 별도 설치 필요 없음)

1. 이 `lotto_mobile` 폴더 전체를 GitHub 저장소로 올립니다 (private 저장소로 만들어도 됩니다).
2. 저장소에 push하면(또는 저장소 페이지 Actions 탭에서 수동 실행하면)
   `.github/workflows/build-apk.yml`이 자동으로 실행되어 GitHub의 서버에서 APK를 빌드합니다.
3. 빌드가 끝나면(첫 빌드는 15~30분 정도 걸릴 수 있음) Actions 실행 결과 페이지 하단의
   "Artifacts"에서 `lotto-coffee-apk` 를 다운로드하면 그 안에 `.apk` 파일이 들어있습니다.
4. 이 apk를 폰에 설치해서 테스트해보거나, 플레이 콘솔에 업로드하면 됩니다.

컴퓨터에 아무것도 설치할 필요 없이, 인터넷 되는 아무 브라우저에서 GitHub 계정만 있으면
진행할 수 있는 방법이라 가장 간단합니다.

### 방법 2) 인터넷 되는 리눅스 환경(또는 WSL2)에서 직접 빌드

```
pip install buildozer cython
sudo apt install -y openjdk-17-jdk unzip
buildozer android debug
```

첫 실행 시 buildozer가 안드로이드 SDK/NDK를 자동으로 내려받습니다(인터넷 필요, 시간 걸림).
완료되면 `bin/` 폴더에 `.apk` 파일이 생깁니다. 윈도우는 WSL2(우분투)를 설치한 뒤 그 안에서
진행하면 됩니다.

### 방법 3) 지금 이 개발 환경(샌드박스)

여기서는 구글 서버(`dl.google.com`) 접속이 막혀있어서 SDK/NDK 다운로드 단계에서 실패합니다.
(실제로 `buildozer android debug`를 실행해서 확인했습니다.) 그래서 이 환경에서는 APK를
끝까지 빌드할 수 없고, 방법 1 또는 2가 필요합니다.

## 폰에 미리 설치해서 테스트하려면

방법 1로 만든 apk 파일을 폰으로 옮긴 뒤(카카오톡 '나에게 보내기', 이메일 첨부, USB 등),
파일을 눌러 설치하면 됩니다. "출처를 알 수 없는 앱" 설치를 허용해야 할 수 있습니다.
플레이스토어에 정식 등록하기 전 단계이므로 정상입니다.

## 주의 (PC버전과 동일)

로또는 완전 무작위 추첨이므로 어떤 알고리즘·AI·휠링·필터도 실제 당첨 확률을 높이지
못합니다. 통계적 참고 도구로만 안내해주세요.
