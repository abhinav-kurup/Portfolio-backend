import re
import markdown

def to_html(md_content: str) -> str:
    return markdown.markdown(md_content, extensions=["fenced_code", "tables"])

def extract_summary(md_content: str, max_chars: int = 200) -> str:
    text = re.sub(r"[#*`>\-!\[\]()]", "", md_content)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars] + "..." if len(text) > max_chars else text

def calculate_reading_time(md_content: str) -> int:
    word_count = len(md_content.split())
    minutes = max(1, round(word_count / 200))
    return minutes