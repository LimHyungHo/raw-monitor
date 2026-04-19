import requests
from urllib.parse import parse_qs, urljoin, urlparse

from app.config.settings import settings


class LawAPICollector:
    def __init__(self):
        self.session = requests.Session()

    def _request(self, response_type, target, law_id, timeout=60, retries=3):
        if not settings.LAW_API_KEY:
            raise ValueError("LAW_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해 주세요.")

        url = "https://law.go.kr/DRF/lawService.do"
        params = {
            "OC": settings.LAW_API_KEY,
            "target": target,
            "ID": law_id,
            "type": response_type,
        }

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                res = self.session.get(url, params=params, timeout=timeout)
                res.raise_for_status()
                return res
            except requests.RequestException as exc:
                last_error = exc
                if attempt == retries:
                    break
                print(
                    f"⚠️ API 재시도 {attempt}/{retries - 1}: "
                    f"target={target}, id={law_id}, error={exc}"
                )

        raise last_error

    # 🔍 JSON (diff용)
    def fetch_json(self, target, law_id):
        res = self._request("JSON", target, law_id)
        return res.json()

    def fetch_json_by_detail_link(self, detail_link, timeout=60, retries=3):
        if not settings.LAW_API_KEY:
            raise ValueError("LAW_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해 주세요.")

        normalized_link = self._normalize_detail_link(detail_link)
        parsed = urlparse(normalized_link)
        params = {
            key: values[-1]
            for key, values in parse_qs(parsed.query).items()
            if values
        }
        params["OC"] = settings.LAW_API_KEY
        params["type"] = "JSON"

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                res = self.session.get(
                    f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    params=params,
                    timeout=timeout,
                )
                res.raise_for_status()
                return res.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt == retries:
                    break
                print(
                    f"⚠️ 상세링크 API 재시도 {attempt}/{retries - 1}: "
                    f"detail_link={normalized_link}, error={exc}"
                )

        raise last_error

    # 📄 HTML (PDF용)
    def fetch_html(self, target, law_id):
        res = self._request("HTML", target, law_id)
        return res.text

    def _normalize_detail_link(self, detail_link):
        raw_link = (detail_link or "").strip()
        if not raw_link:
            raise ValueError("상세 링크가 비어 있습니다.")

        if raw_link.startswith("http://") or raw_link.startswith("https://"):
            return raw_link

        if raw_link.startswith(":///"):
            raw_link = raw_link[3:]

        if raw_link.startswith("//"):
            return f"https:{raw_link}"

        return urljoin("https://law.go.kr", raw_link)
