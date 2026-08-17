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
// 软件图标（来自 src/assets/MT.png）
import logoImg from './assets/MT.png'

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
// 注意：用 !== null 严格判断，避免用户主动清空内容（空字符串）后被示例覆写
const savedMd = localStorage.getItem('marktrans_md_cache')
const markdownContent = ref(savedMd !== null ? savedMd : mdPlaceholder)

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
// 注意：用 !== null 严格判断，避免用户主动清空内容（空字符串）后被示例覆写
const savedExcel = localStorage.getItem('marktrans_excel_cache')
const excelContent = ref(savedExcel !== null ? savedExcel : excelPlaceholder)
const excelPreviewHtml = computed(() => md.render(excelContent.value))

// ===== 防丢失：本地自动实时保存 (Auto Save) =====
// 双写策略：localStorage（同步镜像）+ Python 后端 state.json（真正持久化）
// pywebview 的 localStorage 在关闭程序后可能被清空，因此 Python 文件才是唯一可靠真源。
const _saveTimers = {}
function persistState(key, value) {
  // 1) localStorage 同步写入 —— 运行时快速读取用
  try { localStorage.setItem(key, value) } catch (_) { /* 配额超限忽略 */ }
  // 2) Python 后端异步写入（防抖 300ms，避免逐字符写文件）
  if (!window.pywebview || !window.pywebview.api) return
  if (_saveTimers[key]) clearTimeout(_saveTimers[key])
  _saveTimers[key] = setTimeout(async () => {
    try {
      await window.pywebview.api.save_state(key, value)
    } catch (e) {
      console.warn(`持久化失败 [${key}]:`, e)
    }
  }, 300)
}

// 当用户在代码模式输入时，实时静默保存
watch(markdownContent, (newVal) => {
  persistState('marktrans_md_cache', newVal)
})
// 当用户在 Excel 模式输入时，实时静默保存
watch(excelContent, (newVal) => {
  persistState('marktrans_excel_cache', newVal)
})

// ===== 暗黑模式 (Dark Mode) =====
// 初始化暗黑主题状态
const showTutorial = ref(false)
const isDarkMode = ref(localStorage.getItem('marktrans_theme') === 'dark')

// 监听主题切换，改变 HTML 属性并保持本地存储，同时联动 Vditor
watch(isDarkMode, (newVal) => {
  const themeName = newVal ? 'dark' : 'light'
  persistState('marktrans_theme', themeName)
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
  persistState('marktrans_ai_key', newVal.apiKey)
  persistState('marktrans_ai_url', newVal.baseUrl)
  persistState('marktrans_ai_model', newVal.model)
}, { deep: true })
watch(aiMessages, (newVal) => {
  persistState('marktrans_ai_msgs', JSON.stringify(newVal))
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
      // 1. 获取当前正在编辑的文本上下文
      let currentText = ''
      if (activeTab.value === 'md2doc') currentText = markdownContent.value
      else if (activeTab.value === 'rtf2md' && vditor.value) currentText = vditor.value.getValue()
      else if (activeTab.value === 'md2excel') currentText = excelContent.value

      // 2. 构造强制性系统约束 Prompt
      const systemPrompt = {
        role: 'system',
        content: `你是一个智能Copilot文档助手。当前用户正在工作的文本内容是：\n\n---\n${currentText}\n---\n如果用户要求你对文章进行翻译、重写或修改，请你**必须**将修改后完整的最新全文严格包裹在<<<<UPDATE_START>>>>和<<<<UPDATE_END>>>>这两个标记符之间。除了修改后的全文外，不要在标记内写任何废话。如果只是普通问答，则不要使用此标记。`
      }

      // 3. 将 system 注入到请求的最前面，不显示在前端给用户看
      const requestMessages = [systemPrompt, ...aiMessages.value]

      const res = await window.pywebview.api.chat_with_ai(
        aiConfig.value.baseUrl,
        aiConfig.value.apiKey,
        aiConfig.value.model,
        requestMessages
      )

      if (res.success) {
        let finalReply = res.reply

        // 4. 正则拦截与自动修改魔法
        const updateRegex = /<<<<UPDATE_START>>>>([\s\S]*?)<<<<UPDATE_END>>>>/
        const match = finalReply.match(updateRegex)

        if (match) {
          const newContent = match[1].trim()

          // 保存撤销快照 (后悔药)
          aiUndoSnapshot.value = { tab: activeTab.value, content: currentText }

          // 强行覆盖当前模式的输入框！
          if (activeTab.value === 'md2doc') markdownContent.value = newContent
          else if (activeTab.value === 'rtf2md' && vditor.value) vditor.value.setValue(newContent)
          else if (activeTab.value === 'md2excel') excelContent.value = newContent

          // 将 AI 回复里的长篇巨论替换为一句简短的提示
          finalReply = finalReply.replace(updateRegex, '\n\n*(✨ 已自动将修改后的最新内容同步至当前正文)*\n\n')
        }

        aiMessages.value.push({ role: 'assistant', content: finalReply })
      } else {
        throw new Error(res.error)
      }
    } else {
      throw new Error('请在桌面客户端环境运行该功能！')
    }
  } catch (error) {
    aiMessages.value.push({ role: 'assistant', content: `[接口返回错误] \n${error.message}` })
  } finally {
    isAiLoading.value = false
  }
}
const clearAiMessages = () => { aiMessages.value = [] }

// ================= AI 自动改写撤销快照 =================
const aiUndoSnapshot = ref(null)

const undoAiEdit = () => {
  if (!aiUndoSnapshot.value) return
  const { tab, content } = aiUndoSnapshot.value
  if (tab === 'md2doc') markdownContent.value = content
  else if (tab === 'rtf2md' && vditor.value) vditor.value.setValue(content)
  else if (tab === 'md2excel') excelContent.value = content

  aiUndoSnapshot.value = null
  aiMessages.value.push({ role: 'assistant', content: '🔙 已为您撤销刚才的自动修改。' })
}

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
  persistState('marktrans_ai_key', aiConfig.value.apiKey)
  persistState('marktrans_ai_url', aiConfig.value.baseUrl)
  persistState('marktrans_ai_model', aiConfig.value.model)
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

// ===== 启动时从 Python 后端恢复状态 =====
// pywebview 的 localStorage 在关闭后可能被清空，因此真正的历史数据
// 存放在 ~/.marktrans_data/state.json 中，每次启动时从此处批量恢复。
let _restoredState = null

async function restoreFromBackend() {
  if (!window.pywebview || !window.pywebview.api) return
  try {
    const state = await window.pywebview.api.load_all_state()
    if (!state || typeof state !== 'object') return
    _restoredState = state

    // 恢复 Markdown 内容（后端有值时才覆盖占位符）
    if (state['marktrans_md_cache'] != null) {
      markdownContent.value = state['marktrans_md_cache']
    }
    // 恢复 Excel 内容
    if (state['marktrans_excel_cache'] != null) {
      excelContent.value = state['marktrans_excel_cache']
    }
    // 恢复主题
    if (state['marktrans_theme']) {
      isDarkMode.value = state['marktrans_theme'] === 'dark'
    }
    // 恢复 AI 配置
    if (state['marktrans_ai_key']) aiConfig.value.apiKey = state['marktrans_ai_key']
    if (state['marktrans_ai_url']) aiConfig.value.baseUrl = state['marktrans_ai_url']
    if (state['marktrans_ai_model']) aiConfig.value.model = state['marktrans_ai_model']
    // 恢复 AI 对话记录
    if (state['marktrans_ai_msgs']) {
      try { aiMessages.value = JSON.parse(state['marktrans_ai_msgs']) } catch (_) { /* 忽略 */ }
    }
    // 恢复 Vditor 富文本内容（若 Vditor 已初始化则立即写入）
    if (state['marktrans_vditor_content'] && vditor.value) {
      try { vditor.value.setValue(state['marktrans_vditor_content']) } catch (_) { /* 忽略 */ }
    }
  } catch (e) {
    console.warn('从后端恢复状态失败:', e)
  }
}

// ===== Vditor 生命周期 =====
onMounted(() => {
  if (typeof document === 'undefined') return

  // pywebviewready 事件：JS API 就绪后从 Python 后端恢复历史状态
  // （若事件已错过则直接尝试恢复，load_all_state 内部有判空保护）
  window.addEventListener('pywebviewready', restoreFromBackend)
  // 兜底：若 pywebview 已就绪（事件已触发过），直接调用
  if (window.pywebview && window.pywebview.api) {
    restoreFromBackend()
  }

  // 重新初始化 Vditor
  vditor.value = new Vditor('vditor', {
    mode: 'wysiwyg',
    height: '100%',
    lang: 'zh_CN',
    // 关键优化：将 CDN 指向本地 public/vditor 目录（Vite 打包后位于 dist/vditor/），
    // 避免 Vditor 初始化时从 jsdelivr CDN 加载 i18n/icons/lute 等资源导致桌面端超时卡顿
    cdn: 'vditor',
    toolbarConfig: { pin: true },
    theme: isDarkMode.value ? 'dark' : 'classic',
    // 关闭 Vditor 自带 localStorage 缓存 —— 改由 Python 后端统一持久化，
    // 避免 Vditor 写入的 localStorage 被关闭时清空导致内容丢失
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
    // 内容变化时实时持久化到 Python 后端（防抖由 persistState 内部处理）
    input(content) {
      persistState('marktrans_vditor_content', content)
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

      // 若后端状态已先行加载（pywebviewready 早于 after），此刻补写 Vditor 内容
      if (_restoredState && _restoredState['marktrans_vditor_content']) {
        try { vditor.value.setValue(_restoredState['marktrans_vditor_content']) } catch (_) { /* 忽略 */ }
      }
    },
  })
})

onUnmounted(() => {
  // 移除 pywebviewready 监听，避免重复绑定
  window.removeEventListener('pywebviewready', restoreFromBackend)
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

// ================= 专业查找与替换逻辑 =================
const showFindReplace = ref(false)
const frMode = ref('find') // 'find' | 'replace'
const findText = ref('')
const replaceText = ref('')

// 定义输入框的 DOM 引用
const mdTextareaRef = ref(null)
const excelTextareaRef = ref(null)

// 查找替换悬浮窗位置样式（可自由拖动）
const frPanelStyle = ref({
  top: '120px',
  left: 'auto',
  right: '60px'
})

// 查找替换面板独立的拖拽状态（与 AI 面板解耦，避免互相干扰）
let isFrDragging = false
let frStartX = 0, frStartY = 0, frInitialLeft = 0, frInitialTop = 0

const startFrDrag = (e) => {
  // 点击按钮、tab、输入框时不触发拖拽
  const tag = e.target.tagName.toLowerCase()
  if (tag === 'button' || tag === 'input' || tag === 'label') return
  // 点击 tab 也不拖拽
  if (e.target.classList && e.target.classList.contains('fr-tab-item')) return

  isFrDragging = true
  frStartX = e.clientX
  frStartY = e.clientY

  const panel = document.querySelector('.find-replace-panel')
  if (!panel) return
  const rect = panel.getBoundingClientRect()
  frInitialLeft = rect.left
  frInitialTop = rect.top

  // 转为绝对定位以便平滑拖拽
  frPanelStyle.value.top = `${frInitialTop}px`
  frPanelStyle.value.left = `${frInitialLeft}px`
  frPanelStyle.value.right = 'auto'

  document.addEventListener('mousemove', onFrDrag)
  document.addEventListener('mouseup', stopFrDrag)
}

const onFrDrag = (e) => {
  if (!isFrDragging) return
  const dx = e.clientX - frStartX
  const dy = e.clientY - frStartY
  frPanelStyle.value.left = `${frInitialLeft + dx}px`
  frPanelStyle.value.top = `${frInitialTop + dy}px`
}

const stopFrDrag = () => {
  isFrDragging = false
  document.removeEventListener('mousemove', onFrDrag)
  document.removeEventListener('mouseup', stopFrDrag)
}

// 获取当前激活文本框和内容的辅助函数
const getActiveEditorInfo = () => {
  if (activeTab.value === 'md2doc') return { el: mdTextareaRef.value, text: markdownContent.value, setter: (val) => markdownContent.value = val }
  if (activeTab.value === 'md2excel') return { el: excelTextareaRef.value, text: excelContent.value, setter: (val) => excelContent.value = val }
  return null
}

// 拦截原生 Ctrl+F / Ctrl+H
// 使用 capture: true 在捕获阶段拦截，避免 Vditor 等子组件 stopPropagation 吞掉事件
onMounted(() => {
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key.toLowerCase() === 'f') { e.preventDefault(); e.stopPropagation(); showFindReplace.value = true; frMode.value = 'find' }
      if (e.key.toLowerCase() === 'h') { e.preventDefault(); e.stopPropagation(); showFindReplace.value = true; frMode.value = 'replace' }
    }
    if (e.key === 'Escape') showFindReplace.value = false
  }, true)
})

// 查找下一处
const findNext = () => {
  if (!findText.value) return
  const info = getActiveEditorInfo()
  if (!info) { alert('富文本模式不支持原生逐个定位，请使用全部替换或切回源码模式'); return }

  const el = info.el
  const currentPos = el.selectionEnd || 0
  let index = info.text.indexOf(findText.value, currentPos)

  if (index === -1) {
    index = info.text.indexOf(findText.value, 0) // 从头开始找
    if (index === -1) { alert('未找到匹配内容'); return }
  }

  el.focus()
  el.setSelectionRange(index, index + findText.value.length)
}

// 查找上一处
const findPrev = () => {
  if (!findText.value) return
  const info = getActiveEditorInfo()
  if (!info) return

  const el = info.el
  const currentPos = el.selectionStart || info.text.length
  let index = info.text.lastIndexOf(findText.value, currentPos - 1 - findText.value.length)

  if (index === -1) {
    index = info.text.lastIndexOf(findText.value) // 从末尾找
  }

  if (index !== -1) {
    el.focus()
    el.setSelectionRange(index, index + findText.value.length)
  }
}

// 替换当前选中处
const replaceCurrent = () => {
  const info = getActiveEditorInfo()
  if (!info) return
  const el = info.el

  const start = el.selectionStart
  const end = el.selectionEnd
  const selectedText = info.text.substring(start, end)

  if (selectedText === findText.value) {
    const newVal = info.text.substring(0, start) + replaceText.value + info.text.substring(end)
    info.setter(newVal)
    // 强制 Vue 更新 DOM 后恢复光标并找下一个
    setTimeout(() => {
      el.setSelectionRange(start, start + replaceText.value.length)
      findNext()
    }, 0)
  } else {
    findNext() // 如果当前没选中匹配项，先跳过去
  }
}

// 全部替换
const performReplaceAll = () => {
  if (!findText.value) return
  const target = findText.value
  const replacement = replaceText.value

  if (activeTab.value === 'md2doc') markdownContent.value = markdownContent.value.split(target).join(replacement)
  else if (activeTab.value === 'md2excel') excelContent.value = excelContent.value.split(target).join(replacement)
  else if (activeTab.value === 'rtf2md' && vditor.value) {
    vditor.value.setValue(vditor.value.getValue().split(target).join(replacement))
  }
  alert('批量替换完成！')
}
</script>

<template>
  <div class="app-container">
    <!-- ================= 顶部全局导航栏 ================= -->
    <header class="global-navbar">
      <div class="logo-area">
        <div class="logo-brand" @click="showTutorial = true" title="点击查看使用教程">
          <img :src="logoImg" alt="MarkTrans" class="logo-icon" />
          <span class="logo-text">MarkTrans</span>
        </div>
        <button class="theme-toggle-btn" @click="showFindReplace = !showFindReplace" title="查找与替换 (Ctrl+F)">
          🔍
        </button>
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
          <textarea ref="mdTextareaRef" v-model="markdownContent" class="md-textarea" :placeholder="mdPlaceholder" spellcheck="false"></textarea>
        </div>

        <div class="preview-section card-style">
          <div class="card-header">
            <span class="card-title">实时预览</span>
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
          <textarea ref="excelTextareaRef" v-model="excelContent" class="md-textarea" :placeholder="excelPlaceholder" spellcheck="false"></textarea>
        </div>
        <div class="preview-section card-style">
          <div class="card-header">
            <span class="card-title">表格预览</span>
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
          <button v-show="aiUndoSnapshot" @click="undoAiEdit" title="撤销 AI 的上一笔文章修改" style="color: #ff9800;">🔙 撤销修改</button>
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
          <h2>🚀 MarkTrans 使用指南</h2>
          <button class="close-btn" @click="showTutorial = false">✖</button>
        </div>
        <div class="tutorial-content">
          <h3>� 模式一 · Markdown 编辑与导出</h3>
          <ul>
            <li><strong>实时预览：</strong> 左侧书写源码，右侧即时渲染 Typora 风格排版与 KaTeX 数学公式。</li>
            <li><strong>四格式导出：</strong> 右上角一键导出 <code>HTML</code> / <code>Word</code> / <code>PDF</code> / <code>PPT</code>。</li>
            <li><strong>PPT 分页：</strong> 按 <code>##</code> 二级标题自动切页；勾选【PPT 辅助线】可预览分页位置。</li>
            <li><strong>导入文件：</strong> 点击虚线上传区可导入 <code>.md</code> / <code>.txt</code> / <code>.docx</code>（Word 自动转 Markdown）。</li>
          </ul>

          <h3>🎨 模式二 · 文字转 Markdown（Vditor 富文本）</h3>
          <ul>
            <li><strong>所见即所得：</strong> 像 Word 一样排版，底层自动生成标准 Markdown 源码。</li>
            <li><strong>离线防丢图：</strong> <code>Ctrl+V</code> 粘贴图片会自动转 Base64 嵌入文档，无需图床。</li>
            <li><strong>快捷公式：</strong> 输入 <code>$$</code> 唤出公式编辑器，支持 <code>Ctrl+B</code> 加粗等原生快捷键。</li>
          </ul>

          <h3>📊 模式三 · Markdown 转 Excel</h3>
          <ul>
            <li>粘贴含表格的 Markdown 文本，自动忽略非表格文字，精准剥离为 <code>.xlsx</code> / <code>.csv</code>。</li>
          </ul>

          <h3>🔍 查找与替换</h3>
          <ul>
            <li><strong>快捷键：</strong> <code>Ctrl+F</code> 查找 / <code>Ctrl+H</code> 替换 / <code>Esc</code> 关闭。</li>
            <li><strong>逐个定位：</strong> 上一处 / 下一处高亮选区；【替换】逐个替换当前匹配。</li>
            <li><strong>悬浮窗：</strong> 面板可拖拽到任意位置，仅作用于当前激活的模式。</li>
          </ul>

          <h3>🤖 AI 助手（左下角魔法棒）</h3>
          <ul>
            <li><strong>上下文感知：</strong> AI 会自动读取当前正文，对翻译/重写请求直接修改原文。</li>
            <li><strong>一键撤销：</strong> 点击 🔙 撤销按钮可恢复 AI 修改前的内容。</li>
            <li><strong>设置：</strong> ⚙️ 中配置 OpenAI 标准接口（API Key / Base URL / 模型名）。</li>
          </ul>

          <h3>💾 数据持久化与主题</h3>
          <ul>
            <li><strong>自动保存：</strong> 所有内容实时写入 <code>~/.marktrans_data/state.json</code>，关闭程序不丢失。</li>
            <li><strong>暗黑模式：</strong> 点击 🌙 切换全局主题，状态自动记忆。</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= 专业版查找替换面板（可拖拽悬浮窗） ================= -->
  <div v-show="showFindReplace" class="find-replace-panel card-style" :style="frPanelStyle">
    <div class="fr-header" @mousedown="startFrDrag">
      <div class="fr-tabs">
        <span class="fr-tab-item" :class="{ active: frMode === 'find' }" @click="frMode = 'find'" @mousedown.stop>查找(D)</span>
        <span class="fr-tab-item" :class="{ active: frMode === 'replace' }" @click="frMode = 'replace'" @mousedown.stop>替换(P)</span>
      </div>
      <button class="fr-close" @click="showFindReplace = false" @mousedown.stop>✖</button>
    </div>

    <div class="fr-body">
      <div class="fr-row">
        <label>查找内容(N)</label>
        <input v-model="findText" placeholder="输入要查找的文本..." class="fr-input" @keyup.enter="findNext" />
      </div>
      <div class="fr-row" v-show="frMode === 'replace'">
        <label>替换为(I)</label>
        <input v-model="replaceText" class="fr-input" />
      </div>
    </div>

    <div class="fr-footer">
      <div class="fr-actions-left" v-show="frMode === 'replace'">
        <button class="fr-btn-outline" @click="replaceCurrent">替换(R)</button>
        <button class="fr-btn-outline" @click="performReplaceAll">全部替换(A)</button>
      </div>
      <div class="fr-actions-right">
        <button class="fr-btn-outline" @click="findPrev">上一处(B)</button>
        <button class="fr-btn" @click="findNext">下一处(F)</button>
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

.logo-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s;
}
.logo-brand:hover {
  opacity: 0.8;
}

.logo-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  object-fit: cover;
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
  display: flex;
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

/* ================= 专业查找替换面板样式 ================= */
.find-replace-panel {
  position: fixed; top: 120px; right: 60px; width: 380px;
  background: #fbfbfb; border: 1px solid #dcdcdc; border-radius: 8px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.15); z-index: 1000;
  display: flex; flex-direction: column; overflow: hidden;
}
.fr-header {
  display: flex; justify-content: space-between; align-items: flex-end;
  padding: 10px 15px 0 15px; background: #f0f0f0; border-bottom: 1px solid #ddd;
  cursor: move; /* 悬浮窗头部可拖拽 */
  user-select: none;
}
.fr-tabs { display: flex; gap: 15px; }
.fr-tabs span {
  padding: 8px 5px; cursor: pointer; color: #555; font-size: 13px; font-weight: 500;
  border-bottom: 2px solid transparent; user-select: none;
}
.fr-tabs span.active { color: #0072ff; border-bottom-color: #0072ff; font-weight: bold; }
.fr-close { padding-bottom: 8px; background: none; border: none; cursor: pointer; color: #888; font-size: 14px; }
.fr-close:hover { color: #d32f2f; }
.fr-body { padding: 15px 20px; display: flex; flex-direction: column; gap: 12px; }
.fr-row { display: flex; align-items: center; gap: 10px; }
.fr-row label { width: 80px; font-size: 13px; color: #333; text-align: right; }
.fr-input { flex: 1; padding: 6px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; outline: none; }
.fr-input:focus { border-color: #0072ff; }
.fr-footer { display: flex; justify-content: space-between; padding: 12px 20px; background: #f5f5f5; border-top: 1px solid #eee; }
.fr-actions-left, .fr-actions-right { display: flex; gap: 8px; }
.fr-btn, .fr-btn-outline { padding: 6px 14px; font-size: 12px; border-radius: 4px; cursor: pointer; font-weight: 500; transition: all 0.2s; }
.fr-btn { background: #0072ff; color: #fff; border: 1px solid #0072ff; }
.fr-btn:hover { background: #005bb5; }
.fr-btn-outline { background: #fff; color: #333; border: 1px solid #ccc; }
.fr-btn-outline:hover { background: #e9e9e9; }

/* 适配暗黑模式 */
html[data-theme="dark"] .find-replace-panel { background: #252526; border-color: #444; }
html[data-theme="dark"] .fr-header, html[data-theme="dark"] .fr-footer { background: #1e1e1e; border-color: #333; }
html[data-theme="dark"] .fr-row label, html[data-theme="dark"] .fr-tabs span { color: #ccc; }
html[data-theme="dark"] .fr-tabs span.active { color: #61dafb; border-color: #61dafb; }
html[data-theme="dark"] .fr-input { background: #333; color: #fff; border-color: #555; }
html[data-theme="dark"] .fr-btn-outline { background: #333; color: #ddd; border-color: #555; }
html[data-theme="dark"] .fr-btn-outline:hover { background: #444; }
</style>
