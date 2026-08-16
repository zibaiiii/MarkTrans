"""pywebview + Vue3 Markdown 编辑器后端入口。

启动后会加载同目录下 dist/index.html（由前端 `npm run build` 生成），
并通过 js_api 把导出能力暴露给前端 JS：window.pywebview.api.export_file(...)
"""

import os
import sys
import tempfile

import markdown
import pandas as pd
import webview
import pypandoc

# 输入格式：启用 hard_line_breaks 扩展，让单个回车也视为换行，
# 与前端 textarea 的软换行行为保持一致（HTML/DOCX/PDF 均生效）。
INPUT_FORMAT = 'markdown+hard_line_breaks'


class Api:
    """暴露给前端 JavaScript 调用的后端 API。"""

    def open_file(self):
        import webview
        import os
        import pypandoc

        windows = webview.windows
        if not windows:
            return None

        # 增加对 Word 文档的支持
        file_types = (
            '支持的文档 (*.md;*.txt;*.docx)',
            'Word 文档 (*.docx)',
            'Markdown 文件 (*.md)',
            '文本文档 (*.txt)',
            'All Files (*.*)'
        )
        result = windows[0].create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)

        if result and len(result) > 0:
            file_path = result[0]
            ext = os.path.splitext(file_path)[1].lower()
            try:
                if ext == '.docx':
                    # 黑科技：使用 Pandoc 将 Word 逆向解析为 Markdown 纯文本
                    # --wrap=none 用于防止 pandoc 自动给长段落换行断句
                    md_text = pypandoc.convert_file(file_path, 'markdown', extra_args=['--wrap=none'])
                    return md_text
                else:
                    # 普通文本文件直接读取
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
            except Exception as e:
                return f"读取或转换文件失败: {str(e)}"
        return None

    def export_file(self, file_type, markdown_content):
        """根据 file_type 将 markdown_content 转换并保存为对应文件。

        Args:
            file_type: 导出类型，支持 'html' / 'docx' / 'pdf'。
            markdown_content: 前端传来的 Markdown 源码字符串。

        Returns:
            保存成功时返回生成的文件绝对路径；失败时返回错误信息字符串。
        """
        file_type = (file_type or '').strip().lower()

        # Markdown 转 Excel/CSV：解析 Markdown 表格并导出
        if file_type in ('xlsx', 'csv'):
            try:
                html_str = markdown.markdown(markdown_content or '', extensions=['tables'])
                dfs = pd.read_html(html_str)
            except Exception as e:  # noqa: BLE001
                return f'表格解析失败: {e}'

            if not dfs:
                return '未检测到表格'

            # 统一弹保存对话框（与 md/html/docx/pdf 体验一致）
            ext = '.xlsx' if file_type == 'xlsx' else '.csv'
            result = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=f'export{ext}',
                file_types=(f'{file_type.upper()} files (*{ext})',),
            )
            if not result:
                return '已取消导出'
            if isinstance(result, (list, tuple)):
                save_path = result[0]
            else:
                save_path = result

            try:
                if file_type == 'csv':
                    # utf-8-sig: Excel 打开 CSV 不乱码
                    dfs[0].to_csv(save_path, index=False, encoding='utf-8-sig')
                else:
                    # Excel：每个 Markdown 表格依次写入 Sheet1 / Sheet2 ...
                    with pd.ExcelWriter(save_path, engine='openpyxl') as writer:
                        for idx, df in enumerate(dfs):
                            sheet_name = f'Sheet{idx + 1}'
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                return f'已导出: {save_path}'
            except Exception as e:  # noqa: BLE001
                return f'导出失败: {e}'

        # 导出 Markdown 源文件：无需 pandoc 转换，直接以 UTF-8 写入文本文件
        if file_type == 'md':
            result = webview.windows[0].create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename='export.md',
                file_types=('Markdown files (*.md)',),
            )
            if not result:
                return '已取消导出'
            if isinstance(result, (list, tuple)):
                save_path = result[0]
            else:
                save_path = result
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content or '')
                return f'已导出: {save_path}'
            except Exception as e:  # noqa: BLE001
                return f'导出失败: {e}'

        # 各类型对应的 pandoc 输出格式与文件扩展名
        format_map = {
            'html': ('html', '.html'),
            'docx': ('docx', '.docx'),
            'pdf': ('pdf', '.pdf'),
            'pptx': ('pptx', '.pptx'),
        }

        if file_type not in format_map:
            return f'不支持的导出类型: {file_type}'

        to_format, ext = format_map[file_type]

        # 弹出保存对话框，让用户选择保存位置
        result = webview.windows[0].create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=f'export.{ext}',
            file_types=(f'{file_type.upper()} files (*{ext})',),
        )
        if not result:
            return '已取消导出'

        # create_file_dialog 在不同后端返回 str 或 tuple
        if isinstance(result, (list, tuple)):
            save_path = result[0]
        else:
            save_path = result

        temp_files = []
        try:
            if file_type == 'pdf':
                # 针对 PDF 导出的终极中文排版修复：
                # CJKmainfont 会自动触发 xeCJK 宏包，解决中文段落不自动换行、
                # 文字冲出页面右侧边界的严重问题（mainfont 不会触发 xeCJK）。
                pdf_args = [
                    '--pdf-engine=xelatex',              # 强制使用支持 Unicode 的 XeLaTeX 引擎
                    '-V', 'geometry:margin=1in',         # 设置标准的 1 英寸页面边距
                    '-V', 'CJKmainfont=Microsoft YaHei', # 核心：指定微软雅黑，自动触发 xeCJK 解决中文不换行冲出边界的问题
                    '--wrap=preserve'                    # 保持代码块等内容的格式
                ]
                pypandoc.convert_text(
                    markdown_content,
                    to=to_format,
                    format=INPUT_FORMAT,
                    outputfile=save_path,
                    extra_args=pdf_args,
                )
            elif file_type == 'pptx':
                # 修复幻灯片粘连 Bug：强制指定滑动层级为 2（即 ## 作为新一页的标准）
                pptx_args = ['--slide-level=2']
                pypandoc.convert_text(
                    markdown_content,
                    'pptx',
                    format='markdown',
                    outputfile=save_path,
                    extra_args=pptx_args,
                )
            elif file_type == 'html':
                # 导出 HTML：输出完整 standalone 文档 + MathJax 公式 + GitHub Markdown CSS
                #
                # 为了让 github-markdown-css 生效，pandoc 渲染内容需要被包裹在
                # class="markdown-body" 的容器内，同时在 <head> 注入兜底样式，
                # 保证即便 CDN 不可达也有基础排版（居中、最大宽度等）。
                #
                # 由于 pandoc 的 --include-in-header / --include-before-body /
                # --include-after-body 只接受文件路径，这里用 NamedTemporaryFile
                # 创建临时文件，并在 finally 中清理。
                header_html = (
                    '<meta name="viewport" content="width=device-width, initial-scale=1">'
                    '<style>'
                    'body{'
                    '  max-width: 900px;'
                    '  margin: 0 auto;'
                    '  padding: 40px 24px;'
                    '  font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,'
                    '"Helvetica Neue",Arial,"Noto Sans",sans-serif;'
                    '  line-height: 1.7;'
                    '  color: #333;'
                    '  background: #fff;'
                    '}'
                    '</style>'
                )
                before_html = '<div class="markdown-body">'
                after_html = '</div>'

                def _write_tmp(content, suffix):
                    f = tempfile.NamedTemporaryFile(
                        mode='w', suffix=suffix, delete=False, encoding='utf-8'
                    )
                    try:
                        f.write(content)
                    finally:
                        f.close()
                    temp_files.append(f.name)
                    return f.name

                header_path = _write_tmp(header_html, '.html')
                before_path = _write_tmp(before_html, '.html')
                after_path = _write_tmp(after_html, '.html')

                mathjax_url = (
                    'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js'
                )
                css_url = (
                    'https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/'
                    '5.5.0/github-markdown.min.css'
                )

                extra_args = [
                    '--standalone',
                    f'--mathjax={mathjax_url}',
                    f'--css={css_url}',
                    '--include-in-header=' + header_path,
                    '--include-before-body=' + before_path,
                    '--include-after-body=' + after_path,
                    '--metadata', 'pagetitle=Exported Markdown',
                ]

                pypandoc.convert_text(
                    markdown_content,
                    to=to_format,
                    format=INPUT_FORMAT,
                    outputfile=save_path,
                    extra_args=extra_args,
                )
            else:
                # DOCX 等其它类型，保持默认
                pypandoc.convert_text(
                    markdown_content,
                    to=to_format,
                    format=INPUT_FORMAT,
                    outputfile=save_path,
                )
            return f'已导出: {save_path}'
        except Exception as e:  # noqa: BLE001
            return f'导出失败: {e}'
        finally:
            # 清理临时文件；忽略清理过程中的异常
            for p in temp_files:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except OSError:
                    pass

    def chat_with_ai(self, base_url, api_key, model, messages):
        """通过 Python 后端代理调用大模型接口，规避浏览器跨域 (CORS) 限制。

        使用标准库 urllib，无需引入额外依赖。返回 {success, reply} 或 {success, error}。
        """
        import urllib.request
        import json

        # 补全标准 OpenAI 兼容的路径后缀
        endpoint = base_url.rstrip('/')
        if not endpoint.endswith('/chat/completions'):
            endpoint += '/chat/completions'

        data = json.dumps({
            "model": model,
            "messages": messages
        }).encode('utf-8')

        req = urllib.request.Request(endpoint, data=data)
        req.add_header('Content-Type', 'application/json')
        # 部分特定平台可能要求不同的 Auth 格式，默认走标准的 Bearer
        req.add_header('Authorization', f'Bearer {api_key}')

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                return {"success": True, "reply": result['choices'][0]['message']['content']}
        except Exception as e:
            error_msg = str(e)
            # 尝试读取具体的接口报错信息（如 401 鉴权失败，404 不存在等）
            if hasattr(e, 'read'):
                try:
                    detail = e.read().decode('utf-8')
                    error_msg += f"\n详细信息: {detail}"
                except:
                    pass
            return {"success": False, "error": error_msg}


def get_resource_path():
    """获取前端打包产物的入口 HTML 路径（兼容开发环境与 PyInstaller 打包环境）。

    - 打包后（frozen）：PyInstaller 把 --add-data 注入的数据解压到临时目录
      sys._MEIPASS；打包命令会把 dist 文件夹注入到根目录，故拼接 'dist/index.html'。
    - 开发环境：vite 构建产物输出到 backend/dist/index.html（见 vite.config.js
      的 outDir: '../backend/dist'），故直接从本文件所在目录的 dist 子目录查找。
    """
    if getattr(sys, 'frozen', False):
        # 打包后，PyInstaller 会把数据解压到一个临时目录 sys._MEIPASS
        base_path = sys._MEIPASS
        return os.path.join(base_path, 'dist', 'index.html')
    else:
        # 开发环境下，直接到本文件同级目录的 dist 子目录找（vite 输出在此）
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, 'dist', 'index.html')


def setup_pandoc():
    """设置 pandoc 可执行文件路径（兼容开发环境与打包环境）。

    - 打包后（frozen）：pandoc.exe 由 --add-binary 注入到 sys._MEIPASS 根目录，
      需显式告知 pypandoc 其位置，否则运行时找不到 pandoc。
    - 开发环境：pypandoc 会自动从系统 PATH 查找 pandoc，无需干预。
    """
    if getattr(sys, 'frozen', False):
        pandoc_path = os.path.join(sys._MEIPASS, 'pandoc.exe')
        if os.path.exists(pandoc_path):
            pypandoc.pandoc_path = pandoc_path


def main():
    setup_pandoc()
    api = Api()
    html_path = get_resource_path()

    # 创建窗口：标题与打包产物名一致；保留最小尺寸约束提升体验
    # 创建窗口，设定黄金比例 1440x900，并限制最小尺寸
    webview.create_window(
        'MarkTrans',
        url=html_path,
        js_api=api,
        width=1024,
        height=700,
        min_size=(1024, 700),
    )

    # 关键：debug=False 彻底关闭开发者工具弹窗（正式发布）
    webview.start(debug=False)


if __name__ == '__main__':
    main()
