<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MarkdownIt from 'markdown-it'
import { katex } from '@mdit/plugin-katex'
// 模式二：Vditor 富文本编辑器（所见即所得）
import Vditor from 'vditor'
import 'vditor/dist/index.css'

// 引入本地样式，彻底解决桌面端因网络限制导致的断网/样式错乱问题
import 'katex/dist/katex.min.css'
import 'github-markdown-css/github-markdown.css'

// 初始化 markdown-it，并启用 KaTeX 公式插件
const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  breaks: true,
})
md.use(katex)

// ===== 全局状态 =====
// 当前激活的工作模式：'md2doc' = Markdown 编辑与导出；'rtf2md' = 文字转 Markdown（Vditor 富文本）
const activeTab = ref('md2doc')

// Vditor 富文本编辑器实例（模式二）
const vditor = ref(null)

// 模式一：Markdown 源码内容（textarea 双向绑定）
const markdownContent = ref('')

// 模式一的灰色示例占位符（支持多行排版与示例）
const mdPlaceholder = `在此输入或粘贴 Markdown 源码...

【语法示例】
# 一级标题
## 二级标题

支持 **加粗**、*斜体* 以及插入数学公式：
$$
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$
`

// 实时计算预览 HTML（仅模式一使用）
const previewHtml = computed(() => md.render(markdownContent.value))

// ===== 模式三：Markdown 转 Excel =====
const excelContent = ref('')

// 模式三的灰色示例占位符（提示 + 表格示例）
const excelPlaceholder = `在此输入或粘贴带有表格的 Markdown 文本...
（提示：普通说明文字会被自动忽略，纯净剥离表格导出）

【表格示例】
| 模块名称 | 负责人 | 进度状态 |
| --- | --- | --- |
| Markdown 重构 | 子白 | 已完成 |
| Pandas 接入 | zibai | 进行中 |
`
const excelPreviewHtml = computed(() => md.render(excelContent.value))

/**
 * 获取当前需要导出的 Markdown 内容：
 * - md2doc：直接用 textarea 中的 markdown 源码
 * - rtf2md：调用 Vditor.getValue()，Vditor 会把富文本内容自动转换为 Markdown
 */
function getExportContent() {
  if (activeTab.value === 'md2excel') {
    return excelContent.value || ''
  }
  if (activeTab.value === 'rtf2md' && vditor.value) {
    return vditor.value.getValue() || ''
  }
  return markdownContent.value || ''
}

// 调用 pywebview 暴露的后端 API 进行导出
// 注意：'md' 类型只在 rtf2md 模式下出现，getExportContent() 会自动调用
// vditor.getValue() 把富文本内容转换为 Markdown 源码后传给后端。
function exportFile(type) {
  const content = getExportContent()
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.export_file(type, content)
  } else {
    // 非 pywebview 环境（如纯浏览器调试）下的提示
    console.warn('pywebview API 不可用，请在桌面应用中运行。导出内容预览长度：', content.length)
    alert(`pywebview API 不可用，请在桌面应用中调用导出（类型：${type}）。`)
  }
}

/**
 * 复制 Vditor 当前内容的 Markdown 源码到剪贴板。
 * 优先使用现代 Clipboard API；在 pywebview 的 file:// 上下文下该 API
 * 可能因非安全上下文而失败，故降级到 execCommand('copy') 兜底。
 */
async function copyMarkdown() {
  if (!vditor.value) {
    console.warn('编辑器尚未初始化，无法复制。')
    return
  }
  const text = vditor.value.getValue() || ''

  // 优先：现代 Clipboard API（静默复制，不弹窗）
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return
    }
  } catch (e) {
    console.warn('Clipboard API 不可用，降级到 execCommand:', e)
  }

  // 降级：临时 textarea + execCommand('copy')
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.top = '0'
    ta.style.left = '0'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  } catch (e) {
    console.error('复制失败:', e)
  }
}

// 打开本地文件：通过 pywebview 后端调起系统文件选择对话框，
// 读取文本内容后根据当前 Tab 注入到对应的编辑器/textarea。
const openLocalFile = async () => {
  if (window.pywebview && window.pywebview.api) {
    const fileData = await window.pywebview.api.open_file()
    if (fileData) {
      // 根据当前所在的模式，将读取的文件内容放进去
      if (activeTab.value === 'md2doc') {
        markdownContent.value = fileData
      } else if (activeTab.value === 'rtf2md') {
        vditor.value.setValue(fileData)
      } else if (activeTab.value === 'md2excel') {
        excelContent.value = fileData
      }
    }
  } else {
    alert('请在桌面应用中运行！')
  }
}

// ===== Vditor 生命周期 =====
onMounted(() => {
  if (typeof document === 'undefined') return
  // 重新初始化 Vditor
  vditor.value = new Vditor('vditor', {
    mode: 'wysiwyg',
    height: '100%',
    lang: 'zh_CN',
    toolbarConfig: { pin: true },
    cache: { enable: false },
    placeholder: '在此像使用 Word 一样排版...\n\n💡 提示：支持直接拖拽 / 粘贴图片自动上屏，支持 Ctrl+B 加粗，输入 $$ 可快速插入公式。',
    // 去除 fullscreen 全屏按钮（使用桌面窗口的最大化即可），保持其它按钮精简
    toolbar: [
      'emoji', 'headings', 'bold', 'italic', 'strike', 'link', '|',
      'list', 'ordered-list', 'check', '|',
      'quote', 'line', 'code', 'inline-code', '|',
      'upload', 'table', '|',
      'undo', 'redo', '|',
      {
        name: 'more',
        toolbar: [ 'outline', 'code-theme', 'content-theme' ],
      },
    ],
    // 拦截 Vditor 默认上传逻辑：本地图片直接转 Base64 插入，不走网络
    upload: {
      accept: 'image/*, .jpg, .png, .gif, .svg, .jpeg',
      handler(files) {
        files.forEach(file => {
          const reader = new FileReader()
          reader.onload = (e) => {
            const base64Str = e.target.result
            // 直接将生成的 base64 文本以 markdown 图片语法插入编辑器
            vditor.value.insertValue(`\n![${file.name}](${base64Str})\n`)
          }
          reader.readAsDataURL(file)
        })
        return null // 告诉 Vditor 我们自己处理了，不要报错
      },
    },
    // 在编辑器挂载完成后，强行注入操作系统的原生 title 悬停提示
    after: () => {
      const zhTips = {
        'emoji': '插入表情',
        'headings': '标题格式',
        'bold': '加粗 (Ctrl+B)',
        'italic': '斜体 (Ctrl+I)',
        'strike': '删除线 (Ctrl+S)',
        'link': '插入链接 (Ctrl+K)',
        'list': '无序列表',
        'ordered-list': '有序列表',
        'check': '任务列表',
        'quote': '引用段落',
        'line': '插入分割线',
        'code': '代码块',
        'inline-code': '行内代码 (Ctrl+G)',
        'upload': '上传图片或文件',
        'table': '插入表格 (Ctrl+M)',
        'math': '插入数学公式',
        'undo': '撤销 (Ctrl+Z)',
        'redo': '重做 (Ctrl+Y)',
        'more': '更多选项',
      }

      // 遍历字典，精准给对应的 DOM 按钮添加系统原生 tooltip
      Object.keys(zhTips).forEach(key => {
        const btn = document.querySelector(`.vditor-toolbar__item [data-type="${key}"]`)
        if (btn) {
          btn.setAttribute('title', zhTips[key])
        }
      })
    },
  })
})

onUnmounted(() => {
  // 释放 Vditor 事件监听与 DOM 资源，避免切 Tab/关闭时内存泄漏
  if (vditor.value && typeof vditor.value.destroy === 'function') {
    try {
      vditor.value.destroy()
    } catch (_) {
      /* 忽略销毁过程中的异常 */
    }
  }
  vditor.value = null
})
</script>

<template>
  <div class="app-container">
    <!-- ================= 顶部全局导航栏 ================= -->
    <header class="global-navbar">
      <div class="logo-area">
        <span class="logo-text">MarkTrans</span>
        <button class="btn-export" style="background-color: #607d8b; margin-left: 15px;" @click="openLocalFile" title="支持读取 .md 和解析 .docx 文件">导入文件 (MD/Word)</button>
      </div>

      <nav class="nav-tabs">
        <div
          class="tab-item"
          :class="{ active: activeTab === 'md2doc' }"
          @click="activeTab = 'md2doc'"
        >
          Markdown 编辑与导出
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'md2excel' }"
          @click="activeTab = 'md2excel'"
        >
          Markdown 转 Excel
        </div>
        <div
          class="tab-item"
          :class="{ active: activeTab === 'rtf2md' }"
          @click="activeTab = 'rtf2md'"
        >
          文字转 Markdown
        </div>
      </nav>

      <!-- 按 Tab 模式动态切换导出按钮（居中对齐） -->
      <div class="header-actions">
        <template v-if="activeTab === 'md2doc'">
          <button class="btn-export web-btn" @click="exportFile('html')">
            导出 HTML
          </button>
          <button class="btn-export word-btn" @click="exportFile('docx')">
            导出 Docx
          </button>
          <button class="btn-export pdf-btn" @click="exportFile('pdf')">
            导出 PDF
          </button>
        </template>
        <template v-else-if="activeTab === 'md2excel'">
          <button class="btn-export" style="background-color: #f39c12;" @click="exportFile('csv')">
            导出 CSV
          </button>
          <button class="btn-export" style="background-color: #217346;" @click="exportFile('xlsx')">
            导出 Excel
          </button>
        </template>
        <template v-else>
          <button class="btn-export web-btn" @click="copyMarkdown">
            复制源码(Copy)
          </button>
          <button class="btn-export word-btn" @click="exportFile('md')">
            导出 MD
          </button>
        </template>
      </div>
    </header>

    <!-- ================= 工作区 ================= -->
    <main class="main-workspace">
      <!-- 模式一：Markdown 编辑与导出（纯粹的左右分栏，无工具栏） -->
      <div class="mode-panel md-mode" v-show="activeTab === 'md2doc'">
        <section class="editor-section">
          <textarea
            v-model="markdownContent"
            class="md-textarea"
            :placeholder="mdPlaceholder"
            spellcheck="false"
          ></textarea>
        </section>

        <section class="preview-section">
          <div class="preview pro-typography" v-html="previewHtml"></div>
        </section>
      </div>

      <!-- 模式二：Vditor 富文本编辑（所见即所得，自动转为 Markdown 后可导出） -->
      <div class="mode-panel rtf-mode" v-show="activeTab === 'rtf2md'">
        <div id="vditor" style="height: 100%; width: 100%;"></div>
      </div>

      <!-- === 模式 3：Markdown 转 Excel === -->
      <div v-show="activeTab === 'md2excel'" class="mode-panel md-mode">
        <div class="editor-section">
          <textarea
            v-model="excelContent"
            class="md-textarea"
            :placeholder="excelPlaceholder"
            spellcheck="false"
          ></textarea>
        </div>
        <div class="preview-section">
          <!-- 加上 excel-preview-only 特殊类用于隐藏其它文本 -->
          <div class="preview pro-typography excel-preview-only" v-html="excelPreviewHtml"></div>
        </div>
      </div>
    </main>
  </div>
</template>

<style>
/* ====================
   基础重置与全屏铺满修复
   ==================== */
* {
  box-sizing: border-box;
}

html, body {
  height: 100%;
  width: 100%;
  margin: 0;
  padding: 0;
  background-color: #f5f6f7;
  overflow: hidden; /* 防止出现外层滚动条 */
}

/* 核心杀手锏：彻底干掉 Vue 默认自带的 1280px 宽度限制和 Padding */
#app {
  height: 100%;
  width: 100% !important;
  max-width: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* ================= 顶部全局导航栏 ================= */
.global-navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  background-color: #ffffff;
  border-bottom: 1px solid #e1e4e8;
  padding: 0 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
  flex-shrink: 0;
}

.logo-area {
  width: 220px;
  display: flex;
  align-items: center;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #0366d6;
}

.nav-tabs {
  display: flex;
  height: 100%;
}

.tab-item {
  display: flex;
  align-items: center;
  padding: 0 24px;
  font-size: 15px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
  user-select: none;
}

.tab-item:hover {
  color: #333;
}

.tab-item.active {
  color: #0366d6;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 10%;
  width: 80%;
  height: 3px;
  background-color: #0366d6;
  border-radius: 3px 3px 0 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  width: 320px;
  justify-content: center; /* 三个导出按钮居中，避免拥挤/挤到顶部 */
  align-items: center;
}

.btn-export {
  padding: 6px 12px;
  font-size: 13px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 500;
  color: #fff;
  transition: opacity 0.2s, transform 0.1s;
  white-space: nowrap;
}

.btn-export:active {
  transform: translateY(1px);
}

.web-btn {
  background-color: #42b983;
}

.word-btn {
  background-color: #2b579a;
}

.pdf-btn {
  background-color: #d32f2f;
}

.btn-export:hover {
  opacity: 0.9;
}

/* ================= 工作区布局 ================= */
.main-workspace {
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.mode-panel {
  display: flex;
  height: 100%;
  width: 100%;
}

/* 模式一：左右分栏 */
.md-mode .editor-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e1e4e8;
  background-color: #fff;
  min-width: 0;
  min-height: 0;
}

.md-mode .preview-section {
  flex: 1;
  overflow-y: auto;
  background-color: #fafbfc;
  min-width: 0;
  min-height: 0;
}

.md-textarea {
  flex: 1;
  width: 100%;
  height: 100%;
  padding: 20px;
  border: none;
  outline: none;
  resize: none;
  font-family: 'SFMono-Regular', Consolas, Menlo, monospace;
  font-size: 14.5px;
  line-height: 1.7;
  color: #24292e;
  background-color: #fff;
}

/* ================= 高级排版皮肤 (Typora 风格) ================= */
.pro-typography {
  padding: 30px 50px;
  /* 采用适合中文和外文混排的无衬线字体 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
  font-size: 16px; /* 增加基础字号，阅读更舒服 */
  line-height: 1.8; /* 舒展的行距 */
  color: #333333; /* 柔和的深灰色，不刺眼 */
  text-align: left;
  letter-spacing: 0.3px; /* 微调字间距 */
}

/* 标题样式优化 */
.pro-typography h1,
.pro-typography h2,
.pro-typography h3,
.pro-typography h4 {
  color: #2c3e50;
  font-weight: 600;
  margin-top: 1.8em;
  margin-bottom: 0.8em;
  line-height: 1.4;
}

.pro-typography h2 {
  padding-bottom: 8px;
  border-bottom: 1px solid #eaecef; /* 二级标题加一条温柔的下划线 */
}

/* 段落与加粗 */
.pro-typography p {
  margin-top: 0;
  margin-bottom: 1.2em;
}

.pro-typography strong {
  font-weight: 600;
  color: #1a1a1a; /* 加粗字体颜色更深一点，抓人眼球 */
}

/* 列表缩进优化 */
.pro-typography ul,
.pro-typography ol {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 1.2em;
}

.pro-typography li {
  margin-bottom: 0.4em;
}

/* 代码和引用块优化 */
.pro-typography pre {
  background: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 14px;
}

.pro-typography code {
  background: rgba(27, 31, 35, 0.05);
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, monospace;
}

.pro-typography pre code {
  padding: 0;
  background: none;
}

/* 重点：公式区防错位优化 */
.katex-display {
  margin: 1.2em 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 10px 0;
}

/* Markdown 转 Excel 专属模式：隐藏除表格外的所有内容 */
.excel-preview-only > *:not(table) {
  display: none !important;
}
.excel-preview-only table {
  width: 100%;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  border-radius: 8px;
  overflow: hidden;
}

/* ================= 模式二：Vditor 富文本容器 ================= */
.rtf-mode {
  display: flex;
  flex: 1; /* 撑满剩余空间 */
  width: 100%;
  flex-direction: column;
  text-align: left; /* 恢复正常左对齐 */
}
/* ====================
   斜体修复：放弃系统字体斜体，改用 DOM 物理空间变换倾斜
   ==================== */
em, i,
.pro-typography em,
.pro-typography i,
.vditor-reset em,
.vditor-reset i,
.vditor-wysiwyg em,
.vditor-wysiwyg i,
.vditor-wysiwyg [data-node="em"],
.vditor-wysiwyg [data-marker="*"] {
  font-style: normal !important; /* 放弃对浏览器系统斜体的所有幻想 */
  transform: skewX(-14deg) !important; /* 物理手段：强行把 DOM 节点向右推弯 14 度 */
  display: inline-block !important; /* 必须变为 inline-block 倾斜才能生效 */
  color: #0366d6 !important; /* 加上深蓝色标识，一眼就能看出彻底生效了！ */
}

/* 顺手把粗体样式也打在最底层，确保双模式万无一失 */
strong, b,
.pro-typography strong,
.pro-typography b,
.vditor-reset strong,
.vditor-reset b,
.vditor-wysiwyg strong,
.vditor-wysiwyg b,
.vditor-wysiwyg [data-node="strong"],
.vditor-wysiwyg [data-marker="**"] {
  font-weight: 900 !important;
  color: #111111 !important;
}

/* ====================
   精准修复 KaTeX：仅重置盒子模型，决不干涉内部精密排版
   ==================== */
.katex,
.katex * {
  /* 仅抵消全局 border-box 带来的分式线条消失和盒子挤压问题 */
  box-sizing: content-box !important;
}

.pro-typography .katex {
  /* 防止外部 1.8 的大行距把行内公式拉拽变形，根元素重置即可 */
  line-height: 1.1 !important;
}

.pro-typography .katex-display {
  /* 保证块级公式不被外层行高影响，并保持居中或专属格式 */
  line-height: 1.2 !important;
}
</style>
