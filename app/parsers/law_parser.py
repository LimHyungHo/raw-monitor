import re

class LawParser:

    def parse_full_text(self, text):

        # HTML 태그 제거
        text = re.sub(r"<[^>]+>", "", text)

        # 불필요 공백 제거
        text = re.sub(r"\n+", "\n", text)

        return text.strip()

    def split_articles(self, text):

        pattern = r"(제\d+조(?:의\d+)?\s*\(.*?\).*?)(?=제\d+조|\Z)"
        matches = re.findall(pattern, text, re.DOTALL)

        return matches