from .base_parser import BaseParser


class AdmRulParser(BaseParser):

    def parse(self, data: dict) -> str:
        """
        행정규칙 파서 (미구현 상태)
        """
        title = data.get("법령명", "행정규칙")

        result = []
        result.append(f"# {title}\n")
        result.append("※ AdmRulParser는 아직 구현되지 않았습니다.\n")

        # TODO: 구조 정의 후 구현 예정

        return "\n".join(result)