# 국가법령정보 OPEN API
## 법령
### 목록조회 : 
- URL 
-- http://www.law.go.kr/DRF/lawSearch.do?target=eflaw&OC=ITIBKI&type=JSON&query=전자금융거래법
-- http://www.law.go.kr/DRF/lawSearch.do?target=eflaw&OC=ITIBKI&type=JSON&LID=010199
- 결과
-- LawSearch > law > 현행연혁코드, 법령일련번호, 자법타법여부, 법령상세링크, 법령명한글, 법령구분명, 소관부처명, 공포번호, 제개정구분명, 소관부처코드, id, 법령ID, 공동부령정보, 시행일자, 공포일자, 법렬약칭명
--- 현행연혁코드 : 시행예정, 현행, 연혁
--- 법령상세링크 : http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=eflaw&MST=280277&type=JSON&mobileYn=&efYd=20261217
--- 법령구분명 : 법률
--- 소관부처명 : 금융위원회
--- 법령ID : 010199
--- 법령일련번호 : 280277
--- 시행일자 : 20261217
--- 공포일자 : 20251216

-- http://www.law.go.kr/DRF/lawSearch.do?target=eflaw&OC=ITIBKI&type=JSON&query=전자금융거래법시행령
-- http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=eflaw&MST=266805&type=JSON&mobileYn=&efYd=20241227

### 본문조회 : 법령상세링크, HTML은 JSON으로 변경하여 조회
- URL 
-- http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=eflaw&MST=280277&type=JSON&mobileYn=&efYd=20261217
- 결과
-- { 법령: { 개정문: { 개정문내용 : [[]] }, 법령키, 기본정보: {법령명_한글,공포번호,전화번호,언어,제개정구분,법령ID,공동부령정보,소관부서:{content, 법종구분코드}}, 시행일자, 연락부서: { 부서단위: {부서연락처,부서키,부서명,소관부처명,소관부처코드}}, 조문시행일자문자열, 법령명_한자, 법령명약칭, 공포일자, 편장절관}, 
부칙: { 부칙단위: {부칙키, 부치공포일자,부칙내용[[]], 부칙공포번호}},
조문: { 조문단위: {조문번호, 조문제개정유형, 조문시행일자, 조문변경여부, 조문이동이전, 조문키, 항: {호: {호번호,호내용, 목:{목번호, 목내용}}}조문내용, 조문제목, 조문이동이후, 조문여부}}

## 행정규칙
### 목록조회
- URL 
-- http://www.law.go.kr/DRF/lawSearch.do?target=admrul&OC=ITIBKI&type=JSON&query=전자금융감독규정
### 본문조회
- 결과
-- AdmRulSearch > admrul > 현행연혁구분, 행정규칙명, 발령일자, 행정규칙종류, 소관부처명, 제개정구분코드, 행정규칙상세링크, 제개정구분명, id, 생성일장, 행정규칙ID, 시행일자, 발령번호, 행정규칙일련번호
--- 행정규칙상세링크 : http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=admrul&ID=2100000274812&type=JSON&mobileYn=
--- 행정규칙종류 : 고시

--- 행정규칙상세링크 : http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=admrul&ID=2200000108281&type=JSON&mobileYn=
--- 행정규칙종류: 세칙

<!-- curl -o debug_전자금융거래법_251216.json "http://www.law.go.kr/DRF/lawService.do?OC=ITIBKI&target=eflaw&MST=280277&type=JSON&mobileYn=&efYd=20251216" -->