class ReportService:

    def generate_html(self, law_name, changes, impact):

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial; }}
                .add {{ color: green; }}
                .del {{ color: red; text-decoration: line-through; }}
                .box {{ border:1px solid #ccc; padding:10px; margin:10px; }}
                .impact {{ background:#f5f5f5; padding:10px; }}
            </style>
        </head>
        <body>

        <h2>📢 법령 변경 리포트</h2>
        <h3>{law_name}</h3>

        <div class="impact">
        <h3>📊 영향도 분석</h3>
        {impact}
        </div>
        """

        for c in changes:
            html += f"<div class='box'>"
            html += f"<h4>{c['article']} ({c['type']})</h4>"

            for line in c["diff"].split("\n"):
                if line.startswith("+"):
                    html += f"<div class='add'>{line}</div>"
                elif line.startswith("-"):
                    html += f"<div class='del'>{line}</div>"
                else:
                    html += f"<div>{line}</div>"

            html += "</div>"

        html += "</body></html>"

        return html