import zipfile
import xml.etree.ElementTree as ET
import sys

def get_docx_text(path):
    WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    TEXT = WORD_NAMESPACE + 't'
    PARA = WORD_NAMESPACE + 'p'
    
    try:
        with zipfile.ZipFile(path) as docx:
            tree = ET.parse(docx.open('word/document.xml'))
            root = tree.getroot()
            text_parts = []
            for paragraph in root.iter(PARA):
                texts = [node.text for node in paragraph.iter(TEXT) if node.text]
                if texts:
                    text_parts.append(''.join(texts))
            return '\n'.join(text_parts)
    except Exception as e:
        return f"Error reading docx: {e}"

if __name__ == "__main__":
    path = r"c:\manish\SchoolOfAI\session6_7\queries.docx"
    text = get_docx_text(path)
    print(text)
    # Also save it as a text file for easy access
    with open(r"c:\manish\SchoolOfAI\session6_7\queries.txt", "w", encoding="utf-8") as f:
        f.write(text)
