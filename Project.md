# 프로젝트 구조
- law-monitor
├── .env
├── .gitignore
├── README.md
├── app
│   ├── collectors
│   │   └── law_api_collector.py : "https://law.go.kr/DRF/lawService.do" open api 조회 (json 방식 등)
│   ├── config
│   │   ├── constants.py  : {TARGET_LAWS 정의 : 전자금융거래법 / law, 전자금융거래법 시행령 / law, 전자금융감독규정 / admrul}
│   │   └── settings.py : 환경파일 세팅값 설정 (api key 등)
│   ├── parsers
│   │   └── law_parser.py : {법령, 행정규칙에 따른 json 파싱 로직}
│   ├── repositories
│   │   ├── db.py
│   │   ├── law_repository.py
│   │   └── version_repository.py
│   ├── services
│   │   ├── diff_engine.py
│   │   ├── impact_service.py
│   │   ├── law_id_service.py
│   │   ├── mail_service.py
│   │   ├── monitoring_service.py
│   │   ├── pdf_service.py
│   │   ├── report_service.py
│   │   └── version_service.py
│   └── utils
│       ├── hash_util.py
│       └── logger.py
├── data
├── db
│   └── ddl.sql
├── debug_pdf.py
├── fonts
│   ├── NanumGothic.ttf
│   ├── NanumGothicBold.ttf
│   └── malgun.ttf
├── logs
├── main.py
├── reqtest.py
└── requirements.txt

