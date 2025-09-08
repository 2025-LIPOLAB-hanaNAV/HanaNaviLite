import React, { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Message = { 
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    content: string
    score?: number
  }>
}

const ChatApp: React.FC = () => {
  const API_BASE = 'http://localhost:8001/api/v1'
  
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showSources, setShowSources] = useState(true)
  const [systemHealth, setSystemHealth] = useState<any>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => { 
    endRef.current?.scrollIntoView({ behavior: 'smooth' }) 
  }, [messages])

  // 시스템 상태 확인
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE}/health`)
        if (response.ok) {
          const data = await response.json()
          setSystemHealth(data)
        }
      } catch (error) {
        console.error('Health check failed:', error)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000) // 30초마다 확인
    return () => clearInterval(interval)
  }, [])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    
    setError(null)
    const userMessage: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      // RAG 쿼리 실행
      const response = await fetch(`${API_BASE}/rag/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ query: userMessage.content })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const result = await response.json()
      
      const assistantMessage: Message = {
        role: 'assistant',
        content: result.answer || '답변을 생성할 수 없습니다.',
        sources: result.sources || []
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (err: any) {
      setError(err.message || '오류가 발생했습니다.')
      // 오류 메시지도 채팅에 표시
      const errorMessage: Message = {
        role: 'assistant',
        content: `죄송합니다. 오류가 발생했습니다: ${err.message}`
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    setError(null)
  }

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* 메인 채팅 영역 */}
      <div className="flex-1 flex flex-col">
        {/* 헤더 */}
        <header className="bg-white border-b px-6 py-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">HanaNaviLite Chatbot</h1>
              <p className="text-sm text-gray-600">RAG 기반 문서 검색 챗봇</p>
            </div>
            <div className="flex items-center gap-4">
              {systemHealth && (
                <div className="flex items-center gap-2 text-sm">
                  <div className={`w-2 h-2 rounded-full ${systemHealth.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
                  <span className={systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'}>
                    {systemHealth.status === 'healthy' ? '정상' : '오류'}
                  </span>
                  <span className="text-gray-500">
                    메모리: {systemHealth.details?.memory?.percentage}%
                  </span>
                </div>
              )}
              <button 
                onClick={clearChat}
                className="px-3 py-1 text-sm border rounded-md hover:bg-gray-50"
              >
                대화 지우기
              </button>
            </div>
          </div>
        </header>

        {/* 메시지 영역 */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-6 py-8">
            {messages.length === 0 && (
              <div className="text-center text-gray-500">
                <div className="mb-4">
                  <div className="text-6xl mb-4">🤖</div>
                  <h2 className="text-xl font-semibold mb-2">HanaNaviLite에 오신 것을 환영합니다</h2>
                  <p>궁금한 것을 물어보세요. 문서 기반으로 정확한 답변을 드리겠습니다.</p>
                </div>
              </div>
            )}
            
            <div className="space-y-6">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
                    message.role === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-white border shadow-sm'
                  }`}>
                    {message.role === 'assistant' ? (
                      <div className="prose prose-sm max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    )}
                    
                    {/* 소스 표시 (어시스턴트 메시지에만) */}
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && showSources && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="text-xs font-medium text-gray-600 mb-2">참고 문서:</div>
                        <div className="space-y-1">
                          {message.sources.slice(0, 3).map((source, idx) => (
                            <div key={idx} className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                              <div className="truncate">
                                {source.content.substring(0, 100)}...
                              </div>
                              {source.score && (
                                <div className="text-gray-400 mt-1">
                                  관련도: {(source.score * 100).toFixed(1)}%
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
            
            {loading && (
              <div className="flex justify-start mt-6">
                <div className="bg-white border rounded-lg px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                    <span className="text-sm text-gray-600">답변을 생성하고 있습니다...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={endRef} />
          </div>
        </main>

        {/* 입력 영역 */}
        <footer className="border-t bg-white">
          <div className="max-w-4xl mx-auto px-6 py-4">
            {error && (
              <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="text-sm text-red-700">오류: {error}</div>
              </div>
            )}
            
            <div className="flex items-end gap-3">
              <div className="flex-1">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="질문을 입력하세요... (Enter로 전송, Shift+Enter로 줄바꿈)"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={1}
                  style={{ minHeight: '50px', maxHeight: '150px' }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendMessage()
                    }
                  }}
                />
              </div>
              <button
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? '전송 중...' : '전송'}
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showSources}
                    onChange={(e) => setShowSources(e.target.checked)}
                  />
                  참고 문서 표시
                </label>
              </div>
              <div>
                {systemHealth?.details?.database && (
                  <span>문서 {systemHealth.details.database.documents_count}개 • 청크 {systemHealth.details.database.chunks_count}개</span>
                )}
              </div>
            </div>
          </div>
        </footer>
      </div>

      {/* 사이드바 (문서 업로드) */}
      <aside className="w-80 bg-white border-l">
        <div className="p-6">
          <h3 className="font-semibold mb-4">문서 관리</h3>
          
          {/* 파일 업로드 */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              문서 업로드
            </label>
            <input
              type="file"
              accept=".pdf,.docx,.xlsx,.txt,.md"
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              onChange={async (e) => {
                const file = e.target.files?.[0]
                if (!file) return
                
                const formData = new FormData()
                formData.append('file', file)
                
                try {
                  const response = await fetch(`${API_BASE}/etl/upload`, {
                    method: 'POST',
                    body: formData
                  })
                  
                  if (response.ok) {
                    const result = await response.json()
                    alert(`파일 업로드 성공: ${result.message}`)
                    // 시스템 상태 다시 확인
                    const healthResponse = await fetch(`${API_BASE}/health`)
                    if (healthResponse.ok) {
                      setSystemHealth(await healthResponse.json())
                    }
                  } else {
                    alert('파일 업로드 실패')
                  }
                } catch (error) {
                  alert('파일 업로드 중 오류 발생')
                }
              }}
            />
            <p className="text-xs text-gray-500 mt-1">
              PDF, DOCX, XLSX, TXT, MD 파일 지원
            </p>
          </div>

          {/* 시스템 정보 */}
          {systemHealth && (
            <div className="space-y-3">
              <h4 className="font-medium text-gray-700">시스템 상태</h4>
              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span>상태:</span>
                  <span className={systemHealth.status === 'healthy' ? 'text-green-600' : 'text-red-600'}>
                    {systemHealth.status === 'healthy' ? '정상' : '오류'}
                  </span>
                </div>
                {systemHealth.details?.memory && (
                  <div className="flex justify-between">
                    <span>메모리:</span>
                    <span>{systemHealth.details.memory.used_gb}GB / {systemHealth.details.memory.total_gb}GB</span>
                  </div>
                )}
                {systemHealth.details?.database && (
                  <>
                    <div className="flex justify-between">
                      <span>문서:</span>
                      <span>{systemHealth.details.database.documents_count}개</span>
                    </div>
                    <div className="flex justify-between">
                      <span>청크:</span>
                      <span>{systemHealth.details.database.chunks_count}개</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}

export default ChatApp