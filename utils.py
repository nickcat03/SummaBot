from docx import Document
from pptx import Presentation
import re
import aiohttp
import io

def extract_text_from_docx(docx_bytes):
    doc = Document(io.BytesIO(docx_bytes))
    text = ''
    for paragraph in doc.paragraphs:
        text += paragraph.text + '\n'
    return text

def extract_text_from_pptx(pptx_bytes):
    prs = Presentation(io.BytesIO(pptx_bytes))
    text = ''
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + '\n'
    return text

async def download_file(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                # Handle error responses here
                raise ValueError(f"Failed to download file: {response.status}")

def extract_video_id(url):
    match = re.search(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    else:
        return None
    
def get_length(word_count):
    if word_count < 150:
        return "very short"
    elif word_count < 200:
        return "short"
    elif word_count < 300:
        return "long"
    else:
        return "very long"