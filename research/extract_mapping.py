import json
import re

txt = open(r'D:\Phát hiện bệnh cây lúa\frontend\src\pages\DiseaseLibrary.jsx', encoding='utf-8').read()
matches = re.findall(r'id:\s*"([^"]+)".*?name:\s*"([^"]+)"', txt, re.DOTALL)

print('| Mã chuẩn AI (Tên thư mục) | Tên hiển thị Tiếng Việt trên Web |')
print('|---|---|')
for m in matches:
    print(f'| `{m[0]}` | **{m[1]}** |')
