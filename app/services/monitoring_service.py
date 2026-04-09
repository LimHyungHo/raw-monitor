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

DATA_DIR = os.path.expanduser("~/law-monitor-data/")


class MonitoringService:

    def __init__(self):
        self.collector = LawAPICollector()
        self.parser = LawParser()
        self.diff_engine = DiffEngine()
        self.id_service = LawIdService()
        self.report_service = ReportService()
        self.mail_service = MailService()
        self.impact_service = ImpactService()

        os.makedirs(DATA_DIR, exist_ok=True)

# from app.services.pdf_service import PdfService
    # def run_pdf_job(self):

    #     print("=== 법령 PDF 생성 (다중 첨부) ===")

    #     from app.services.pdf_service import PdfService

    #     pdf_service = PdfService()

    #     pdf_files = []

    #     for law in TARGET_LAWS:

    #         name = law["name"]
    #         target = law["target"]

    #         print(f"\n▶ {name}")

    #         law_id = self.id_service.get_law_id(name, target)

    #         content = self.collector.fetch_by_id(target, law_id)

    #         # PDF 생성
    #         pdf_path = pdf_service.generate_pdf(name, content)

    #         pdf_files.append(pdf_path)

    #     # 🔥 메일 1번 (여러 첨부)
    #     self.mail_service.send_mail_with_attachments(
    #         subject="[월간 법령 PDF]",
    #         body="전체 법령 PDF 첨부드립니다.",
    #         file_paths=pdf_files
    #     )
    def run_pdf_job(self):

        print("=== 법령 PDF 생성 ===")

        from app.services.pdf_service import PdfService

        pdf_service = PdfService()

        pdf_files = []

        for law in TARGET_LAWS:

            name = law["name"]
            target = law["target"]

            print(f"\n▶ {name}")

            law_id = self.id_service.get_law_id(name, target)

            # 🔥 HTML 사용
            html = self.collector.fetch_html(target, law_id)

            pdf_path = pdf_service.generate_pdf(name, html)

            pdf_files.append(pdf_path)

        self.mail_service.send_mail_with_attachments(
            subject="[월간 법령 PDF]",
            body="전체 법령 PDF 첨부드립니다.",
            file_paths=pdf_files
        )

    def run(self):
        print("=== 법령 모니터링 시작 ===")

        for law in TARGET_LAWS:
            self.process(law)

    def process(self, law):

        name = law["name"]
        target = law["target"]

        print(f"\n▶ {name}")

        law_id = self.id_service.get_law_id(name, target)

        new_data = self.collector.fetch_json(target, law_id)
        new_hash = generate_hash(new_data)

        file_path = os.path.join(DATA_DIR, f"{name}.txt")

        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_data)
            print("📁 최초 저장 완료")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            old_data = f.read()

        old_hash = generate_hash(old_data)

        if new_hash == old_hash:
            print("✅ 변경 없음")
            return

        print("🚨 변경 감지")

        old_articles = self.parser.parse_articles(old_data)
        new_articles = self.parser.parse_articles(new_data)

        changes = self.diff_engine.compare_articles(old_articles, new_articles)

        for c in changes:
            print(f"\n{c['article']} ({c['type']})")
            print(c["diff"][:300])

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_data)

        print("💾 업데이트 완료")

        if changes:

            print(f"\n===== {name} 변경 내용 =====")

            for c in changes:
                print(f"\n■ {c['article']} ({c['type']})")
                print(c["diff"][:300])

            # 🔥 AI 영향도 분석
            impact = self.impact_service.analyze(name, changes)

            # 🔥 HTML 리포트 생성
            html = self.report_service.generate_html(name, changes, impact)

            # 🔥 메일 발송
            self.mail_service.send_mail(
                subject=f"[법령 변경] {name}",
                html_body=html
            )