import sys
from app.config.settings import settings
from app.services.monitoring_service import MonitoringService
from app.web import create_app

if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == "web":
            app = create_app()
            app.run(
                host=settings.WEB_HOST,
                port=settings.WEB_PORT,
                debug=settings.WEB_DEBUG,
            )

        else:
            service = MonitoringService()

            if mode == "pdf":
                service.run_pdf_job()

            elif mode == "monitor":
                service.run()

            else:
                print("❌ 지원하지 않는 옵션")
    else:
        service = MonitoringService()
        service.run()
