import os
import re
import html
from pathlib import Path

class PdfService:
    def __init__(self):
        self.font_name = "NanumGothic"
        self.font_path = Path(__file__).resolve().parents[2] / "fonts" / "NanumGothic.ttf"

    def generate_pdf(self, law_name, content):
        save_dir = os.path.expanduser("~/law-monitor-data/")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        safe_name = self._sanitize_filename(law_name) or "document"
        file_path = os.path.join(save_dir, f"{safe_name}.pdf")

        try:
            self._generate_with_reportlab(law_name, content, file_path)
            print(f"✅ PDF 생성 완료: {file_path}")
            return file_path
        except Exception as e:
            print(f"⚠️ reportlab PDF 생성 실패, weasyprint로 재시도합니다: {e}")

        try:
            self._generate_with_weasyprint(law_name, content, file_path)
            print(f"✅ PDF 생성 완료: {file_path}")
        except Exception as e:
            print(f"❌ PDF 빌드 중 오류 발생: {e}")
            return None

        return file_path

    def generate_pdf_from_parsed_data(self, law_name, parsed_data, version_label=None):
        save_dir = os.path.expanduser("~/law-monitor-data/")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        title = str(law_name or "").strip()
        if version_label:
            title = f"{title}_{version_label}"

        safe_name = self._sanitize_filename(title) or "document"
        file_path = os.path.join(save_dir, f"{safe_name}.pdf")

        try:
            html_document = self._build_html_document_from_parsed_data(law_name, parsed_data)
            self._write_weasyprint_pdf(html_document, file_path)
            print(f"✅ PDF 생성 완료: {file_path}")
            return file_path
        except Exception as exc:
            print(f"⚠️ 구조화 PDF 생성 실패, 텍스트 PDF로 재시도합니다: {exc}")

        raw_text = self._build_fallback_text(parsed_data)
        return self.generate_pdf(title, raw_text)

    def _sanitize_filename(self, value):
        sanitized = re.sub(r'[\\/:*?"<>|]+', "_", str(value or "").strip())
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
        return sanitized[:120]

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
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _build_html_document_from_parsed_data(self, law_name, parsed_data):
        sections = [
            "<!DOCTYPE html>",
            "<html lang='ko'>",
            "<head><meta charset='utf-8'></head>",
            "<body>",
            f"<h1>{html.escape(str(law_name or ''), quote=False)}</h1>",
        ]

        for article in parsed_data.get("articles", []):
            if not isinstance(article, dict):
                continue

            heading = self._build_article_heading(article)
            if heading:
                sections.append(f"<h2>{html.escape(heading, quote=False)}</h2>")

            content = str(article.get("content") or "").strip()
            for block in self._text_to_html_blocks(content):
                sections.append(block)

        addenda = parsed_data.get("addenda") or []
        addenda_html = self._build_addenda_html(addenda)
        if addenda_html:
            sections.append("<section class='appendix-block'>")
            sections.append("<h2>부칙</h2>")
            sections.extend(addenda_html)
            sections.append("</section>")

        for appendix in self._flatten_appendix(parsed_data.get("appendix", [])):
            if not isinstance(appendix, dict):
                continue
            title = str(appendix.get("title") or "").strip()
            content = appendix.get("content")
            if not title and not content:
                continue

            sections.append("<section class='appendix-block'>")
            if title:
                sections.append(f"<h2>{html.escape(title, quote=False)}</h2>")
            sections.extend(self._appendix_content_to_html(content))
            sections.append("</section>")

        sections.append("</body></html>")
        return "\n".join(sections)

    def _build_article_heading(self, article):
        number = str(article.get("number") or "").strip()
        title = str(article.get("title") or "").strip()
        if number and title:
            return f"제{number}조({title})"
        if number:
            return f"제{number}조"
        if title:
            return title
        return ""

    def _text_to_html_blocks(self, text):
        blocks = []
        for line in str(text or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            escaped = html.escape(stripped, quote=False)
            if stripped.startswith("### "):
                blocks.append(f"<h4>{html.escape(stripped[4:].strip(), quote=False)}</h4>")
            elif stripped.startswith("## "):
                blocks.append(f"<h3>{html.escape(stripped[3:].strip(), quote=False)}</h3>")
            elif stripped.startswith("# "):
                blocks.append(f"<h2>{html.escape(stripped[2:].strip(), quote=False)}</h2>")
            else:
                blocks.append(f"<p>{escaped}</p>")
        return blocks

    def _build_addenda_html(self, addenda):
        if isinstance(addenda, str):
            addenda = [addenda]
        blocks = []
        for item in addenda or []:
            blocks.extend(self._text_to_html_blocks(item))
        return blocks

    def _appendix_content_to_html(self, content):
        if isinstance(content, list):
            blocks = []
            for item in content:
                blocks.extend(self._text_to_html_blocks(item))
            return blocks

        raw = str(content or "").strip()
        if not raw:
            return []

        if "<table" in raw or "<div" in raw or "<pre" in raw or "<p>" in raw:
            return [raw]

        return self._text_to_html_blocks(raw)

    def _flatten_appendix(self, appendix):
        flat = []
        for item in appendix or []:
            if isinstance(item, list):
                flat.extend(self._flatten_appendix(item))
            else:
                flat.append(item)
        return flat

    def _build_fallback_text(self, parsed_data):
        chunks = []
        for article in parsed_data.get("articles", []):
            if not isinstance(article, dict):
                continue
            heading = self._build_article_heading(article)
            if heading:
                chunks.append(heading)
            content = str(article.get("content") or "").strip()
            if content:
                chunks.append(content)

        addenda = parsed_data.get("addenda") or []
        if isinstance(addenda, str):
            addenda = [addenda]
        if addenda:
            chunks.append("부칙")
            chunks.extend(str(item) for item in addenda if item)

        for appendix in self._flatten_appendix(parsed_data.get("appendix", [])):
            if not isinstance(appendix, dict):
                continue
            title = str(appendix.get("title") or "").strip()
            content = appendix.get("content")
            if title:
                chunks.append(title)
            if isinstance(content, list):
                chunks.extend(str(item) for item in content if item)
            elif content:
                chunks.append(self._clean_html(str(content)))

        return "\n\n".join(chunk for chunk in chunks if chunk)

    def _generate_with_reportlab(self, law_name, content, file_path):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        if self.font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(self.font_name, str(self.font_path)))
            except Exception:
                pass

        title_style = ParagraphStyle(
            name="KoreanTitle",
            fontName=self.font_name,
            fontSize=18,
            leading=22,
            alignment=1,
            spaceAfter=20,
        )
        article_style = ParagraphStyle(
            name="ArticleTitle",
            fontName=self.font_name,
            fontSize=12,
            leading=16,
            textColor="#2E5984",
            spaceBefore=10,
            spaceAfter=5,
            bold=True,
        )
        body_style = ParagraphStyle(
            name="KoreanBody",
            fontName=self.font_name,
            fontSize=10,
            leading=15,
            leftIndent=10,
            firstLineIndent=0,
            spaceAfter=3,
        )

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50,
        )

        clean_text = self._clean_html(content) if "<" in content and ">" in content else content
        story = [Paragraph(f"<b>{self._escape(law_name)}</b>", title_style), Spacer(1, 10)]

        for line in clean_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.match(r"^제\s*\d+\s*조", line):
                story.append(Spacer(1, 5))
                story.append(Paragraph(self._escape(line), article_style))
            else:
                story.append(Paragraph(self._escape(line), body_style))

        doc.build(story)

    def _generate_with_weasyprint(self, law_name, content, file_path):
        clean_text = self._clean_html(content) if "<" in content and ">" in content else str(content or "")
        body_lines = []
        for line in clean_text.split("\n"):
            text = line.strip()
            if not text:
                continue
            escaped = html.escape(text, quote=False)
            if re.match(r"^제\s*\d+\s*조", text):
                body_lines.append(f"<h2>{escaped}</h2>")
            else:
                body_lines.append(f"<p>{escaped}</p>")

        title_html = f"<h1>{html.escape(str(law_name or ''), quote=False)}</h1>"
        full_html = "\n".join(
            [
                "<!DOCTYPE html>",
                "<html lang='ko'>",
                "<head><meta charset='utf-8'></head>",
                "<body>",
                title_html,
                *body_lines,
                "</body></html>",
            ]
        )
        self._write_weasyprint_pdf(full_html, file_path)

    def _write_weasyprint_pdf(self, full_html, file_path):
        from weasyprint import CSS, HTML

        font_face = ""
        if self.font_path.exists():
            font_url = self.font_path.as_uri()
            font_face = (
                "@font-face {"
                f"font-family: '{self.font_name}'; src: url('{font_url}');"
                "}"
            )

        css = CSS(
            string="\n".join(
                [
                    "@page { size: A4; margin: 16mm 14mm 18mm; }",
                    font_face,
                    (
                        "body { font-family: 'NanumGothic', sans-serif; font-size: 11pt; "
                        "line-height: 1.65; color: #111; }"
                    ),
                    "h1 { font-size: 18pt; text-align: center; margin-bottom: 16px; }",
                    "h2 { font-size: 12pt; color: #2E5984; margin-top: 12px; margin-bottom: 6px; }",
                    "h3 { font-size: 11pt; margin-top: 10px; margin-bottom: 6px; }",
                    "h4 { font-size: 10.5pt; margin-top: 8px; margin-bottom: 4px; }",
                    "p { margin: 0.2em 0 0.5em; white-space: pre-wrap; overflow-wrap: anywhere; }",
                    ".appendix-block { margin-top: 1.1em; }",
                    ".appendix-prefix p { margin: 0.15em 0; white-space: pre-wrap; }",
                    ".law-table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 12px; margin: 0.6em 0 1em; }",
                    ".law-table th, .law-table td { border: 1px solid #333; padding: 8px 10px; vertical-align: top; word-break: break-word; overflow-wrap: anywhere; white-space: pre-wrap; line-height: 1.5; }",
                    ".law-table th { background-color: #f2f2f2; font-weight: bold; text-align: center; }",
                    "thead { display: table-header-group; }",
                    "tfoot { display: table-footer-group; }",
                    "tr, td, th { page-break-inside: avoid; }",
                    ".ascii-form-panels { display: block; margin: 0.4em 0 1em; }",
                    ".ascii-form-panel { display: block; width: 100%; margin: 0 0 10px; break-inside: avoid-page; page-break-inside: avoid; }",
                    ".ascii-form-panel pre, .ascii-form-raw { margin: 0; padding: 8px; border: 1px solid #777; font-family: monospace; font-size: 8.4pt; line-height: 1.2; white-space: pre; overflow: hidden; }",
                ]
            )
        )
        HTML(string=full_html, base_url=str(self.font_path.parent)).write_pdf(file_path, stylesheets=[css])
