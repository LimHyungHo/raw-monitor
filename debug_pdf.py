import sys, os
from app.services.monitoring_service import MonitoringService
from app.collectors.law_api_collector import LawAPICollector
from app.parsers.law_parser import LawParser
from app.services.pdf_service import PdfService

# 데이터 저장 경로 설정
DATA_DIR = os.path.expanduser("~/law-monitor-data/")

if __name__ == "__main__":
	print("PDF 디버그 모드로 실행")

	# service = MonitoringService()
	collector = LawAPICollector()
	parser = LawParser()
	pdf_service = PdfService() # 생성자에서 초기화 권장

	# 데이터 저장 디렉토리 생성
	os.makedirs(DATA_DIR, exist_ok=True)