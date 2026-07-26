import zipfile
import re

def extract_to_file(docx_path, out_file):
    try:
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml').decode('utf-8')
            text = re.sub('<[^>]+>', ' ', xml_content)
            text = re.sub('\s+', ' ', text)
            out_file.write(f"--- {docx_path} ---\n")
            out_file.write(text + "\n\n")
    except Exception as e:
        out_file.write(f"Error reading {docx_path}: {e}\n")

with open('D:/Phát hiện bệnh cây lúa/temp_docx_output.txt', 'w', encoding='utf-8') as f:
    extract_to_file("D:/Phát hiện bệnh cây lúa/Bao_Cao_Du_An.docx", f)
    extract_to_file("D:/Phát hiện bệnh cây lúa/Do_An_Nhan_Dien_Benh_Lua_Draft.docx", f)
