class ImpactService:

    def analyze(self, law_name, changes):

        keywords = {
            "개인정보": "고객정보 처리 시스템 영향",
            "인증": "인증/로그인 시스템 영향",
            "거래": "결제/거래 시스템 영향",
            "보안": "보안 정책 영향",
            "접근통제": "권한 관리 영향"
        }

        impact_results = []

        for c in changes:
            text = c["diff"]

            for k, v in keywords.items():
                if k in text:
                    impact_results.append(f"- {k} 관련: {v}")

        if not impact_results:
            impact_results.append("- 일반 변경 (영향 낮음)")

        return "<br>".join(set(impact_results))