import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { Skeleton } from './ui/skeleton';
import { Alert, AlertDescription } from './ui/alert';
import { Button } from './ui/button';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface ChatBubbleProps {
  type: 'user' | 'assistant' | 'system';
  content: string;
  state?: 'empty' | 'loading' | 'success' | 'warning' | 'pii-detected';
  timestamp?: string;
  className?: string;
  onRetry?: () => void;
  evidenceCount?: number;
  responseTime?: number;
  hasPII?: boolean;
  isEvidenceLow?: boolean;
}

export function ChatBubble({ 
  type, 
  content, 
  state = 'success', 
  timestamp,
  className,
  onRetry,
  evidenceCount = 0,
  responseTime,
  hasPII = false,
  isEvidenceLow = false
}: ChatBubbleProps) {
  const isUser = type === 'user';
  const isSystem = type === 'system';

  // Normalize common HTML breaks and spacing artifacts to Markdown-friendly newlines
  const normalizeMarkdown = (text: string) => {
    if (!text) return '';
    return text
      // Convert HTML <br> variants to newlines
      .replace(/<br\s*\/?>(\s*)/gi, '\n')
      // Basic HTML -> Markdown-ish conversions for common tags
      .replace(/<\/?ul>/gi, '')
      .replace(/<\/?ol>/gi, '')
      .replace(/<li>/gi, '- ')
      .replace(/<\/li>/gi, '\n')
      .replace(/<p>/gi, '')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<strong>/gi, '**')
      .replace(/<\/strong>/gi, '**')
      .replace(/<b>/gi, '**')
      .replace(/<\/b>/gi, '**')
      .replace(/<em>/gi, '*')
      .replace(/<\/em>/gi, '*')
      .replace(/<i>/gi, '*')
      .replace(/<\/i>/gi, '*')
      // Normalize CRLF
      .replace(/\r\n/g, '\n')
      // Collapse 3+ newlines to two (Markdown paragraph break)
      .replace(/\n{3,}/g, '\n\n')
      // Trim excessive leading/trailing whitespace
      .trim();
  };

  if (state === 'loading') {
    return (
      <div className={cn(
        "flex gap-3",
        isUser ? "justify-end" : "justify-start",
        className
      )}>
        {!isUser && (
          <Avatar className="h-8 w-8">
            <AvatarFallback>
              <Icon name="bot" size={16} />
            </AvatarFallback>
          </Avatar>
        )}
        
        <div className={cn(
          "max-w-[70%] space-y-2",
          isUser && "order-first"
        )}>
          <Card className="p-4">
            <div className="space-y-3">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-4 w-3/5" />
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (state === 'empty') {
    return null;
  }

  return (
    <div className={cn(
      "flex gap-3",
      isUser ? "justify-end" : "justify-start",
      className
    )}>
      {!isUser && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback>
            {isSystem ? (
              <Icon name="shield" size={16} />
            ) : (
              <Icon name="bot" size={16} />
            )}
          </AvatarFallback>
        </Avatar>
      )}
      
      <div className={cn(
        "max-w-[70%] space-y-2",
        isUser && "order-first"
      )}>
        <Card className={cn(
          "p-4",
          isUser 
            ? "bg-primary text-primary-foreground" 
            : state === 'warning' 
            ? "bg-warning/10 border-warning"
            : state === 'pii-detected'
            ? "bg-destructive/10 border-destructive"
            : "bg-card"
        )}>
          {/* PII Detection Warning */}
          {hasPII && !isUser && (
            <Alert className="mb-3 bg-destructive/20 border-destructive/30">
              <Icon name="shield" size={16} />
              <AlertDescription className="text-sm">
                개인정보로 의심되는 값은 자동 마스킹 되었어요.
              </AlertDescription>
            </Alert>
          )}

          {/* Low Evidence Warning */}
          {isEvidenceLow && !isUser && (
            <Alert className="mb-3 bg-warning/20 border-warning/30">
              <Icon name="alert-triangle" size={16} />
              <AlertDescription className="text-sm flex items-center justify-between">
                <span>근거가 부족해요. 정밀검증 모드로 전환할까요?</span>
                <Button size="sm" variant="outline" className="ml-2">
                  전환
                </Button>
              </AlertDescription>
            </Alert>
          )}

          <div className="text-sm leading-relaxed prose prose-sm max-w-none dark:prose-invert">
            {isUser ? (
              <div className="whitespace-pre-wrap">{normalizeMarkdown(content)}</div>
            ) : (
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                // Treat single newlines as <br/>
                // This helps with content coming from chat that uses single newlines
                breaks
                components={{
                  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc list-inside mb-2 last:mb-0 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal list-inside mb-2 last:mb-0 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="text-sm">{children}</li>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  code: ({ children }) => <code className="bg-muted px-1 py-0.5 rounded text-sm font-mono">{children}</code>,
                  pre: ({ children }) => <pre className="bg-muted p-3 rounded-md overflow-x-auto text-sm">{children}</pre>,
                  blockquote: ({ children }) => <blockquote className="border-l-4 border-muted pl-4 italic">{children}</blockquote>,
                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
                }}
              >
                {normalizeMarkdown(content)}
              </ReactMarkdown>
            )}
          </div>
          
          {/* Assistant message metadata */}
          {!isUser && type === 'assistant' && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-border/20">
              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                {responseTime && (
                  <div className="flex items-center gap-1">
                    <Icon name="clock" size={12} />
                    {responseTime.toFixed(1)}초
                  </div>
                )}
                
                {evidenceCount > 0 && (
                  <Badge variant="outline" className="text-xs">
                    근거 {evidenceCount}개
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-1">
                {state === 'warning' && onRetry && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={onRetry}
                    className="h-6 px-2"
                  >
                    <Icon name="refresh-cw" size={12} />
                  </Button>
                )}
              </div>
            </div>
          )}
        </Card>
        
        {timestamp && (
          <div className={cn(
            "text-xs text-muted-foreground px-3",
            isUser ? "text-right" : "text-left"
          )}>
            {timestamp}
          </div>
        )}
      </div>
      
      {isUser && (
        <Avatar className="h-8 w-8 flex-shrink-0">
          <AvatarFallback>
            <Icon name="user" size={16} />
          </AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
