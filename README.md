# 🚀 MarkTrans - 桌面级多功能 Markdown 工作台

**MarkTrans** 是一款基于 Vue3 + Python (Pywebview) 构建的现代化双向 Markdown 桌面客户端。打破传统编辑器的单一形态，提供“代码流”、“富文本流”与“数据流”三大工作模式，致力于为开发者、科研人员和创作者提供极致的本地化文档处理体验。

![Vue3](https://img.shields.io/badge/Frontend-Vue3-42b883?style=flat-square&logo=vuedotjs)
![Python](https://img.shields.io/badge/Backend-Python3-3776ab?style=flat-square&logo=python)
![Pywebview](https://img.shields.io/badge/UI_Container-Pywebview-ffc107?style=flat-square)
![Vditor](https://img.shields.io/badge/Editor-Vditor-blue?style=flat-square)

---

## ✨ 核心功能与三大模式

### 👨‍💻 模式一：Markdown 编辑与导出（代码流）
纯净的极客输入环境，左侧书写 Markdown 源码，右侧实时 pro-typography 沉浸式绝美预览。
*   **全格式支持**：支持完整的 Markdown 语法及 KaTeX 复杂数学公式。
*   **一键终态导出**：内置 Pandoc 引擎，支持将 Markdown 无损导出为 **HTML、Word (.docx) 和 PDF** 文件。

### 🎨 模式二：富文本转 Markdown（提效流）
极其丝滑的所见即所得 (WYSIWYG) 富文本环境，像使用 Word 一样排版，但底层自动生成标准 Markdown 源码！
*   **逆向解析黑科技 (Word 转 MD)**：点击导入本地 `.docx` 文件，秒级剥离格式并在后台转化为干净的 Markdown 代码！
*   **免图床图片直出**：直接拖拽或 `Ctrl+V` 粘贴截图，图片瞬间转化为 **Base64 纯文本编码**嵌入文档。从此告别链接失效、图文分离，实现彻底的离线化！
*   **快捷排版**：输入 `$$` 唤出原生公式编辑器，悬停提示原生快捷键（Ctrl+B 加粗等）。

### 📊 模式三：Markdown 转 Excel（数据流）
数据处理专精模式。日常收集的 Markdown 表格，一键剥离！
*   **智能屏蔽**：自动忽略输入区的所有非表格文字。
*   **秒转表格**：借助后端的 Pandas 引擎，将 Markdown 表格一键提取并存为 **Excel (.xlsx) 或 CSV** 文件。

---

## 🛠️ 技术栈与特性修复

*   **前端**：Vite + Vue 3 + `@mdit/plugin-katex`（解决远古 KaTeX 上下标错位问题） + Vditor
*   **后端**：Python 3 + Pywebview + Pandas + Pypandoc (需系统预装 Pandoc 或在环境中集成)
*   **系统级排版修复**：通过定制化 CSS 空间物理扭曲 (`transform: skewX`) 及字体后备策略，完美解决了 Windows Chromium 内核锁定中文字体斜体渲染的骨灰级 Bug。

---

## 📦 本地开发与运行指南

### 1. 环境准备
确保你的电脑已安装 `Node.js` 和 `Python 3.8+`。

### 2. 前端构建
进入 frontend 目录，安装依赖并编译获取静态文件：
```bash
cd frontend
npm install
npm run build
```

### 3. 后端依赖安装
进入 backend 目录，安装所需的 Python 处理库：
```bash
cd backend
pip install pywebview pandas openpyxl markdown lxml pypandoc pyinstaller
```

### 4. 运行调试
在 backend 目录下，直接运行 Python 入口文件：
```bash
python main.py
```
*(注意：调试阶段可在 `main.py` 中将 `webview.start(debug=True)` 开启以调出浏览器开发者工具)*

---

## 🚀 一键打包发布 (Windows .exe)

使用 PyInstaller 将应用打包为无需依赖环境的单文件绿色版桌面软件。
在 `backend` 目录下执行以下命令：

```bash
pyinstaller --noconsole --onefile --name "MarkTrans" --add-data "../frontend/dist;dist" main.py
```
构建成功后，在 `backend/dist` 文件夹下即可找到 `MarkTrans.exe`。双击即可在任何 Windows 电脑上体验秒开的快乐！

