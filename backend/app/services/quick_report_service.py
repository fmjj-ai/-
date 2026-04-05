from __future__ import annotations

from typing import Any, Dict, List, Optional
from html import escape


class QuickReportService:
    """快速 HTML 报告服务。"""

    @staticmethod
    def get_capabilities() -> Dict[str, Any]:
        return {
            "service": "quick_reports",
            "description": "提供快速 HTML 分析报告能力，不替代现有导出体系。",
            "formats": ["html"],
            "blocks": ["overview", "descriptive_stats", "charts", "highlights", "notes"],
        }

    @staticmethod
    def get_generation_steps() -> List[Dict[str, Any]]:
        return [
            {"step": 1, "name": "collect_dataset_context"},
            {"step": 2, "name": "assemble_report_blocks"},
            {"step": 3, "name": "render_html_template"},
            {"step": 4, "name": "persist_or_download_artifact"},
        ]

    @staticmethod
    def render_html_report(title: str, dataset_name: str, blocks: List[Dict[str, Any]]) -> str:
        sections: List[str] = []
        for block in blocks:
            block_title = escape(str(block.get("title") or "内容块"))
            block_type = block.get("type")
            if block_type == "overview":
                items = block.get("items") or {}
                rows = "".join(
                    f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in items.items()
                )
                sections.append(f"<section><h2>{block_title}</h2><table>{rows}</table></section>")
            elif block_type == "descriptive_stats":
                rows = []
                for row in block.get("rows") or []:
                    cols = "".join(f"<td>{escape(str(v))}</td>" for v in row.values())
                    rows.append(f"<tr>{cols}</tr>")
                header = "".join(f"<th>{escape(str(k))}</th>" for k in ((block.get("rows") or [{}])[0].keys() if block.get("rows") else []))
                sections.append(f"<section><h2>{block_title}</h2><table><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table></section>")
            elif block_type == "chart":
                image_url = block.get("image_url") or ""
                caption = escape(str(block.get("caption") or ""))
                img_html = f"<img src=\"{escape(str(image_url))}\" alt=\"chart\" style=\"max-width:100%;border-radius:8px;\" />" if image_url else ""
                sections.append(f"<section><h2>{block_title}</h2>{img_html}<p>{caption}</p></section>")
            else:
                content = escape(str(block.get("content") or ""))
                sections.append(f"<section><h2>{block_title}</h2><p>{content}</p></section>")

        return f"""
<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 32px; color: #222; background: #fafafa; }}
    .wrap {{ max-width: 960px; margin: 0 auto; background: #fff; padding: 32px; border-radius: 16px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }}
    h1, h2 {{ color: #1677ff; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #e5e7eb; padding: 10px 12px; text-align: left; }}
    th {{ background: #f5f7fa; width: 220px; }}
    section {{ margin-bottom: 28px; }}
    .meta {{ color: #666; margin-bottom: 24px; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <h1>{escape(title)}</h1>
    <div class=\"meta\">数据集：{escape(dataset_name)}</div>
    {''.join(sections)}
  </div>
</body>
</html>
""".strip()
