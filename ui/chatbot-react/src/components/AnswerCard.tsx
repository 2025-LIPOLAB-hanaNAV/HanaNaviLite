import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface EvidenceItem {
  id: string;
  title: string;
  section: string;
  page?: number;
  confidence: number;
  type: 'official' | 'unofficial' | 'restricted';
  preview: string;
}

interface NextDestination {
  id: string;
  title: string;
  description: string;
  type: 'document' | 'contact' | 'process';
}

interface AnswerCardProps {
  id: string;
  summary: string;
  evidence: EvidenceItem[];
  preview?: string;
  nextDestinations: NextDestination[];
  onEvidenceClick?: (evidence: EvidenceItem) => void;
  onDestinationClick?: (destination: NextDestination) => void;
  onSave?: (id: string) => void;
  onShare?: (id: string) => void;
  isSaved?: boolean;
  className?: string;
}

export function AnswerCard({
  id,
  summary,
  evidence,
  preview,
  nextDestinations,
  onEvidenceClick,
  onDestinationClick,
  onSave,
  onShare,
  isSaved = false,
  className
}: AnswerCardProps) {
  const [expandedSections, setExpandedSections] = useState({
    evidence: false,
    preview: false,
    destinations: false
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const getEvidenceTypeColor = (type: EvidenceItem['type']) => {
    switch (type) {
      case 'official':
        return 'bg-success text-success-foreground';
      case 'unofficial':
        return 'bg-warning text-warning-foreground';
      case 'restricted':
        return 'bg-destructive text-destructive-foreground';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const getEvidenceTypeLabel = (type: EvidenceItem['type']) => {
    switch (type) {
      case 'official':
        return '공식문서';
      case 'unofficial':
        return '비공식';
      case 'restricted':
        return '권한제한';
      default:
        return '일반';
    }
  };

  return (
    <Card className={cn("p-6 space-y-6", className)}>
      {/* Header with Actions */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon name="map-pin" size={16} className="text-primary" />
            <span className="text-sm font-medium text-primary">답변 경로</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onSave?.(id)}
            className={cn(
              "text-muted-foreground hover:text-foreground",
              isSaved && "text-primary"
            )}
          >
            {isSaved ? (
              <Icon name="bookmark-check" size={16} />
            ) : (
              <Icon name="bookmark" size={16} />
            )}
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onShare?.(id)}
            className="text-muted-foreground hover:text-foreground"
          >
            <Icon name="share-2" size={16} />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground"
          >
            <Icon name="more-horizontal" size={16} />
          </Button>
        </div>
      </div>

      {/* Summary Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">요약</h3>
        </div>
        <p className="leading-relaxed text-foreground">
          {summary}
        </p>
      </div>

      <Separator />

      {/* Evidence Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon name="book-open" size={16} className="text-accent" />
            <h3 className="font-medium">핵심 근거</h3>
            <Badge variant="outline">{evidence.length}개</Badge>
          </div>
          
          {evidence.length > 2 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => toggleSection('evidence')}
            >
              {expandedSections.evidence ? '접기' : '더보기'}
            </Button>
          )}
        </div>
        
        <div className="space-y-2">
          {evidence
            .slice(0, expandedSections.evidence ? undefined : 2)
            .map((item) => (
            <Card 
              key={item.id}
              className="p-3 hover:bg-accent/50 cursor-pointer transition-colors"
              onClick={() => onEvidenceClick?.(item)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon name="file-text" size={16} className="text-muted-foreground flex-shrink-0" />
                    <span className="font-medium text-sm truncate">
                      {item.title}
                    </span>
                    <Badge 
                      variant="outline" 
                      className={cn("text-xs", getEvidenceTypeColor(item.type))}
                    >
                      {getEvidenceTypeLabel(item.type)}
                    </Badge>
                  </div>
                  
                  <div className="text-xs text-muted-foreground mb-2">
                    {item.section}
                    {item.page && ` · p.${item.page}`}
                    <span className="ml-2">신뢰도 {item.confidence}%</span>
                  </div>
                  
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {item.preview}
                  </p>
                </div>
                
                <Button variant="ghost" size="sm" className="flex-shrink-0">
                  <Icon name="external-link" size={12} />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Preview Section */}
      {preview && (
        <>
          <Separator />
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Icon name="eye" size={16} className="text-muted-foreground" />
                <h3 className="font-medium">미리보기</h3>
              </div>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => toggleSection('preview')}
              >
                {expandedSections.preview ? '접기' : '펼치기'}
              </Button>
            </div>
            
            <Card className="p-4 bg-muted/30">
              <p className={cn(
                "text-sm leading-relaxed text-muted-foreground",
                !expandedSections.preview && "line-clamp-3"
              )}>
                {preview}
              </p>
            </Card>
          </div>
        </>
      )}

      {/* Next Destinations */}
      {nextDestinations.length > 0 && (
        <>
          <Separator />
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Icon name="arrow-right" size={16} className="text-primary" />
              <h3 className="font-medium">다음 경유지</h3>
            </div>
            
            <div className="grid gap-2">
              {nextDestinations.map((destination) => (
                <Button
                  key={destination.id}
                  variant="outline"
                  className="justify-start h-auto p-3"
                  onClick={() => onDestinationClick?.(destination)}
                >
                  <div className="text-left">
                    <div className="font-medium text-sm">{destination.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {destination.description}
                    </div>
                  </div>
                  <Icon name="arrow-right" size={16} className="ml-auto flex-shrink-0" />
                </Button>
              ))}
            </div>
          </div>
        </>
      )}
    </Card>
  );
}