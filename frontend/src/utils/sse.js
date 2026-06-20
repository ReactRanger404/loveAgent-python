/**
 * 解析 SSE 流式响应 — 后端将事件编码为 JSON 放在 data: 行
 *
 * data 格式：{"type":"think|text|think_clear|tool|file|error","content":"..."}
 * 不再依赖 event: 行，避免 SSE 分块边界导致事件类型丢失
 *
 * @param {Response} response fetch 响应对象
 * @param {object} handlers 事件处理器
 */
export async function parseSseStream(response, handlers) {
  const { onText, onTool, onThink, onThinkClear, onFile, onError, onDone } = handlers

  if (!response.ok) {
    onError?.(`请求失败: ${response.status} ${response.statusText}`)
    onDone?.()
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    onError?.('无法读取响应流')
    onDone?.()
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed || trimmed.startsWith(':')) continue

      if (trimmed.startsWith('data:')) {
        const raw = trimmed.slice(5).trim()
        if (!raw || raw === '[DONE]') continue

        try {
          const parsed = JSON.parse(raw)
          const type = parsed.type || ''
          const content = parsed.content ?? ''

          switch (type) {
            case 'think':
              onThink?.(content); break
            case 'think_clear':
              onThinkClear?.(); break
            case 'tool':
              onTool?.(content); break
            case 'file':
              onFile?.(content); break
            case 'error':
              onError?.(content); break
            case 'text':
              onText?.(content); break
            case 'done':
              onDone?.(); break
          }
        } catch (e) {
          // 旧格式兼容
          if (raw === '智能体未初始化' || raw.startsWith('请求失败')) {
            onError?.(raw)
          }
        }
      }
    }
  }

  // 处理 buffer 中残留的单行数据
  if (buffer.trim()) {
    const trimmed = buffer.trim()
    if (trimmed.startsWith('data:')) {
      const raw = trimmed.slice(5).trim()
      if (raw && raw !== '[DONE]') {
        try {
          const parsed = JSON.parse(raw)
          const type = parsed.type || ''
          const content = parsed.content ?? ''
          if (type === 'think') onThink?.(content)
          else if (type === 'think_clear') onThinkClear?.()
          else if (type === 'tool') onTool?.(content)
          else if (type === 'file') onFile?.(content)
          else if (type === 'text') onText?.(content)
          else if (type === 'error') onError?.(content)
          else if (type === 'done') onDone?.()
        } catch (e) {}
      }
    }
  }

  onDone?.()
}
