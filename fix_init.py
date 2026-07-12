with open('src/main.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('chroma_path=CHROMA_DB_PATH', 'db_path=CHROMA_DB_PATH')
with open('src/main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK')