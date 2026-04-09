from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import re


class PdfService:

    def __init__(self):

        # =========================
        # 한글 폰트 등록
        # =========================
		# 🔥 한글 폰트 등록 (중요)
        font_path = "./fonts/NanumGothic.ttf" # 실제 폰트 파일 경로로 변경
        pdfmetrics.registerFont(TTFont("NanumGothic", font_path))

        # doc = SimpleDocTemplate(filename)
        # styles = getSampleStyleSheet()

		# 🔥 한글 스타일 생성
		# title_style = ParagraphStyle(
		#     name="KoreanTitle",
		#     parent=styles["Heading2"],
		#     fontName="MalgunGothic"
		# )

		# body_style = ParagraphStyle(
		#     name="KoreanBody",
		#     parent=styles["BodyText"],
		#     fontName="MalgunGothic"
		# )
        # title_style = ParagraphStyle(
		# 	name="KoreanTitle",
		# 	fontName="NanumGothic",
		# 	fontSize=16,
		# 	leading=20
		# )

        body_style = ParagraphStyle(
			name="KoreanBody",
			fontName="NanumGothic",
			fontSize=11,
			leading=15
		)
        # font_path = os.path.join("fonts", "NotoSansKR-Regular.otf")
        # pdfmetrics.registerFont(TTFont("Korean", font_path))

        # # =========================
        # # 스타일 정의
        # # =========================
        self.title_style = ParagraphStyle(
            name="KoreanTitle",
            fontName="NanumGothic",
            fontSize=16,
            leading=20,
            spaceAfter=12
        )

        self.article_style = ParagraphStyle(
            name="Article",
            fontName="NanumGothic",
            fontSize=12,
            leading=16,
            spaceAfter=6
        )

        self.body_style = ParagraphStyle(
            name="KoreanBody",
            fontName="NanumGothic",
            fontSize=10,
            leading=14,
            leftIndent=10,
            spaceAfter=2
        )

    # =========================
    # PDF 생성
    # =========================
    def generate_pdf(self, law_name, html):

        file_path = os.path.expanduser(f"~/law-monitor-data/{law_name}.pdf")

        doc = SimpleDocTemplate(file_path)

        story = []

        # 🔥 HTML → 텍스트 변환
        text = self._clean_html(html)

        # 🔥 조문 분리
        articles = self._split_articles(text)
	   # 🔥 fallback (핵심)
        if not articles:
           print("⚠️ 조문 분리 실패 → 전체 텍스트 사용")
           articles = [text]

        # =========================
        # 제목
        # =========================
        story.append(Paragraph(f"<b>{law_name}</b>", self.title_style))
        story.append(Spacer(1, 20))

        # =========================
        # 조문 렌더링
        # =========================
        for article in articles:

            lines = article.split("\n")

            # 조문 제목 (제1조...)
            title = lines[0]
            story.append(Paragraph(f"<b>{self._escape(title)}</b>", self.article_style))

            # 본문
            for line in lines[1:]:
                if line.strip():
                    story.append(Paragraph(self._escape(line), self.body_style))

            story.append(Spacer(1, 10))

        doc.build(story)

        print(f"📄 PDF 생성 완료: {file_path}")

        return file_path

    # =========================
    # HTML 정리 (핵심)
    # =========================
    # def _clean_html(self, html):

    #     # script/style 제거
    #     html = re.sub(r"<script.*?>.*?</script>", "", html, flags=re.DOTALL)
    #     html = re.sub(r"<style.*?>.*?</style>", "", html, flags=re.DOTALL)

    #     # HTML 태그 제거
    #     text = re.sub(r"<[^>]+>", "", html)

    #     # 특수문자 정리
    #     text = text.replace("&nbsp;", " ")
    #     text = text.replace("&lt;", "<").replace("&gt;", ">")

    #     # 줄 정리
    #     text = re.sub(r"\n+", "\n", text)

    #     return text.strip()
    def _clean_html(self, html):

       import re

       html = re.sub(r"<[^>]+>", "", html)

		# 🔥 제X조 앞에 줄바꿈 추가
       html = re.sub(r"(제\d+조)", r"\n\1", html)

       html = re.sub(r"\n+", "\n", html)

       return html.strip()
    # =========================
    # 조문 분리
    # =========================
    def _split_articles(self, text):

        pattern = r"(제\d+조(?:의\d+)?\s*\(.*?\).*?)(?=제\d+조|\Z)"
        return re.findall(pattern, text, re.DOTALL)

    # =========================
    # HTML escape
    # =========================
    def _escape(self, text):
        return text.replace("<", "&lt;").replace(">", "&gt;")