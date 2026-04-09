import requests
import json
import os
from app.config.settings import settings

# 캐시 파일 (권한 문제 해결)
CACHE_FILE = os.path.expanduser("~/law-monitor-data/law_ids.json")


class LawIdService:

    def __init__(self):
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

        # 1️⃣ 캐시
        if name in self.cache:
            print(f"📦 캐시 사용: {name} → {self.cache[name]}")
            return self.cache[name]

        print(f"🔍 ID 조회 중: {name}")

        url = "https://law.go.kr/DRF/lawSearch.do"

        params = {
            "OC": settings.LAW_API_KEY,
            "target": target,
            "query": name,
            "type": "JSON"
        }

        res = requests.get(url, params=params, timeout=60)
        res.raise_for_status()

        data = res.json()

        # =========================
        # 🔥 target별 구조 분기
        # =========================
        if target == "law":
            search = data.get("LawSearch", {})
        elif target == "admrul":
            search = data.get("AdmRulSearch", {})
        else:
            search = {}

        items = search.get(target, [])

        # 단건 → 리스트 변환
        if isinstance(items, dict):
            items = [items]

        if not items:
            print(json.dumps(data, indent=2, ensure_ascii=False))
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

    # =========================
    # 🔥 핵심 매칭 로직
    # =========================
    def _select_best_match(self, name, items, target):

        # 이름/ID 필드 분기
        def get_name(item):
            return item.get("법령명") if target == "law" else item.get("행정규칙명")

        def get_id(item):
            return item.get("법령ID") if target == "law" else item.get("행정규칙일련번호")

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
        norm_name = name.replace(" ", "")

        for item in items:
            item_name = get_name(item)

            if item_name and item_name.replace(" ", "") == norm_name:
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