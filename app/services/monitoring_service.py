import os
from app.collectors.law_api_collector import LawAPICollector
from app.parsers.law_parser import LawParser
from app.services.diff_engine import DiffEngine
from app.services.law_id_service import LawIdService
from app.utils.hash_util import generate_hash
from app.config.constants import TARGET_LAWS
from app.services.report_service import ReportService
from app.services.mail_service import MailService
from app.services.impact_service import ImpactService
from app.services.pdf_service import PdfService

# 데이터 저장 경로 설정
DATA_DIR = os.path.expanduser("~/law-monitor-data/")

class MonitoringService:
    def __init__(self):
        # 각 역할을 담당하는 서비스들 초기화
        self.collector = LawAPICollector()
        self.parser = LawParser()
        self.diff_engine = DiffEngine()
        self.id_service = LawIdService()
        self.report_service = ReportService()
        self.mail_service = MailService()
        self.impact_service = ImpactService()
        self.pdf_service = PdfService() # 생성자에서 초기화 권장

        # 데이터 저장 디렉토리 생성
        os.makedirs(DATA_DIR, exist_ok=True)

    def run_pdf_job(self):
        """
        [파라미터 pdf 로 실행 시]
        전체 법령 데이터를 수집하여 PDF로 만들고 메일로 전송합니다.
        """
        print("\n" + "="*30)
        print("   법령 PDF 생성 및 전송 시작")
        print("="*30)

        pdf_files = []

        for law in TARGET_LAWS:
            name = law["name"]
            target = law["target"]

            print(f"\n▶ {name} 처리 중...")

            try:
                # 1. 법령 ID 조회
                law_id = self.id_service.get_law_id(name, target)
                
                # 2. 데이터 수집 (안정적인 JSON 데이터 사용) [cite: 1, 3]
                # HTML 대신 JSON을 가져와서 파서를 통해 텍스트로 변환합니다.
                raw_json = self.collector.fetch_json(target, law_id)
                # 🔥 여기에 디버깅 코드 추가
                if "감독규정" in name:
                 print(f"\n🔍 [DEBUG] {name} JSON 원본 구조:")
                import json
                # 콘솔에 예쁘게 출력
                print(json.dumps(raw_json, indent=4, ensure_ascii=False)[:2000]) 
                
                # 내용이 길면 파일로 저장해서 확인 (가장 확실함)
                with open(f"debug_{name}.json", "w", encoding="utf-8") as f:
                    json.dump(raw_json, f, indent=4, ensure_ascii=False)
                print(f"✅ 상세 구조가 debug_{name}.json 파일로 저장되었습니다.")
                articles = self.parser.parse_articles(raw_json)

                # 3. PDF용 텍스트 조립 (조항별 제목 + 내용)
                full_content = ""
                for art_title, art_body in articles.items():
                    full_content += f"{art_title}\n{art_body}\n\n"

                if not full_content.strip():
                    print(f"⚠️ {name}: 본문 내용이 비어있어 PDF 생성을 건너뜁니다.")
                    continue

                # 4. PDF 생성 (PdfService에 텍스트 전달)
                pdf_path = self.pdf_service.generate_pdf(name, full_content)
                pdf_files.append(pdf_path)
                
            except Exception as e:
                print(f"❌ {name} 처리 중 오류 발생: {e}")

        # 5. 메일 발송 (첨부파일이 있을 경우만)
        if pdf_files:
            print(f"\n📧 메일 발송 중... (첨부파일 {len(pdf_files)}건)")
            self.mail_service.send_mail_with_attachments(
                subject="[법령 모니터링] 전체 법령 PDF 리포트",
                body="요청하신 법령의 전체 본문 PDF 파일들을 첨부하여 보내드립니다.",
                file_paths=pdf_files
            )
            print("✅ 메일 발송 완료")
        else:
            print("📭 생성된 PDF 파일이 없어 메일을 발송하지 않았습니다.")

    def run(self):
        """
        [일반 모니터링 모드]
        변경사항을 감지하고 분석하여 리포트를 발송합니다.
        """
        print("\n" + "="*30)
        print("   법령 모니터링 시작")
        print("="*30)

        for law in TARGET_LAWS:
            self.process(law)

    def process(self, law):
        name = law["name"]
        target = law["target"]

        print(f"\n▶ {name} 분석 중")

        # 1. 최신 데이터 수집 및 해시 생성
        law_id = self.id_service.get_law_id(name, target)
        new_data = self.collector.fetch_json(target, law_id) # [cite: 1]
        new_hash = generate_hash(new_data)

        file_path = os.path.join(DATA_DIR, f"{name}.txt")

        # 2. 최초 수집 처리
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_data)
            print("📁 최초 데이터 저장 완료")
            return

        # 3. 기존 데이터와 비교
        with open(file_path, "r", encoding="utf-8") as f:
            old_data = f.read()

        old_hash = generate_hash(old_data)

        if new_hash == old_hash:
            print("✅ 변경 사항 없음")
            return

        print("🚨 변경 감지! 분석을 시작합니다.")

        # 4. 변경 내용 상세 분석 (Diff)
        old_articles = self.parser.parse_articles(old_data)
        new_articles = self.parser.parse_articles(new_data)
        changes = self.diff_engine.compare_articles(old_articles, new_articles)

        if changes:
            # 5. 영향도 분석 및 리포트 발송
            impact = self.impact_service.analyze(name, changes)
            html_report = self.report_service.generate_html(name, changes, impact)

            self.mail_service.send_mail(
                subject=f"[법령 개정 알림] {name}",
                html_body=html_report
            )
            
            # 6. 로컬 저장소 업데이트
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_data)
            print(f"💾 {name} 업데이트 및 메일 발송 완료")