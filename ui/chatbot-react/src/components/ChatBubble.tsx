import React from 'react';
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

          <div className="whitespace-pre-wrap text-sm leading-relaxed">
            {content}
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