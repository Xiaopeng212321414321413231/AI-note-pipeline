c = open('src/ai_rewrite.py','r',encoding='utf-8').read()

# 找到并替换第93行附近的问题部分
old = "{topic_name and f'## 本文主题\n{topic_name}\n关键词：{keywords}' or ''}"
# 用简单的拼接代替 f-string
new = "'## 本文主题\n' + topic_name + '\n关键词：' + keywords if topic_name else ''"

c = c.replace(old, new)

# 如果上面没匹配到，可能是 \n 被编码成了实际换行
if old in c:
    c = c.replace(old, new)
    print('replaced with literal \\n')
else:
    # 尝试用实际换行符匹配
    old2 = "{topic_name and f'## 本文主题" + "\n" + "{topic_name}" + "\n" + "关键词：{keywords}' or ''}"
    c = c.replace(old2, new)
    print('replaced with actual newline')

open('src/ai_rewrite.py','w',encoding='utf-8').write(c)
print('OK')