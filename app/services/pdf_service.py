import os
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

class PdfService:
    def __init__(self):
        # 1. 한글 폰트 등록 (파일 경로가 정확해야 합니다)
        # 프로젝트 루트에 fonts 폴더가 있다고 가정합니다.
        self.font_name = "NanumGothic"
        font_path = os.path.join(os.getcwd(), "fonts", "NanumGothic.ttf")
        
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont(self.font_name, font_path))
        else:
            # 폰트 파일이 없을 경우 시스템 폰트 경로 등을 탐색하는 로직이 필요할 수 있습니다.
            print(f"⚠️ 경고: 폰트 파일을 찾을 수 없습니다: {font_path}")

        # 2. 스타일 정의
        self.title_style = ParagraphStyle(
            name="KoreanTitle",
            fontName=self.font_name,
            fontSize=18,
            leading=22,
            alignment=1,  # 중앙 정렬
            spaceAfter=20
        )

        self.article_style = ParagraphStyle(
            name="ArticleTitle",
            fontName=self.font_name,
            fontSize=12,
            leading=16,
            textColor="#2E5984", # 조문 제목에 색상 부여
            spaceBefore=10,
            spaceAfter=5,
            bold=True
        )

        self.body_style = ParagraphStyle(
            name="KoreanBody",
            fontName=self.font_name,
            fontSize=10,
            leading=15,
            leftIndent=10,
            firstLineIndent=0,
            spaceAfter=3
        )

    def generate_pdf(self, law_name, content):
        """
        텍스트 내용을 받아 PDF 파일로 저장합니다.
        """
        # 저장 경로 설정 (사용자 홈 디렉토리 내 law-monitor-data)
        save_dir = os.path.expanduser("~/law-monitor-data/")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        file_path = os.path.join(save_dir, f"{law_name}.pdf")
        
        # 문서 템플릿 생성
        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )

        story = []

        # 3. 데이터 전처리
        # 만약 HTML이 들어온 경우를 대비해 태그 제거 로직 유지
        if "<" in content and ">" in content:
            clean_text = self._clean_html(content)
        else:
            clean_text = content

        # 4. PDF 내용 구성 (Story building)
        # 제목 추가
        story.append(Paragraph(f"<b>{self._escape(law_name)}</b>", self.title_style))
        story.append(Spacer(1, 10))

        # 줄 단위로 읽으며 조문(제N조) 단위로 스타일 적용
        lines = clean_text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # '제 1 조' 또는 '제1조'로 시작하는 경우 조문 제목 스타일 적용
            if re.match(r"^제\s*\d+\s*조", line):
                story.append(Spacer(1, 5))
                story.append(Paragraph(self._escape(line), self.article_style))
            else:
                # 일반 본문 내용
                story.append(Paragraph(self._escape(line), self.body_style))

        # 5. PDF 파일 쓰기
        try:
            doc.build(story)
            print(f"✅ PDF 생성 완료: {file_path}")
        except Exception as e:
            print(f"❌ PDF 빌드 중 오류 발생: {e}")
            return None

        return file_path

    def _clean_html(self, html):
        """HTML 태그 제거 및 텍스트 정규화"""
        # script, style 제거
        html = re.sub(r"<(script|style).*?>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # 나머지 모든 태그 제거
        text = re.sub(r"<[^>]+>", "", html)
        # 특수문자 변환
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        # 과도한 공백 정리
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()

    def _escape(self, text):
        """ReportLab Paragraph 내에서 오류를 일으킬 수 있는 특수문자 이스케이프"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")