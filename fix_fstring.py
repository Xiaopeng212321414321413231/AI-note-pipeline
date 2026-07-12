with open('src/ai_rewrite.py','r',encoding='utf-8') as f:
    c = f.read()

old = "topic_name and f'## 本文主题\n{topic_name}\n关键词：{keywords}' or ''"
new = "'## 本文主题\n' + topic_name + '\n关键词：' + keywords if topic_name else ''"
c = c.replace(old, new)

with open('src/ai_rewrite.py','w',encoding='utf-8') as f:
    f.write(c)
print('OK')