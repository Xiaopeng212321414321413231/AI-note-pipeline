# Obsidian Web Clipper 架构分析

> 分析时间：2026-07-22
> 目的：理解官方 Web Clipper "快"的本质，反哺 B站视频流水线优化

---

## 一、核心架构：纯客户端流水线，零服务端

```
浏览器已加载页面 → 扩展读取已渲染 DOM → 就地处理 → 直接写入 Obsidian
       ↑                           ↑
  没有网络回传                  没有中转服务器
```

**关键差异：Web Clipper 不走网络。** 页面已经在浏览器 DOM 里了，它只是从中"拿"值，而不是再去下载一遍。

---

## 二、四个加速引擎

### 1️⃣ Readability.js —— 内容提取的核武器

Mozilla 打磨十几年的算法（与 Firefox 阅读模式同源）：

- **DOM 评分**：遍历 HTML 节点，给每个元素打分
  - `<article>` +20 分，`<nav>` -10 分，`<div class="ad">` -50 分
- **主干识别**：找到分数最高的内容块，一刀砍掉侧栏、广告、页脚、弹窗
- **不解析 CSS**：只读 DOM 结构，不做样式计算

→ **毫秒级**从杂乱页面里捞到正文。

### 2️⃣ Turndown.js —— HTML→Markdown 快过解析器

大部分方案：HTML → 解析 AST → 序列化 Markdown（两遍遍历）

Turndown：直接操作 DOM tree，CSS 选择器匹配规则，**一次遍历完成转换**

→ 没有中间 AST，没有二次遍历，**复杂度 O(n)**

### 3️⃣ 视频内容：读元数据，不是下载视频

这是"连视频都很快"的真相——**它根本不下视频文件**。

视频页面 `<head>` 里嵌好了结构化元数据：

```html
<!-- Open Graph -->
<meta property="og:video" content="https://..." />
<meta property="og:title" content="..." />
<meta property="og:description" content="..." />

<!-- JSON-LD (schema.org) -->
<script type="application/ld+json">
{ "@type": "VideoObject", "name": "...", "duration": "PT10M", "thumbnailUrl": "..." }
</script>

<!-- oEmbed endpoint -->
<link rel="alternate" type="application/json+oembed" href="..." />
```

Web Clipper 从 DOM 里直接 `querySelector` 这些标签 → 读标题、描述、封面图 URL、嵌入链接 → 写入笔记。**全程没有网络请求，没有视频转码，没有 ffmpeg**。

### 4️⃣ 模板系统：已知网站走快车道

对 YouTube、Vimeo、Reddit、Twitter 等已知平台有专用模板：

- 不需要 Readability 去猜正文在哪里
- 直接走到固定的 DOM 路径取值
- **跳过所有启发式分析，直接 O(1) 读取**

---

## 三、架构对比

| 步骤 | 普通方案 | Web Clipper |
|------|---------|-------------|
| 获取内容 | HTTP 请求（100-500ms） | 从已加载的 DOM 读（0ms） |
| 解析 HTML | html2ast 全量解析 | Readability 结构评分（~5ms） |
| 视频处理 | 下载/ffmpeg/Whisper | 读 meta 标签（~1ms） |
| 格式转换 | 多步管道 | Turndown 单次遍历（~3ms） |
| 保存 | API 写入远程 | 本地 Obsidian URI 直写（~10ms） |

**整个流水线耗时通常在 20-50ms 内。**

---

## 四、关键设计原则（可复用到 B站流水线）

### 原则 1：渐进式降级（Fallback Chain）

Web Clipper 不是"要么全有要么全无"：

```
DOM 直接读取 → Readability 提取 → 原始 HTML 兜底
    (快)             (中)              (慢)
```

每一级都比上一级慢但更鲁棒，只在必要时降级。

### 原则 2：已知平台走专用路径

对已知平台跳过通用算法，直接硬编码 DOM 路径。**模板匹配 ≈ 10μs，通用提取 ≈ 5ms，差了 500 倍。**

### 原则 3：只读不变的数据

视频场景下：**元数据 ≈ 永久不变**（标题、描述、封面 URL），**媒体数据 ≈ 临时下载**（视频流）。

Web Clipper 只读元数据 — 这决定了它的速度。你的流水线在"已看"场景下也可以只读元数据 + 缓存字幕，不重复下载音频。

### 原则 4：不做不必要的媒体处理

视频信息提取的"快慢鸿沟"：

| 操作 | 耗时 |
|------|------|
| 读 B站 API 获取元数据 | ~200ms |
| 读 API 字幕 | ~300ms |
| 下载音频（10min 视频） | ~30s |
| ffmpeg 转码 | ~10s |
| faster-whisper 转写 | ~180s |

**尽早短路**：能用 API 拿到的，绝不下载处理。
