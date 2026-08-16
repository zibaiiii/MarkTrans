<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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

// PPT 分页辅助线开关（仅模式一预览区，开启时显示红色断层线）
const showPptGuides = ref(false)

// 模式一的灰色示例占位符（支持多行排版与示例）
const mdPlaceholder = `在此输入或粘贴 Markdown 源码...

【语法示例】
# 一级标题
## 二级标题

支持 **加粗**、*斜体* 以及插入数学公式：
$$
x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}
$$

💡 【一键生成 PPT 提示】
# 这是一张标题幻灯片
## 这是一张内容幻灯片
* 汇报要点 1
* 汇报要点 2
`

// 模式一：Markdown 源码内容（textarea 双向绑定）
// 初始化时优先尝试从 localStorage 读取历史数据，若无则使用默认占位文本
const markdownContent = ref(localStorage.getItem('marktrans_md_cache') || mdPlaceholder)

// 实时计算预览 HTML（仅模式一使用）
const previewHtml = computed(() => md.render(markdownContent.value))

// ===== 模式三：Markdown 转 Excel =====
// 模式三的灰色示例占位符（提示 + 表格示例）
const excelPlaceholder = `在此输入或粘贴带有表格的 Markdown 文本...
（提示：普通说明文字会被自动忽略，纯净剥离表格导出）

【表格示例】
| 模块名称 | 负责人 | 进度状态 |
| --- | --- | --- |
| Markdown 重构 | 子白 | 已完成 |
| Pandas 接入 | zibai | 进行中 |
`
// 初始化时优先尝试从 localStorage 读取历史数据，若无则使用默认占位文本
const excelContent = ref(localStorage.getItem('marktrans_excel_cache') || excelPlaceholder)
const excelPreviewHtml = computed(() => md.render(excelContent.value))

// ===== 防丢失：本地自动实时保存 (Auto Save) =====
// 当用户在代码模式输入时，实时静默保存
watch(markdownContent, (newVal) => {
  localStorage.setItem('marktrans_md_cache', newVal)
})
// 当用户在 Excel 模式输入时，实时静默保存
watch(excelContent, (newVal) => {
  localStorage.setItem('marktrans_excel_cache', newVal)
})

// ===== 暗黑模式 (Dark Mode) =====
// 初始化暗黑主题状态
const showTutorial = ref(false)
const isDarkMode = ref(localStorage.getItem('marktrans_theme') === 'dark')

// 监听主题切换，改变 HTML 属性并保持本地存储，同时联动 Vditor
watch(isDarkMode, (newVal) => {
  const themeName = newVal ? 'dark' : 'light'
  localStorage.setItem('marktrans_theme', themeName)
  document.documentElement.setAttribute('data-theme', themeName)

  // 联动富文本 Vditor 换肤
  if (vditor.value) {
    vditor.value.setTheme(themeName, themeName, newVal ? 'native' : 'github')
  }
}, { immediate: true })

// ================= AI 助手相关状态 =================
const isAiOpen = ref(false)
const showAiSettings = ref(false)
const aiConfig = ref({
  apiKey: localStorage.getItem('marktrans_ai_key') || '',
  baseUrl: localStorage.getItem('marktrans_ai_url') || 'https://api.openai.com/v1',
  model: localStorage.getItem('marktrans_ai_model') || 'gpt-3.5-turbo'
})
const aiMessages = ref(JSON.parse(localStorage.getItem('marktrans_ai_msgs') || '[]'))
const aiInput = ref('')
const isAiLoading = ref(false)

watch(aiConfig, (newVal) => {
  localStorage.setItem('marktrans_ai_key', newVal.apiKey)
  localStorage.setItem('marktrans_ai_url', newVal.baseUrl)
  localStorage.setItem('marktrans_ai_model', newVal.model)
}, { deep: true })
watch(aiMessages, (newVal) => {
  localStorage.setItem('marktrans_ai_msgs', JSON.stringify(newVal))
}, { deep: true })

const sendAiMessage = async () => {
  if (!aiInput.value.trim() || isAiLoading.value) return
  if (!aiConfig.value.apiKey) {
    alert("请先点击 AI 面板右上角的⚙️设置 API Key")
    showAiSettings.value = true
    return
  }
  const userText = aiInput.value.trim()
  aiMessages.value.push({ role: 'user', content: userText })
  aiInput.value = ''
  isAiLoading.value = true

  try {
    if (window.pywebview && window.pywebview.api) {
      // 交给不具备跨域限制的 Python 后端去发请求
      const res = await window.pywebview.api.chat_with_ai(
        aiConfig.value.baseUrl,
        aiConfig.value.apiKey,
        aiConfig.value.model,
        aiMessages.value
      )

      if (res.success) {
        aiMessages.value.push({ role: 'assistant', content: res.reply })
      } else {
        throw new Error(res.error)
      }
    } else {
      throw new Error("请在桌面客户端环境运行该功能！")
    }
  } catch (error) {
    aiMessages.value.push({ role: 'assistant', content: `[接口返回错误] \n${error.message}` })
  } finally {
    isAiLoading.value = false
  }
}
const clearAiMessages = () => { aiMessages.value = [] }

// ================= AI 面板拖拽与样式状态 =================
const aiPanelStyle = ref({
  width: '320px',
  height: '480px',
  top: 'auto',
  left: '30px',
  bottom: '80px'
})

let isDragging = false
let startX = 0, startY = 0, initialLeft = 0, initialTop = 0

const startDrag = (e) => {
  // 如果是点击了按钮等元素，不触发拖拽
  if (e.target.tagName.toLowerCase() === 'button') return

  isDragging = true
  startX = e.clientX
  startY = e.clientY

  const panel = document.querySelector('.ai-panel')
  const rect = panel.getBoundingClientRect()
  initialLeft = rect.left
  initialTop = rect.top

  // 转换为绝对定位以便平滑拖拽
  aiPanelStyle.value.top = `${initialTop}px`
  aiPanelStyle.value.left = `${initialLeft}px`
  aiPanelStyle.value.bottom = 'auto'

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
}

const onDrag = (e) => {
  if (!isDragging) return
  const dx = e.clientX - startX
  const dy = e.clientY - startY
  aiPanelStyle.value.left = `${initialLeft + dx}px`
  aiPanelStyle.value.top = `${initialTop + dy}px`
}

const stopDrag = () => {
  isDragging = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
}

// 显式保存配置方法
const saveAiConfig = () => {
  localStorage.setItem('marktrans_ai_key', aiConfig.value.apiKey)
  localStorage.setItem('marktrans_ai_url', aiConfig.value.baseUrl)
  localStorage.setItem('marktrans_ai_model', aiConfig.value.model)
  alert('配置已持久化保存！')
  showAiSettings.value = false
}

const copyAiMessage = async (text) => {
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text)
      alert('已复制到剪贴板！')
    } else {
      // 兼容古老环境的备用复制方案
      const textArea = document.createElement("textarea")
      textArea.value = text
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand("copy")
      document.body.removeChild(textArea)
      alert('已复制到剪贴板！')
    }
  } catch (err) {
    alert('复制失败，请手动选中复制')
  }
}

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
    theme: isDarkMode.value ? 'dark' : 'classic',
    cache: {
      enable: true,
      id: 'marktrans_vditor_cache'
    },
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
        <span class="logo-text" @click="showTutorial = true" title="点击查看使用教程">MarkTrans</span>
        <button class="theme-toggle-btn" @click="isDarkMode = !isDarkMode" :title="isDarkMode ? '切换至亮色模式' : '切换至夜间模式'">
          {{ isDarkMode ? '☀️' : '🌙' }}
        </button>
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

      <!-- 按 Tab 模式动态切换导出按钮（仅 rtf2md 模式保留在顶部栏） -->
      <div class="header-actions" v-if="activeTab === 'rtf2md'">
        <button class="btn-export web-btn" @click="copyMarkdown">
          复制源码(Copy)
        </button>
        <button class="btn-export word-btn" @click="exportFile('md')">
          导出 MD
        </button>
      </div>
    </header>

    <!-- ================= 工作区 ================= -->
    <main class="main-workspace">
      <!-- 模式一：Markdown 编辑与导出（SaaS 卡片布局） -->
      <div class="mode-panel md-mode" v-show="activeTab === 'md2doc'">
        <div class="editor-section card-style">
          <div class="card-header">
            <span class="card-title">📄 编辑 Markdown 内容</span>
            <label class="ppt-toggle" title="开启后可清晰查看 PPT 将在哪里分页">
              <input type="checkbox" v-model="showPptGuides" /> PPT 辅助线
            </label>
          </div>
          <!-- 仿在线工具的虚线文件区 -->
          <div class="dashed-upload-area" @click="openLocalFile">
            <div class="upload-icon">📤</div>
            <div class="upload-text">点击选择本地 Markdown / TXT 文件</div>
            <div class="upload-subtext">也支持直接在此处下方粘贴内容（本地处理，绝对隐私）</div>
          </div>
          <textarea v-model="markdownContent" class="md-textarea" :placeholder="mdPlaceholder" spellcheck="false"></textarea>
        </div>

        <div class="preview-section card-style">
          <div class="card-header">
            <span class="card-title">👁️ 实时预览</span>
            <div class="card-actions">
              <button class="btn-export html" @click="exportFile('html')">导出 HTML</button>
              <button class="btn-export docx" @click="exportFile('docx')">导出 Docx</button>
              <button class="btn-export pdf" @click="exportFile('pdf')">导出 PDF</button>
              <button class="btn-export pptx" @click="exportFile('pptx')">导出 PPT</button>
            </div>
          </div>
          <div class="preview p-content pro-typography" :class="{ 'ppt-guides-active': showPptGuides }" v-html="previewHtml"></div>
        </div>
      </div>

      <!-- 模式二：Vditor 富文本编辑（所见即所得，自动转为 Markdown 后可导出） -->
      <div class="mode-panel rtf-mode" v-show="activeTab === 'rtf2md'">
        <div id="vditor" style="height: 100%; width: 100%;"></div>
      </div>

      <!-- === 模式 3：Markdown 转 Excel (SaaS 卡片布局) === -->
      <div v-show="activeTab === 'md2excel'" class="mode-panel md-mode">
        <div class="editor-section card-style">
          <div class="card-header">
            <span class="card-title">📊 输入 Markdown 表格</span>
          </div>
          <div class="dashed-upload-area" @click="openLocalFile">
            <div class="upload-icon">📤</div>
            <div class="upload-text">点击选择本地 Markdown / TXT 文件</div>
            <div class="upload-subtext">普通文字会被自动忽略，仅提取表格导出</div>
          </div>
          <textarea v-model="excelContent" class="md-textarea" :placeholder="excelPlaceholder" spellcheck="false"></textarea>
        </div>
        <div class="preview-section card-style">
          <div class="card-header">
            <span class="card-title">👁️ 表格预览</span>
            <div class="card-actions">
              <button class="btn-export" style="background-color: #f39c12;" @click="exportFile('csv')">导出 CSV</button>
              <button class="btn-export" style="background-color: #217346;" @click="exportFile('xlsx')">导出 Excel</button>
            </div>
          </div>
          <div class="preview p-content pro-typography excel-preview-only" v-html="excelPreviewHtml"></div>
        </div>
      </div>
    </main>

    <!-- 左下角触发按钮 -->
    <div class="ai-trigger-btn" @click="isAiOpen = !isAiOpen" :title="isAiOpen ? '收起 AI' : '唤醒 AI'">✨</div>
    <!-- 聊天面板 -->
    <div v-show="isAiOpen" class="ai-panel" :style="aiPanelStyle">
      <!-- 头部 -->
      <div class="ai-header" @mousedown="startDrag">
        <div class="header-title">🤖 AI 助手</div>
        <div class="ai-header-actions">
          <button @click="clearAiMessages" title="清空对话">🗑️</button>
          <button @click="showAiSettings = !showAiSettings" title="设置 API">⚙️</button>
          <button @click="isAiOpen = false">✖</button>
        </div>
      </div>

      <!-- 设置浮层 -->
      <div v-show="showAiSettings" class="ai-settings">
        <div class="setting-item"><label>Base URL:</label><input v-model="aiConfig.baseUrl" placeholder="https://api.openai.com/v1" /></div>
        <div class="setting-item"><label>API Key:</label><input v-model="aiConfig.apiKey" type="password" placeholder="sk-..." /></div>
        <div class="setting-item"><label>Model:</label><input v-model="aiConfig.model" placeholder="gpt-4o / deepseek-chat" /></div>
        <button @click="saveAiConfig" class="save-config-btn">✅ 确认并保存配置</button>
      </div>

      <!-- 消息列表 (增加头像展示) -->
      <div class="ai-messages">
        <div v-if="aiMessages.length === 0" class="ai-empty">
          <div class="empty-icon">✨</div>
          你好！我是你的文档助手。你可以在⚙️中配置接口，然后向我提问。
        </div>
        <div v-for="(msg, index) in aiMessages" :key="index" :class="['ai-msg', msg.role === 'user' ? 'ai-user' : 'ai-bot']">
          <div v-if="msg.role === 'assistant'" class="ai-avatar">🤖</div>
          <div class="msg-bubble">
            <div class="msg-content">{{ msg.content }}</div>
            <button v-if="msg.role === 'assistant'" class="ai-copy-btn" @click="copyAiMessage(msg.content)" title="复制回复">📋</button>
          </div>
          <div v-if="msg.role === 'user'" class="ai-avatar">🧑‍💻</div>
        </div>
        <div v-if="isAiLoading" class="ai-msg ai-bot">
          <div class="ai-avatar">🤖</div>
          <div class="msg-bubble"><div class="msg-content loading-dots">正在思考，请稍候...</div></div>
        </div>
      </div>

      <!-- 现代风格药丸形输入区 -->
      <div class="ai-input-area">
        <div class="input-wrapper">
          <textarea v-model="aiInput" @keydown.enter.prevent="sendAiMessage" placeholder="输入问题，Enter 发送..." rows="1"></textarea>
          <button class="send-btn" :disabled="isAiLoading || !aiInput.trim()" @click="sendAiMessage">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ================= 使用教程弹窗 ================= -->
    <div v-show="showTutorial" class="tutorial-overlay" @click.self="showTutorial = false">
      <div class="tutorial-modal">
        <div class="tutorial-header">
          <h2>🚀 MarkTrans 核心使用指南</h2>
          <button class="close-btn" @click="showTutorial = false">✖</button>
        </div>
        <div class="tutorial-content">
          <h3>1. 👨‍💻 模式一：Markdown 编辑与终态导出（代码流）</h3>
          <ul>
            <li><strong>一键多格式导出：</strong> 在右侧预览区右上角，可由源码一键提取为 <strong>PDF、Word、HTML 以及 PPT</strong>。</li>
            <li><strong>PPT 分页技巧：</strong> 导出 PPT 时，系统按一级标题(<code>#</code>)或二级标题(<code>##</code>)自动切页，你也可使用分割线(<code>---</code>)强行分页。勾选右上方【PPT 辅助线】可实时查看分页断层。</li>
          </ul>

          <h3>2. 🎨 模式二：文字转 Markdown（富文本流）</h3>
          <ul>
            <li><strong>逆向剥离：</strong> 点击左上的【导入文件】，上传别人的 `.docx` Word 文档，它会在底层被瞬间洗成极其极其纯净的 Markdown 源码！</li>
            <li><strong>纯离线防丢图：</strong> 直接 Ctrl+V 粘贴电脑截图，图片会被瞬间提取为 <strong>Base64 编码文本</strong>写进底层。告别图床，完全离线化阅读。</li>
          </ul>

          <h3>3. 📊 模式三：Markdown 转 Excel（数据流）</h3>
          <ul>
            <li>将混杂在文字中的 Markdown 表格粘贴进来，系统会自动屏蔽多余废话，一键精准剥离成 <code>.xlsx</code> 或 <code>.csv</code> 文件。</li>
          </ul>

          <h3>4. ✨ AI Co-pilot 与暗黑模式</h3>
          <ul>
            <li>点击最左下角的魔法棒唤出面板，在 ⚙️ 设置中输入提供商的 API 即可使用沉浸式 AI 问答，支持文本代码一键复制。</li>
            <li>点击顶部 🌙 图标，即可开启全局联动的极客护眼模式。</li>
          </ul>
        </div>
      </div>
    </div>
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
  height: 70px;
  background-color: #fff;
  border-bottom: 1px solid #eaeaea;
  padding: 0 40px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
  flex-shrink: 0;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #0366d6;
}

.nav-tabs {
  display: flex;
  gap: 30px;
}

.tab-item {
  cursor: pointer;
  padding: 8px 10px;
  color: #666;
  font-weight: 500;
  font-size: 16px;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
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
  align-items: center;
  gap: 12px;
}

.btn-export {
  padding: 8px 18px;
  color: white;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  transition: opacity 0.2s, transform 0.1s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-left: 0;
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
  transform: translateY(-1px);
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
  border-right: 1px solid #eaeaea;
  background-color: #fff;
  min-width: 0;
  min-height: 0;
}

.md-mode .preview-section {
  flex: 1;
  padding: 40px 50px;
  overflow-y: auto;
  background-color: #fafbfc;
  min-width: 0;
  min-height: 0;
}

.md-textarea {
  flex: 1;
  width: 100%;
  height: 100%;
  padding: 30px 40px;
  border: none;
  outline: none;
  resize: none;
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 16px;
  line-height: 1.8;
  color: #24292e;
  background-color: #fff;
  box-sizing: border-box;
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

/* PPT 辅助线开关样式 */
.ppt-toggle {
  font-size: 13px;
  color: #555;
  display: flex;
  align-items: center;
  gap: 5px;
  margin-right: 15px;
  cursor: pointer;
  user-select: none;
}
.ppt-toggle input {
  cursor: pointer;
}

/* =========================================
   PPT 幻灯片分割线视觉模拟 (仅开启辅助线时生效)
   ========================================= */
/* 让分割线变成一条带有"新幻灯片"提示的华丽界线 */
.pro-typography.ppt-guides-active hr {
  height: 4px;
  background-color: #d24726;
  border: none;
  margin: 40px 0;
  position: relative;
  overflow: visible;
}
.pro-typography.ppt-guides-active hr::after {
  content: "✂️ 新一页幻灯片 (分割线切页)";
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: white;
  padding: 0 10px;
  color: #d24726;
  font-size: 12px;
  font-weight: bold;
}

/* 让二级标题自带顶级间距和边界，暗示由于 --slide-level=2，这里会自动切页 */
.pro-typography.ppt-guides-active h2 {
  margin-top: 50px;
  padding-top: 20px;
  border-top: 2px dashed #999;
  position: relative;
}
.pro-typography.ppt-guides-active h2::before {
  content: "📄 新一页幻灯片 (由标题切页)";
  position: absolute;
  top: -12px;
  right: 0;
  background: white;
  padding: 0 5px;
  color: #888;
  font-size: 11px;
}

/* =========================================
   🌙 全局暗黑模式 (Dark Mode)
   ========================================= */
/* 去除暗黑按钮的默认边框和背景 */
.theme-toggle-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  margin-left: 15px;
  transition: transform 0.2s;
}
.theme-toggle-btn:hover {
  transform: scale(1.1);
}

/* 当 HTML 带有 data-theme="dark" 时，强制覆盖颜色 */
html[data-theme="dark"] body {
  background-color: #1a1a1a !important;
  color: #d4d4d4 !important;
}

html[data-theme="dark"] header {
  background-color: #252526 !important;
  border-bottom: 1px solid #333 !important;
}

html[data-theme="dark"] .logo {
  color: #e0e0e0 !important;
}

html[data-theme="dark"] .tab-item {
  color: #a0a0a0;
}
html[data-theme="dark"] .tab-item.active {
  color: #61dafb;
  border-bottom-color: #61dafb;
}

html[data-theme="dark"] .editor-section {
  border-right: 1px solid #333 !important;
}

html[data-theme="dark"] .md-textarea {
  background-color: #1e1e1e !important;
  color: #eeeeee !important;
}

html[data-theme="dark"] .preview-section {
  background-color: transparent !important;
}

/* 覆盖 pro-typography Markdown 渲染区的普通颜色 */
html[data-theme="dark"] .pro-typography {
  color: #c9d1d9 !important;
}
html[data-theme="dark"] .pro-typography h1,
html[data-theme="dark"] .pro-typography h2,
html[data-theme="dark"] .pro-typography h3 {
  color: #f0f6fc !important;
}
html[data-theme="dark"] .pro-typography pre,
html[data-theme="dark"] .pro-typography code {
  background-color: #2d333b !important;
  color: #e8eaf1 !important;
}
html[data-theme="dark"] .pro-typography table th {
  background-color: #21262d !important;
  border-color: #30363d !important;
}
html[data-theme="dark"] .pro-typography table td,
html[data-theme="dark"] .pro-typography table tr {
  border-color: #30363d !important;
  background-color: #0d1117 !important;
}

/* ================= 仪表盘卡片流布局 (SaaS Card Layout) ================= */
/* 给页面底层铺上浅灰蓝底色 */
main {
  background-color: #f4f6f8;
  padding: 30px;
}
.mode-panel {
  gap: 30px;
  background: transparent !important;
}

/* 独立悬浮卡片通用样式 */
.card-style {
  background-color: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  border: 1px solid #eef1f5;
  display: flex !important;
  flex-direction: column;
  overflow: hidden;
  border-right: none !important;
}
.card-style:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.3s ease;
}

/* 卡片头部小横条 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 25px;
  background-color: #fdfdfd;
  border-bottom: 1px solid #f0f0f0;
}
.card-title {
  font-size: 16px;
  font-weight: 700;
  color: #333;
}
.card-actions {
  display: flex;
  gap: 10px;
}

/* 虚线本地提取框 (仿截图样式) */
.dashed-upload-area {
  margin: 20px 25px 0 25px;
  border: 2px dashed #d9e2ec;
  border-radius: 8px;
  padding: 25px 15px;
  text-align: center;
  cursor: pointer;
  background-color: #fafbfc;
  transition: all 0.2s;
}
.dashed-upload-area:hover {
  border-color: #0072ff;
  background-color: #f0f7ff;
}
.upload-icon { font-size: 28px; margin-bottom: 8px; }
.upload-text { font-size: 15px; font-weight: bold; color: #444; }
.upload-subtext { font-size: 12px; color: #888; margin-top: 5px; }

/* 调整之前文本区和预览区的内边距，适应新卡片 */
.card-style .md-textarea {
  padding: 25px;
  background: #ffffff;
}
.card-style .preview {
  padding: 25px 40px;
  height: 100%;
  overflow-y: auto;
}

/* 根据截图美化那些不同颜色的极客导出按钮 */
.btn-export.html { background-color: #10a37f; }
.btn-export.docx { background-color: #556ee6; }
.btn-export.pdf { background-color: #d13030; }
.btn-export.pptx { background-color: #e76f51; }
.btn-export { padding: 6px 14px; font-size: 13px; border-radius: 6px; }

/* 适配暗黑模式 */
html[data-theme="dark"] main { background-color: #121212; }
html[data-theme="dark"] .card-style { background-color: #1e1e1e; border-color: #2b2b2b; }
html[data-theme="dark"] .card-header { background-color: #252526; border-color: #333; }
html[data-theme="dark"] .card-title { color: #d4d4d4; }
html[data-theme="dark"] .dashed-upload-area { border-color: #444; background-color: #252526; }
html[data-theme="dark"] .upload-text { color: #ccc; }
html[data-theme="dark"] .card-style .md-textarea { background: #1e1e1e; }

/* ================= AI 面板现代化美化 ================= */
.ai-trigger-btn {
  position: fixed; left: 20px; bottom: 20px; width: 50px; height: 50px;
  background: linear-gradient(135deg, #00c6ff, #0072ff);
  color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 24px; box-shadow: 0 4px 15px rgba(0, 198, 255, 0.4); cursor: pointer; z-index: 1000; transition: all 0.3s;
}
.ai-trigger-btn:hover { transform: scale(1.1) translateY(-3px); box-shadow: 0 8px 25px rgba(0, 198, 255, 0.5); }

.ai-panel {
  position: fixed; background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px); border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.1); border: 1px solid rgba(0,0,0,0.08);
  display: flex; flex-direction: column; z-index: 999;
  resize: both; overflow: hidden; min-width: 300px; min-height: 400px; max-width: 80vw; max-height: 90vh;
}

/* 巨无霸防滑缩放拉杆 */
.ai-panel::-webkit-resizer {
  background-color: transparent;
  background-image: repeating-linear-gradient(135deg, transparent, transparent 3px, #aaa 3px, #aaa 5px);
  background-size: 16px 16px; background-position: bottom right; background-repeat: no-repeat;
}

.ai-header {
  height: 48px; background: rgba(245,247,250,0.8);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; font-weight: bold; border-bottom: 1px solid rgba(0,0,0,0.05);
  cursor: grab; user-select: none; color: #333;
}
.ai-header:active { cursor: grabbing; }
.header-title { display: flex; align-items: center; gap: 6px; }
.ai-header-actions button { background: none; border: none; cursor: pointer; margin-left: 10px; font-size: 15px; opacity: 0.6; }
.ai-header-actions button:hover { opacity: 1; }

.ai-settings { padding: 15px; background: #fff; border-bottom: 1px solid #eaeaea; font-size: 12px; }
.setting-item input { border: 1px solid #d9d9d9; padding: 8px; border-radius: 6px; outline: none; margin-top: 5px; width: 100%; box-sizing: border-box; }
.save-config-btn { width: 100%; padding: 10px; background: #10a37f; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; margin-top: 10px; }

.ai-messages { flex: 1; padding: 20px 15px; overflow-y: auto; background: transparent; display: flex; flex-direction: column; gap: 20px; }
.ai-empty { text-align: center; color: #888; margin-top: 40px; }
.empty-icon { font-size: 32px; margin-bottom: 10px; }
.ai-msg { display: flex; align-items: flex-start; gap: 10px; width: 100%; }
.ai-user { flex-direction: row-reverse; }
.ai-avatar { font-size: 24px; line-height: 1; }
.msg-bubble { max-width: 75%; display: flex; flex-direction: column; }
.ai-msg .msg-content { padding: 10px 14px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; user-select: text !important; }
.ai-user .msg-content { background: #0072ff; color: #fff; border-radius: 16px 4px 16px 16px; box-shadow: 0 4px 10px rgba(0,114,255,0.15); }
.ai-bot .msg-content { background: #fff; color: #333; border: 1px solid #e5e5e5; border-radius: 4px 16px 16px 16px; }
.ai-copy-btn { margin-top: 4px; background: #fff; border: 1px solid #eee; border-radius: 4px; padding: 4px 8px; cursor: pointer; align-self: flex-start; font-size: 12px; }

.ai-input-area { padding: 15px; background: rgba(255,255,255,0.8); border-top: 1px solid rgba(0,0,0,0.05); }
.input-wrapper { display: flex; align-items: center; background: #f4f5f7; border-radius: 20px; padding: 5px 15px; }
.input-wrapper textarea { flex: 1; border: none; background: transparent; padding: 10px 0; resize: none; outline: none; font-size: 14px; }
.send-btn { width: 32px; height: 32px; border-radius: 50%; border: none; background: #0072ff; color: #fff; display: flex; align-items: center; justify-content: center; cursor: pointer; margin-left: 8px; flex-shrink: 0; }
.send-btn:disabled { background: #ccc; cursor: not-allowed; }

/* 暗黑模式适配 */
html[data-theme="dark"] .ai-panel { background: rgba(30,30,30,0.95); border-color: #444; }
html[data-theme="dark"] .ai-header { background: rgba(40,40,40,0.9); border-color: #333; color: #eee; }
html[data-theme="dark"] .ai-settings { background: #252526; border-color: #333; }
html[data-theme="dark"] .setting-item input { background: #1e1e1e; color: #eee; border-color: #444; }
html[data-theme="dark"] .ai-bot .msg-content { background: #2d2d30; color: #eee; border-color: #444; }
html[data-theme="dark"] .ai-input-area { background: transparent; border-color: #333; }
html[data-theme="dark"] .input-wrapper { background: #2d2d30; }
html[data-theme="dark"] .input-wrapper textarea { color: #fff; }
html[data-theme="dark"] .ai-copy-btn { background: #333; border-color: #444; color: #ccc; }

/* ================= Logo 交互与教程弹窗 ================= */
.logo-text {
  cursor: pointer;
  transition: transform 0.2s, color 0.2s;
  user-select: none;
}
.logo-text:hover {
  transform: scale(1.05);
  color: #0072ff;
}

.tutorial-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(6px);
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s ease-out;
}

.tutorial-modal {
  background: #fff;
  width: 650px;
  max-width: 90vw;
  max-height: 85vh;
  border-radius: 16px;
  box-shadow: 0 15px 50px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease-out;
}

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

.tutorial-header {
  padding: 16px 24px;
  background: #f8f9fa;
  border-bottom: 1px solid #eaeaea;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tutorial-header h2 { margin: 0; font-size: 18px; color: #333; }
.tutorial-header .close-btn { background: none; border: none; font-size: 20px; cursor: pointer; color: #888; transition: color 0.2s; }
.tutorial-header .close-btn:hover { color: #ff4757; }

.tutorial-content {
  padding: 24px 30px;
  overflow-y: auto;
  line-height: 1.7;
  color: #444;
  font-size: 14px;
}
.tutorial-content h3 { color: #0072ff; margin-top: 25px; margin-bottom: 12px; font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
.tutorial-content h3:first-child { margin-top: 0; }
.tutorial-content ul { padding-left: 20px; margin: 0; }
.tutorial-content li { margin-bottom: 8px; }
.tutorial-content strong { color: #222; }

/* 教程暗黑模式适配 */
html[data-theme="dark"] .tutorial-modal { background: #1e1e1e; border: 1px solid #333; }
html[data-theme="dark"] .tutorial-header { background: #252526; border-color: #333; }
html[data-theme="dark"] .tutorial-header h2 { color: #eee; }
html[data-theme="dark"] .tutorial-content { color: #ccc; }
html[data-theme="dark"] .tutorial-content h3 { color: #61dafb; border-color: #333; }
html[data-theme="dark"] .tutorial-content strong { color: #eee; }
</style>
