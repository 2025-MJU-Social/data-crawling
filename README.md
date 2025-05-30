# data-crawling

키노라이츠(Kinolights) 웹사이트에서 영화 및 콘텐츠 데이터를 수집하는 파이프라인입니다.

## 파이프라인 개요

![파이프라인 다이어그램](./docs/main-pipeline.drawio.svg)

이 파이프라인은 다음 절차로 데이터를 수집합니다:

1. **콘텐츠 랭킹 데이터 확인**: 오늘 날짜의 데이터가 이미 있는지 확인
2. **OTT 플랫폼별 콘텐츠 랭킹 수집**: 각 플랫폼(Netflix, Tving 등)에서 인기 콘텐츠 수집
3. **남성/여성 선호 콘텐츠 분리**: 성별 및 연령대별 선호 콘텐츠 저장
4. **콘텐츠 통합 및 중복 제거**: 중복 없는 title, year, genre, genre_detail 정보 저장
5. **상세 장르 정보 수집**: 빈 genre_detail 필드가 있는 콘텐츠에 대해서만 상세 장르 수집
6. **데이터 병합**: 모든 정보를 통합하여 최종 데이터 생성

## 폴더 구조

```
data-crawling/
│
├── data/                   # 크롤링된 데이터 저장 폴더
│   ├── contents.csv        # 중복 제거된 콘텐츠 정보 (title, year, genre, genre_detail 등)
│   ├── daily_MALE_*.csv    # 남성 선호 콘텐츠
│   ├── daily_FEMALE_*.csv  # 여성 선호 콘텐츠
│   └── *_train_*.csv       # 훈련 데이터(content와 daily_ 데이터 조인)
│
├── docs/                   # 문서 폴더
│   └── main-pipeline.drawio.svg  # 파이프라인 다이어그램
│
├── main.py                 # 메인 실행 파일
├── crawling_data.py        # OTT 플랫폼 랭킹 데이터 수집 모듈
└── genre_collector.py      # 상세 장르 정보 수집 모듈
```

## 설치 및 설정

### 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 필요 패키지 목록

-   selenium
-   pandas
-   beautifulsoup4
-   webdriver_manager
-   python-dateutil

### 웹 드라이버 설정

크롬 드라이버는 자동으로 설치되지만, 크롬 브라우저가 미리 설치되어 있어야 합니다.

## 사용 방법

### 파이프라인 전체 실행

```bash
python main.py
```

### 개별 모듈 실행

```bash
# 랭킹 데이터만 수집
python crawling_data.py

# 상세 장르 정보만 수집 (contents.csv 파일 필요)
python genre_collector.py
```

## 데이터 출력 형식

### 콘텐츠 기본 정보 (contents.csv)

-   title: 제목
-   year: 출시 연도
-   genre: 기본 장르
-   genre_detail: 상세 장르 정보

### 콘텐츠 랭킹 데이터 (daily\_\*.csv)

-   rank: 순위
-   title: 제목
-   genre: 기본 장르
-   year: 출시 연도
-   score: 점수
-   platform: 제공 플랫폼 (쉼표로 구분된 여러 값 가능)
-   age_group: 연령대
-   gender: 성별

### 최종 훈련 데이터 (_*train*_.csv)

-   위의 모든 필드
-   genre_detail: 상세 장르 정보

## 주의사항

-   웹 크롤링 시 해당 사이트의 이용약관을 준수하세요
-   과도한 요청은 IP 차단을 야기할 수 있으니 주의하세요
-   데이터는 `./data` 폴더에 저장되며, contents.csv 파일은 계속 업데이트됩니다
