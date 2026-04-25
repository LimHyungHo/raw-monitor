from app.collectors.law_api_collector import LawAPICollector
from app.repositories.monitoring_target_repository import MonitoringTargetRepository
from app.services.law_id_service import LawIdService
from app.services.mail_service import MailService
from app.services.monitoring_service import MonitoringService
from app.services.pdf_service import PdfService


class LatestPdfService:
    def __init__(self):
        self.collector = LawAPICollector()
        self.target_repository = MonitoringTargetRepository()
        self.id_service = LawIdService()
        self.monitoring_service = MonitoringService()
        self.pdf_service = PdfService()
        self.mail_service = MailService()

    def send_latest_pdf(self, target_id):
        target = self.target_repository.get_target_by_id(target_id)
        if not target:
            raise ValueError("대상을 찾지 못했습니다.")

        target_type = self.monitoring_service._normalize_target_type(target.get("target_type"))
        document_name = (target.get("document_name") or "").strip()
        if not document_name:
            raise ValueError("법령명이 비어 있습니다.")

        document_id = (target.get("document_id") or "").strip()
        if not document_id:
            document_id = self.id_service.get_law_id(document_name, target_type)
            self.target_repository.update_target(target_id, document_id=document_id)

        raw_json = self.collector.fetch_json(target_type, document_id)
        self.monitoring_service._validate_raw_json(raw_json, target_type, document_name, document_id)
        parsed_data = self.monitoring_service._parse_document(raw_json, target_type)
        raw_text = self.monitoring_service._build_raw_text(parsed_data)
        if not raw_text.strip():
            raise ValueError("PDF로 만들 본문을 찾지 못했습니다.")

        metadata = self.monitoring_service._extract_version_metadata(raw_json, target_type, document_id)
        version_date = metadata.get("effective_date") or metadata.get("promulgation_date") or "latest"
        pdf_path = self.pdf_service.generate_pdf_from_parsed_data(
            document_name,
            parsed_data,
            version_label=version_date,
        )
        if not pdf_path:
            raise ValueError("PDF 생성에 실패했습니다.")

        recipient_email = (target.get("notify_email") or "").strip()
        if not recipient_email:
            raise ValueError("수신 이메일이 설정되지 않았습니다.")

        subject = f"[RAW-MONITOR] {document_name} 최신 법령 PDF"
        body_lines = [
            f"{document_name} 최신 법령 전문 PDF를 첨부합니다.",
            f"- 대상 유형: {target_type}",
            f"- 문서 ID: {document_id}",
        ]
        if metadata.get("effective_date"):
            body_lines.append(f"- 시행일자: {metadata['effective_date']}")
        if metadata.get("promulgation_date"):
            body_lines.append(f"- 공포/발령일자: {metadata['promulgation_date']}")
        if metadata.get("announcement_no"):
            body_lines.append(f"- 공포/발령번호: {metadata['announcement_no']}")

        self.mail_service.send_mail_with_attachments(
            subject=subject,
            body="\n".join(body_lines),
            file_paths=[pdf_path],
            recipient_email=recipient_email,
        )

        return {
            "target": target,
            "recipient_email": recipient_email,
            "pdf_path": pdf_path,
            "document_id": document_id,
            "metadata": metadata,
        }
