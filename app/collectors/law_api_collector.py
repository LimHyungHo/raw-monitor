import requests
from app.config.settings import settings


class LawAPICollector:

    # 🔍 JSON (diff용)
    def fetch_json(self, target, law_id):

        url = "https://law.go.kr/DRF/lawService.do"

        params = {
            "OC": settings.LAW_API_KEY,
            "target": target,
            "ID": law_id,
            "type": "JSON"
        }

        res = requests.get(url, params=params, timeout=60)
        res.raise_for_status()

        return res.json()

    # 📄 HTML (PDF용)
    def fetch_html(self, target, law_id):

        url = "https://law.go.kr/DRF/lawService.do"

        params = {
            "OC": settings.LAW_API_KEY,
            "target": target,
            "ID": law_id,
            "type": "HTML"
        }

        res = requests.get(url, params=params, timeout=60)
        res.raise_for_status()

        return res.text