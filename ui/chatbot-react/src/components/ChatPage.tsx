import React, { useState, useRef, useEffect } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Separator } from './ui/separator';
import { ChatBubble } from './ChatBubble';
import { AnswerCard } from './AnswerCard';
import { SearchBar } from './SearchBar';
import { QualityDashboard } from './QualityDashboard';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  state?: 'loading' | 'success' | 'warning' | 'pii-detected';
  evidenceCount?: number;
  responseTime?: number;
  hasPII?: boolean;
  isEvidenceLow?: boolean;
  turnNumber?: number;
  confidence?: number;
  intent?: string;
  requiresSearch?: boolean;
  summary?: string;
}

interface EvidenceItem {
  id: string;
  title: string;
  section: string;
  page?: number;
  confidence: number;
  type: 'official' | 'unofficial' | 'restricted';
  preview: string;
}

interface ChatMode {
  id: string;
  name: string;
  description: string;
  icon: string;
}

interface FilterState {
  department: string;
  dateRange: string;
  documentType: string;
}

interface ChatPageProps {
  onEvidenceClick?: (evidence: EvidenceItem) => void;
}

export function ChatPage({ onEvidenceClick }: ChatPageProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentMode, setCurrentMode] = useState('quick');
  const [isPreloading, setIsPreloading] = useState(false);
  const [preloadOk, setPreloadOk] = useState<null | boolean>(null);
  const [filters, setFilters] = useState<FilterState>({
    department: 'all',
    dateRange: 'all',
    documentType: 'all'
  });
  const [showFilters, setShowFilters] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const API_BASE_URL = (import.meta as any)?.env?.VITE_API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');
  
  const chatModes: ChatMode[] = [
    { id: 'quick', name: '빠른답', description: '즉시 답변', icon: 'arrow-right' },
    { id: 'precise', name: '정밀검증', description: '상세 검증', icon: 'search' },
    { id: 'summary', name: '요약전용', description: '핵심만', icon: 'file-text' }
  ];

  const qualityMetrics = {
    responseTime: messages.length > 0 ? 
      messages.filter(m => m.type === 'assistant' && m.responseTime)
        .reduce((acc, m) => acc + (m.responseTime || 0), 0) / 
        messages.filter(m => m.type === 'assistant' && m.responseTime).length || 0 : 0,
    evidenceRate: messages.length > 0 ? 
      (messages.filter(m => m.type === 'assistant' && m.evidenceCount && m.evidenceCount > 0).length / 
       messages.filter(m => m.type === 'assistant').length) * 100 : 0,
    piiRate: messages.filter(m => m.hasPII).length / Math.max(messages.length, 1) * 100,
    targetResponseTime: 3,
    targetEvidenceRate: 95,
  };

  const sampleEvidences: EvidenceItem[] = [
    {
      id: '1',
      title: 'HR_휴가정책_v3.2.pdf',
      section: '섹션 3.1 - 육아휴직',
      page: 12,
      confidence: 98,
      type: 'official',
      preview: '근속 6개월 이상의 직원은 육아휴직을 신청할 수 있으며, 최대 1년까지 가능합니다...'
    },
    {
      id: '2',
      title: '사내 공지 2025-03-15',
      section: '육아휴직 급여 지급 안내',
      confidence: 95,
      type: 'official',
      preview: '육아휴직 기간 중에는 기본급의 40%를 육아휴직급여로 지급합니다...'
    }
  ];

  const createSession = async (): Promise<string | null> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/conversation/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: '새 대화',
          max_turns: 20,
          session_duration_hours: 24
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
      }

      const data = await response.json();
      return data.session_id;
    } catch (error) {
      console.error('Failed to create session:', error);
      setSessionError('세션 생성에 실패했습니다.');
      return null;
    }
  };

  const ensureSession = async (): Promise<string | null> => {
    if (sessionId) {
      return sessionId;
    }
    
    const newSessionId = await createSession();
    if (newSessionId) {
      setSessionId(newSessionId);
      setSessionError(null);
    }
    return newSessionId;
  };

  const handleSearch = async (query: string, files?: File[]) => {
    if (!query.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString('ko-KR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Add loading message
    const loadingMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: '',
      timestamp: '',
      state: 'loading'
    };
    
    setMessages(prev => [...prev, loadingMessage]);

    try {
      // Ensure session exists
      const currentSessionId = await ensureSession();
      if (!currentSessionId) {
        throw new Error('Failed to create session');
      }

      // Send message to backend
      const response = await fetch(`${API_BASE_URL}/api/v1/conversation/sessions/${currentSessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: query,
          search_engine_type: 'hybrid',
          include_context: true,
          max_context_turns: 3,
          chat_mode: currentMode  // 현재 선택된 챗 모드 전송
        })
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.statusText}`);
      }

      const data = await response.json();
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: data.assistant_message,
        timestamp: new Date().toLocaleTimeString('ko-KR', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
        state: 'success',
        evidenceCount: data.search_context?.requires_search ? 1 : 0,
        responseTime: data.response_time_ms / 1000, // Convert to seconds
        hasPII: false,
        isEvidenceLow: false,
        turnNumber: data.turn_number,
        confidence: data.confidence_score,
        intent: data.search_context?.intent,
        requiresSearch: data.search_context?.requires_search,
        summary: data.assistant_message.substring(0, 200) + (data.assistant_message.length > 200 ? '...' : '') // 간단한 요약
      };

      setMessages(prev => prev.slice(0, -1).concat(assistantMessage));
      setIsLoading(false);
      setSessionError(null);
      
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Fallback response
      const errorMessage: ChatMessage = {
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: '죄송합니다. 현재 시스템에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.',
        timestamp: new Date().toLocaleTimeString('ko-KR', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
        state: 'warning',
        evidenceCount: 0,
        responseTime: 0,
        hasPII: false,
        isEvidenceLow: true
      };

      setMessages(prev => prev.slice(0, -1).concat(errorMessage));
      setIsLoading(false);
      setSessionError(error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.');
    }
  };

  const handleRetry = () => {
    // Implement retry logic
  };

  const handleClearFilters = () => {
    setFilters({
      department: 'all',
      dateRange: 'all',
      documentType: 'all'
    });
  };

  const handleFeedback = (messageId: string, isHelpful: boolean, reason?: string) => {
    // Implement feedback logic
    console.log('Feedback:', { messageId, isHelpful, reason });
  };

  const handleContextRollback = () => {
    if (messages.length >= 2) {
      setMessages(prev => prev.slice(0, -2));
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Prepopulate chat via localStorage bridge from Documents tab
  useEffect(() => {
    const payload = localStorage.getItem('prepopulate_chat');
    if (payload && payload.trim()) {
      localStorage.removeItem('prepopulate_chat');
      // send without files
      handleSearch(payload);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nextDestinations = [
    {
      id: '1',
      title: '휴직신청서 작성',
      description: '온라인 신청 시스템으로 이동',
      type: 'process' as const
    },
    {
      id: '2',
      title: '인사팀 담당자 연락',
      description: '추가 문의사항 상담',
      type: 'contact' as const
    }
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Quality Dashboard */}
      <div className="p-4 border-b">
        <QualityDashboard 
          metrics={qualityMetrics}
          isLoading={isLoading}
          className="mb-4"
        />
      </div>

      {/* Chat Controls */}
      <div className="flex items-center justify-between p-4 border-b bg-elevated">
        <div className="flex items-center gap-4">
          {/* Mode Toggle */}
          <div className="flex items-center gap-2">
            <Icon name="settings" size={16} className="text-muted-foreground" />
            <Select value={currentMode} onValueChange={setCurrentMode}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {chatModes.map((mode) => {
                  return (
                    <SelectItem key={mode.id} value={mode.id}>
                      <div className="flex items-center gap-2">
                        <Icon name={mode.icon as any} size={16} />
                        <span>{mode.name}</span>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                try {
                  setIsPreloading(true);
                  setPreloadOk(null);
                  const res = await fetch(`${API_BASE_URL}/api/v1/conversation/preload`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mode: currentMode })
                  });
                  const data = await res.json();
                  setPreloadOk(!!data.success);
                } catch (e) {
                  setPreloadOk(false);
                } finally {
                  setIsPreloading(false);
                  // Auto-clear feedback after a short delay
                  setTimeout(() => setPreloadOk(null), 2000);
                }
              }}
              disabled={isPreloading}
              className={cn(
                preloadOk === true && 'border-success text-success',
                preloadOk === false && 'border-destructive text-destructive'
              )}
            >
              {isPreloading ? '준비중…' : preloadOk === true ? '준비완료' : preloadOk === false ? '실패' : '확정'}
            </Button>
          </div>

          {/* Filter Toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(showFilters && "bg-accent")}
          >
            <Icon name="filter" size={16} />
            필터
          </Button>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleContextRollback}
            disabled={messages.length < 2}
            className="text-muted-foreground"
          >
            <Icon name="arrow-right" size={16} />
            되돌리기
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      {showFilters && (
        <div className="p-4 border-b bg-muted/30">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Icon name="settings" size={16} className="text-muted-foreground" />
              <Select 
                value={filters.department} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, department: value }))}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">전체 부서</SelectItem>
                  <SelectItem value="hr">인사</SelectItem>
                  <SelectItem value="finance">재무</SelectItem>
                  <SelectItem value="it">IT</SelectItem>
                  <SelectItem value="risk">리스크</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Icon name="calendar" size={16} className="text-muted-foreground" />
              <Select 
                value={filters.dateRange} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, dateRange: value }))}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">전체 기간</SelectItem>
                  <SelectItem value="recent">최근 3개월</SelectItem>
                  <SelectItem value="year">1년 이내</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Icon name="file-text" size={16} className="text-muted-foreground" />
              <Select 
                value={filters.documentType} 
                onValueChange={(value) => setFilters(prev => ({ ...prev, documentType: value }))}
              >
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">모든 문서</SelectItem>
                  <SelectItem value="policy">정책 문서</SelectItem>
                  <SelectItem value="manual">매뉴얼</SelectItem>
                  <SelectItem value="notice">공지사항</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearFilters}
              className="text-muted-foreground hover:text-foreground"
            >
              <Icon name="help-circle" size={16} />
              필터 초기화
            </Button>
          </div>
        </div>
      )}

      {/* Session Error Display */}
      {sessionError && (
        <div className="p-4 border-b bg-destructive/10 border-destructive/20">
          <div className="flex items-center gap-2 text-destructive">
            <Icon name="alert-triangle" size={16} />
            <span className="text-sm">{sessionError}</span>
          </div>
        </div>
      )}

      {/* Chat Messages */}
      <div className="flex-1 overflow-auto p-4 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Icon name="search" size={32} className="text-primary" />
            </div>
            <div className="space-y-2">
              <h3 className="font-medium">아직 방문지가 없어요</h3>
              <p className="text-muted-foreground">
                첫 질문을 입력해 보세요.
              </p>
              {!sessionId && (
                <p className="text-xs text-muted-foreground">
                  첫 메시지를 보내면 새 대화 세션이 시작됩니다.
                </p>
              )}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div key={message.id} className="space-y-4">
                <ChatBubble
                  type={message.type}
                  content={message.content}
                  state={message.state}
                  timestamp={message.timestamp}
                  onRetry={handleRetry}
                  evidenceCount={message.evidenceCount}
                  responseTime={message.responseTime}
                  hasPII={message.hasPII}
                  isEvidenceLow={message.isEvidenceLow}
                />
                
                {/* Answer Card for assistant messages with evidence (only for info requests, not small talk) */}
                {message.type === 'assistant' && 
                 message.state === 'success' && 
                 message.evidenceCount && 
                 message.evidenceCount > 0 &&
                 message.intent !== 'small_talk' && (
                  <div className="ml-11">
                    <AnswerCard
                      id={message.id}
                      summary={message.summary || message.content}  // summary가 있으면 사용, 없으면 전체 내용
                      evidence={sampleEvidences}
                      preview="육아휴직 정책에 대한 상세한 내용은 사내 인트라넷의 HR 정책 섹션에서 확인하실 수 있습니다. 추가적으로 각 지점별로 차이가 있을 수 있으니 인사팀 담당자와 상담하시기 바랍니다."
                      nextDestinations={nextDestinations}
                      onEvidenceClick={onEvidenceClick}
                      className="mt-4"
                    />
                    
                    {/* Feedback Bar - only for info requests, not small talk */}
                    {message.intent !== 'small_talk' && (
                      <div className="flex items-center justify-center gap-4 mt-4 p-3 bg-muted/30 rounded-lg">
                        <span className="text-sm text-muted-foreground">이 답변이 도움되었나요?</span>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, true)}
                            className="text-muted-foreground hover:text-success"
                          >
                            <Icon name="check-circle" size={16} />
                            도움됨
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, false)}
                            className="text-muted-foreground hover:text-destructive"
                          >
                            <Icon name="help-circle" size={16} />
                            별로임
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Search Input */}
      <div className="p-4 border-t bg-elevated">
        <SearchBar
          onSearch={handleSearch}
          onVoiceToggle={setIsVoiceActive}
          isVoiceActive={isVoiceActive}
          isLoading={isLoading}
          placeholder="추가 질문을 입력하세요..."
        />
      </div>
    </div>
  );
}
