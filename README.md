# MarkTrans — LaTeX Markdown 桌面工作台

基于 **Vue 3 + Python (pywebview)** 构建的离线优先 Markdown 桌面应用。集编辑、预览、多格式导出、AI 助手于一体，支持 LaTeX 公式、暗黑模式、自动保存（Python 侧文件持久化，关闭程序数据不丢失），可一键打包为独立 `.exe`。

![Vue3](https://img.shields.io/badge/Frontend-Vue3-42b883?style=flat-square&logo=vuedotjs)
![Python](https://img.shields.io/badge/Backend-Python3-3776ab?style=flat-square&logo=python)
![Pywebview](https://img.shields.io/badge/Desktop-Pywebview-ffc107?style=flat-square)
![Vditor](https://img.shields.io/badge/Editor-Vditor-blue?style=flat-square)

---

## 三大工作模式

### 模式一：Markdown 编辑与导出

左右双卡片布局，左侧书写源码，右侧实时预览（Typora 风格排版 + KaTeX 公式渲染）。

- **四格式导出**：HTML / Word (.docx) / PDF / PowerPoint (.pptx)
- **PPT 分页辅助线**：开关开启后，预览区以红色断层线标示 `##` 标题和 `---` 分割线对应的幻灯片分页位置
- **PDF 中文排版**：XeLaTeX 引擎 + `CJKmainfont=Microsoft YaHei` + `geometry:margin=1in`，彻底解决中文冲出页面边界的 Bug
- **PPT 幻灯片切页**：`--slide-level=2` 强制按二级标题分页，避免内容粘连
- **虚线上传区**：点击导入本地 `.md` / `.txt` / `.docx` 文件（Word 自动转 Markdown）
- <img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/c29c9c0b-896a-4f42-827e-32c7fdff961d" />


### 模式二：Markdown 转 Excel

从 Markdown 文本中智能提取表格，导出为 Excel / CSV。

- **自动忽略非表格文字**：只提取 `| ... |` 格式的表格行
- **Pandas 引擎**：后端 pandas 处理，支持 .xlsx / .csv 双格式导出
- <img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/c29695b7-01cb-43ee-bded-a30f6ba93c7e" />


### 模式三：文字转 Markdown（Vditor 富文本）

所见即所得编辑器，像 Word 一样排版，底层自动生成标准 Markdown。

- **拖拽/粘贴图片**：自动转 Base64 嵌入文档，无需图床，永不离线失效
- **快捷公式**：输入 `$$` 唤出公式编辑器，`Ctrl+B` 加粗等原生快捷键
- **导出**：复制 Markdown 源码 / 导出 .md 文件
- <img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/c8f1258f-2270-4f03-8df3-3aa3e52632d1" />


---

## 全局功能

### 🔍 查找与替换（专业版悬浮窗）

顶部 🔍 按钮或 `Ctrl+F` / `Ctrl+H` 唤出专业查找替换面板，仿 WPS/Office 交互：
<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/1cb9f0ea-7796-4af5-a02f-7928ab4272ab" />
- **Tab 切换**：查找(D) / 替换(P) 两种模式
- **逐个定位**：上一处(B) / 下一处(F) 高亮选区，支持环绕查找
- **替换当前**：逐个替换选中的匹配项，替换后自动跳到下一处
- **全部替换**：一键批量替换，支持三个模式
- **可拖拽悬浮窗**：面板可自由移动到任意位置，`Esc` 快速关闭
- **模式隔离**：仅作用于当前激活的模式（Tab）

### 🌙 暗黑模式

顶部一键切换 🌙/☀️，全界面联动换肤：导航栏、编辑区、预览区、AI 面板、卡片全部适配。主题选择持久化到 `~/.marktrans_data/state.json`，重启自动恢复。

### 💾 自动保存（防丢失）

三个模式的内容均实时静默保存，采用 **Python 侧文件持久化** 作为真正存储后端（不依赖浏览器 localStorage）：

- **双写策略**：前端每次修改同时写入 localStorage（运行时镜像）和 Python 后端 `~/.marktrans_data/state.json`（持久真源）
- **防抖写入**：300ms 防抖避免逐字符写文件，输入停顿后自动落盘
- **原子写入**：先写 `.tmp` 临时文件再 `os.replace` 替换，杜绝写入中途崩溃导致文件损坏
- **启动恢复**：应用启动时监听 `pywebviewready` 事件，调用 `load_all_state()` 批量恢复全部状态
- 模式一 / 模式三：`watch` 监听输入 → `persistState()` 双写
- 模式二：Vditor `input` 回调 → `persistState()` 双写（已关闭 Vditor 自带 localStorage 缓存）
- 即便 localStorage 被系统清理，下次启动仍能从 `state.json` 完整恢复

### 🤖 AI 助手（侧边悬浮面板）

左下角 ✨ 按钮唤起，支持拖拽移动、右下角缩放。
<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/fc5028f1-7595-4460-8944-ac41dcad571b" />

- **上下文感知自动改写**：AI 自动读取当前正文，对翻译/重写/修改请求直接修改原文
- **一键撤销**：修改后 AI 面板头部出现 🔙 撤销按钮，点击即可恢复修改前的内容
- **OpenAI 兼容接口**：支持自定义 Base URL / API Key / Model（兼容 OpenAI、DeepSeek、Moonshot 等）
- **后端代理**：通过 Python `urllib` 转发请求，彻底规避浏览器 CORS 跨域限制
- **对话持久化**：聊天历史和 API 配置均存入 `state.json`（Python 侧持久化）
- **一键复制**：AI 回复气泡内嵌 📋 按钮，`navigator.clipboard` + `execCommand` 双路径兜底
- **现代化 UI**：毛玻璃面板、头像气泡、药丸形输入框、SVG 纸飞机发送按钮

### 🎨 SaaS 卡片布局

仿在线工具的悬浮卡片设计：
- 底层浅灰蓝 `#f4f6f8` 背景 + 30px 外留白
- 白色圆角卡片 + 轻阴影 + hover 加深
- 卡片头部承载标题和操作按钮，内容区与操作区分离
- 虚线上传区模仿现代 SaaS 工具的文件导入交互

---

## 技术栈

| 层 | 技术 |
|---|---|
| 前端框架 | Vue 3 + Vite |
| Markdown 渲染 | markdown-it + @mdit/plugin-katex |
| 富文本编辑 | Vditor（WYSIWYG 模式） |
| 桌面容器 | pywebview（Chromium 内核） |
| 文档转换 | pypandoc → Pandoc（HTML/DOCX/PDF/PPTX） |
| 表格处理 | pandas + openpyxl |
| AI 代理 | Python urllib（标准库，零额外依赖） |
| 状态持久化 | Python 侧 JSON 文件（`~/.marktrans_data/state.json`，原子写入） |
| 打包 | PyInstaller（单文件 .exe） |

---

## 本地开发

### 1. 环境准备

- Node.js 18+
- Python 3.8+
- [Pandoc](https://pandoc.org/installing.html)（PDF 导出需额外安装 [MiKTeX](https://miktex.org/) 提供 XeLaTeX 引擎）

### 2. 前端构建

```bash
cd frontend
npm install
npm run build
```

构建产物输出到 `backend/dist/`（vite.config.js 中配置 `outDir: '../backend/dist'`）。

### 3. 后端依赖

```bash
cd backend
pip install pywebview pandas openpyxl markdown lxml pypandoc
```

### 4. 启动应用

```bash
cd backend
python main.py
```

> 调试时可将 `main.py` 末尾的 `webview.start(debug=False)` 改为 `True` 以开启 DevTools。

---


## 项目结构

```
MarkTrans/
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   │   └── MT.png            # 软件品牌图标
│   │   ├── App.vue          # 主组件（三模式 + AI 助手 + 暗黑模式 + 查找替换 + 卡片布局）
│   │   ├── main.js          # Vue 入口
│   │   └── style.css        # 全局样式
│   ├── index.html
│   ├── vite.config.js       # outDir → ../backend/dist
│   └── package.json
├── backend/
│   ├── main.py              # pywebview 入口 + Api 类（导出/转换/AI 代理/状态持久化/WebView2 缓存清理）
│   ├── requirements.txt
│   └── dist/                # 前端构建产物（gitignore）
├── release/                 # PyInstaller 产物（gitignore）
├── .gitignore
└── README.md
```

---

## PDF 导出依赖说明

PDF 导出依赖 XeLaTeX 引擎渲染，以下参数已硬编码在 `backend/main.py` 中：

```python
pdf_args = [
    '--pdf-engine=xelatex',
    '-V', 'geometry:margin=1in',
    '-V', 'CJKmainfont=Microsoft YaHei',
    '--wrap=preserve'
]
```

- **开发环境**：需安装 MiKTeX 或 TeX Live 提供 `xelatex` 命令
- **打包 exe**：XeLaTeX 引擎体积过大（数 GB）无法打包进 exe，目标机器需自行安装

---

## License

MIT
