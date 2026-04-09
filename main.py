import sys
from app.services.monitoring_service import MonitoringService

if __name__ == "__main__":

    service = MonitoringService()

    if len(sys.argv) > 1:

        mode = sys.argv[1]

        if mode == "pdf":
            service.run_pdf_job()

        elif mode == "monitor":
            service.run()

        else:
            print("❌ 지원하지 않는 옵션")
    else:
        service.run()