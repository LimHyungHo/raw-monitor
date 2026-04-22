import requests
import json
import os
from app.config.settings import settings

# 캐시 파일 (권한 문제 해결)
CACHE_FILE = os.path.expanduser("~/law-monitor-data/law_ids.json")


class LawIdService:

    def __init__(self):
        self.session = requests.Session()
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        self.cache = self._load_cache()

    # =========================
    # 캐시 로드
    # =========================
    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    # =========================
    # 캐시 저장
    # =========================
    def _save_cache(self):
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    # =========================
    # ID 조회 (메인 함수)
    # =========================
    def get_law_id(self, name, target):
        if not settings.LAW_API_KEY:
            raise ValueError("LAW_API_KEY가 설정되지 않았습니다. .env 또는 환경변수를 확인해 주세요.")

        cached_id = self._get_cached_id(name)
        if cached_id:
            print(f"📦 캐시 사용: {name} → {cached_id}")
            return cached_id

        print(f"🔍 ID 조회 중: {name}")

        items = self.search_items(target=target, query=name)

        if not items:
            raise Exception(f"법령 검색 실패: {name}")

        # =========================
        # 🔥 핵심: 정확 매칭
        # =========================
        law_id = self._select_best_match(name, items, target)

        if not law_id:
            raise Exception(f"ID 추출 실패: {name}")

        self.cache[name] = law_id
        self._save_cache()

        print(f"✅ ID 저장: {name} → {law_id}")

        return law_id

    def find_previous_version_metadata(
        self,
        *,
        name,
        target,
        current_effective_date=None,
        document_id=None,
    ):
        normalized_target = self._normalize_target(target)
        if normalized_target == "law" and document_id:
            print(
                f"🔎 이전 버전 후보 조회(LID): "
                f"name={name}, target={normalized_target}, document_id={document_id}, "
                f"current_effective_date={current_effective_date}"
            )
            items = self.search_items(target=normalized_target, lid=document_id)
        elif normalized_target == "admrul":
            print(
                f"🔎 이전 버전 후보 조회(admrul 연혁): "
                f"name={name}, target={normalized_target}, document_id={document_id}, "
                f"current_effective_date={current_effective_date}"
            )
            items = self.search_items(
                target=normalized_target,
                query=name,
                nw=2,
                # knd=3,
                sort="efdes",
            )
        else:
            print(
                f"🔎 이전 버전 후보 조회(query): "
                f"name={name}, target={normalized_target}, document_id={document_id}, "
                f"current_effective_date={current_effective_date}"
            )
            items = self.search_items(target=normalized_target, query=name)
        if not items:
            print(f"⚠️ 이전 버전 후보 없음: name={name}, target={normalized_target}")
            return None

        print(f"📚 목록조회 결과 건수: {len(items)}")

        normalized_name = self._normalize_name(name)
        current_date = self._normalize_date(current_effective_date)
        candidates = []

        for item in items:
            item_name = self._get_item_name(item, normalized_target)
            item_document_id = self._get_item_document_id(item, normalized_target)
            if (
                normalized_target != "admrul"
                and document_id
                and item_document_id
                and str(item_document_id) != str(document_id)
            ):
                continue
            if not document_id and self._normalize_name(item_name) != normalized_name:
                continue
            if normalized_target == "admrul" and self._normalize_name(item_name) != normalized_name:
                continue

            item_effective_date = self._normalize_date(
                self._get_item_effective_date(item, normalized_target)
            )
            if current_date and item_effective_date and item_effective_date >= current_date:
                continue

            candidates.append(
                {
                    "document_id": item_document_id,
                    "item_name": item_name,
                    "effective_date": self._get_item_effective_date(item, normalized_target),
                    "promulgation_date": self._get_item_promulgation_date(item, normalized_target),
                    "announcement_no": self._get_item_announcement_no(item, normalized_target),
                    "version_no": self._safe_int(self._get_item_version_no(item, normalized_target)),
                    "revision_type": item.get("제개정구분명"),
                    "detail_link": self._get_item_detail_link(item, normalized_target),
                    "raw": item,
                }
            )

        if not candidates:
            print(
                f"⚠️ 현재 시행일보다 이전 후보를 찾지 못함: "
                f"name={name}, document_id={document_id}, current_effective_date={current_effective_date}"
            )
            return None

        candidates.sort(
            key=lambda item: (
                self._normalize_date(item.get("effective_date")) or "",
                str(item.get("version_no") or ""),
            ),
            reverse=True,
        )
        selected = candidates[0]
        print(
            f"✅ 이전 버전 후보 선택: "
            f"name={selected.get('item_name')}, effective_date={selected.get('effective_date')}, "
            f"promulgation_date={selected.get('promulgation_date')}, "
            f"announcement_no={selected.get('announcement_no')}, version_no={selected.get('version_no')}"
        )
        return selected

    def search_items(self, *, target, query=None, lid=None, nw=None, knd=None, sort=None):
        normalized_target = self._normalize_target(target)
        data = self._search_api(
            target=normalized_target,
            query=query,
            lid=lid,
            nw=nw,
            knd=knd,
            sort=sort,
        )

        if normalized_target == "law":
            search = data.get("LawSearch", {})
        elif normalized_target == "admrul":
            search = data.get("AdmRulSearch", {})
        else:
            search = {}

        items = search.get("law" if normalized_target == "law" else normalized_target, [])
        if isinstance(items, dict):
            items = [items]
        return items

    def _search_api(self, *, target, query=None, lid=None, nw=None, knd=None, sort=None, retries=3):
        url = "https://law.go.kr/DRF/lawSearch.do"
        api_target = "eflaw" if target == "law" else target
        params = {
            "OC": settings.LAW_API_KEY,
            "target": api_target,
            "type": "JSON",
        }
        if query:
            params["query"] = query
        if lid:
            params["LID"] = lid
        if nw is not None:
            params["nw"] = nw
        if knd is not None:
            params["knd"] = knd
        if sort:
            params["sort"] = sort

        last_error = None
        for attempt in range(1, retries + 1):
            try:
                res = self.session.get(url, params=params, timeout=60)
                res.raise_for_status()
                return res.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt == retries:
                    break
                print(
                    f"⚠️ 검색 API 재시도 {attempt}/{retries - 1}: "
                    f"target={api_target}, query={query}, lid={lid}, nw={nw}, "
                    f"knd={knd}, sort={sort}, error={exc}"
                )

        raise last_error

    def _get_cached_id(self, name):
        if name in self.cache:
            return self.cache[name]

        normalized_name = self._normalize_name(name)
        for cached_name, cached_id in self.cache.items():
            if self._normalize_name(cached_name) == normalized_name:
                return cached_id

        return None

    def _normalize_name(self, name):
        return (name or "").replace(" ", "").strip()

    def _normalize_target(self, target):
        normalized_target = (target or "").strip().lower()
        if normalized_target in {"law", "eflaw"}:
            return "law"
        if normalized_target == "admrul":
            return "admrul"
        return normalized_target

    def _normalize_date(self, value):
        if not value:
            return None
        return str(value).replace(".", "").replace("-", "").strip()

    def _safe_int(self, value):
        if value in (None, ""):
            return None
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None

    def _get_item_name(self, item, target):
        if target == "law":
            return (
                item.get("법령명한글")
                or item.get("법령명")
                or item.get("법령명_한글")
                or ""
            )
        return item.get("행정규칙명") or ""

    def _get_item_document_id(self, item, target):
        if target == "law":
            return item.get("법령ID")
        return item.get("행정규칙일련번호") or item.get("행정규칙ID")

    def _get_item_effective_date(self, item, target):
        if target == "law":
            return item.get("시행일자")
        return item.get("시행일자") or item.get("발령일자")

    def _get_item_promulgation_date(self, item, target):
        if target == "law":
            return item.get("공포일자")
        return item.get("발령일자")

    def _get_item_announcement_no(self, item, target):
        if target == "law":
            return item.get("공포번호")
        return item.get("발령번호")

    def _get_item_version_no(self, item, target):
        if target == "law":
            return item.get("법령일련번호")
        return item.get("행정규칙일련번호")

    def _get_item_detail_link(self, item, target):
        if target == "law":
            return item.get("법령상세링크")
        return item.get("행정규칙상세링크")

    # =========================
    # 🔥 핵심 매칭 로직
    # =========================
    def _select_best_match(self, name, items, target):

        # 이름/ID 필드 분기
        def get_name(item):
            return self._get_item_name(item, target)

        def get_id(item):
            return self._get_item_document_id(item, target)

        # =========================
        # 1️⃣ 완전 일치 (최우선)
        # =========================
        for item in items:
            item_name = get_name(item)

            if item_name == name:
                print(f"🎯 완전 일치: {item_name}")
                return get_id(item)

        # =========================
        # 2️⃣ 공백 제거 일치
        # =========================
        norm_name = self._normalize_name(name)

        for item in items:
            item_name = get_name(item)

            if item_name and self._normalize_name(item_name) == norm_name:
                print(f"🎯 공백 무시 일치: {item_name}")
                return get_id(item)

        # =========================
        # 3️⃣ 포함 매칭 (세칙 제외)
        # =========================
        for item in items:
            item_name = get_name(item)

            if not item_name:
                continue

            # 🔥 핵심: 시행세칙 제거
            if "세칙" in item_name:
                continue

            if name in item_name:
                print(f"🎯 포함 매칭: {item_name}")
                return get_id(item)

        # =========================
        # 4️⃣ fallback
        # =========================
        print("⚠️ fallback 선택:", get_name(items[0]))
        return get_id(items[0])
