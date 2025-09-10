import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
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

interface EvidencePanelProps {
  evidence: EvidenceItem;
  onClose: () => void;
}

export function EvidencePanel({ evidence, onClose }: EvidencePanelProps) {
  const [selectedText, setSelectedText] = useState('');
  const [showFullDocument, setShowFullDocument] = useState(false);

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

  const getEvidenceTypeIcon = (type: EvidenceItem['type']) => {
    switch (type) {
      case 'official':
        return 'check-circle';
      case 'unofficial':
        return 'alert-triangle';
      case 'restricted':
        return 'shield';
      default:
        return 'file-text';
    }
  };

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().length > 0) {
      setSelectedText(selection.toString());
    }
  };

  const handleCopyText = (text: string) => {
    navigator.clipboard.writeText(text);
    // Show toast notification (would implement with actual toast system)
    console.log('Copied to clipboard:', text);
  };

  const mockDocumentContent = `
3.1 육아휴직 신청 자격

하나은행 직원으로서 다음 조건을 만족하는 경우 육아휴직을 신청할 수 있습니다:

• 근속 6개월 이상의 정규직 직원
• 만 8세 이하 또는 초등학교 2학년 이하의 자녀를 양육하는 직원
• 배우자가 취업 중이거나 질병, 장애 등의 사유로 자녀를 돌볼 수 없는 경우

3.2 급여 지급 기준

육아휴직 기간 중 급여는 다음과 같이 지급됩니다:

근속기간별 지급율:
• 6개월 이상 1년 미만: 기본급의 40%
• 1년 이상 3년 미만: 기본급의 50%  
• 3년 이상: 기본급의 60%

지급 방법:
• 매월 25일 본인 계좌로 입금
• 최대 지급 기간: 1년
• 4대보험 본인 부담분 공제 후 지급

3.3 신청 절차

1. 휴직 시작일 30일 전까지 신청서 제출
2. 인사시스템을 통한 온라인 신청
3. 필요 서류: 가족관계증명서, 주민등록등본
4. 부서장 및 인사팀 승인
5. 승인 완료 후 휴직 개시
  `;

  const typeIconName = getEvidenceTypeIcon(evidence.type);

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Icon name="map-pin" size={16} className="text-primary flex-shrink-0" />
              <span className="text-sm font-medium text-primary">근거 상세</span>
            </div>
            
            <div className="flex items-center gap-3 mb-2">
              <Icon name={typeIconName} size={20} className="text-muted-foreground flex-shrink-0" />
              <h2 className="font-medium truncate">{evidence.title}</h2>
            </div>
            
            <div className="flex items-center gap-2 mb-2">
              <Badge 
                variant="outline" 
                className={cn("text-xs", getEvidenceTypeColor(evidence.type))}
              >
                {getEvidenceTypeLabel(evidence.type)}
              </Badge>
              <Badge variant="outline" className="text-xs">
                신뢰도 {evidence.confidence}%
              </Badge>
            </div>
            
            <p className="text-sm text-muted-foreground">
              {evidence.section}
              {evidence.page && ` · 페이지 ${evidence.page}`}
            </p>
          </div>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="flex-shrink-0"
          >
            <Icon name="x" size={16} />
          </Button>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-b">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFullDocument(!showFullDocument)}
            className="flex items-center gap-2"
          >
            <Icon name="book-open" size={16} />
            {showFullDocument ? '하이라이트만' : '전체 문서'}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2"
          >
            <ExternalLink className="h-4 w-4" />
            원문 보기
          </Button>
          
          {selectedText && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleCopyText(selectedText)}
              className="flex items-center gap-2"
            >
              <Copy className="h-4 w-4" />
              복사
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-4">
            {/* Preview Card */}
            <Card className="p-4 bg-accent/20 border-accent/30">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <Eye className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium mb-2">핵심 내용</h3>
                  <p 
                    className="text-sm leading-relaxed select-text cursor-text"
                    onMouseUp={handleTextSelection}
                  >
                    {evidence.preview}
                  </p>
                </div>
              </div>
            </Card>

            <Separator />

            {/* Document Content */}
            <div className="space-y-4">
              <h3 className="font-medium flex items-center gap-2">
                <FileText className="h-4 w-4" />
                문서 내용
              </h3>
              
              <Card className="p-4">
                <div 
                  className="prose prose-sm max-w-none select-text cursor-text whitespace-pre-line"
                  onMouseUp={handleTextSelection}
                >
                  {showFullDocument ? mockDocumentContent : (
                    <div className="space-y-4">
                      <div className="bg-yellow-100 dark:bg-yellow-900/20 p-3 rounded-lg border-l-4 border-yellow-400">
                        <p className="text-sm">
                          <span className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">
                            근속 6개월 이상
                          </span>의 정규직 직원이 
                          <span className="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">
                            육아휴직
                          </span>을 신청할 수 있으며, 최대 1년까지 가능합니다.
                        </p>
                      </div>
                      
                      <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border-l-4 border-blue-400">
                        <p className="text-sm">
                          육아휴직 기간 중에는 
                          <span className="bg-blue-200 dark:bg-blue-800 px-1 rounded">
                            기본급의 40%
                          </span>를 육아휴직급여로 지급하며, 매월 25일에 계좌로 입금됩니다.
                        </p>
                      </div>
                      
                      <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg border-l-4 border-green-400">
                        <p className="text-sm">
                          <span className="bg-green-200 dark:bg-green-800 px-1 rounded">
                            휴직 시작일 30일 전까지
                          </span> 인사팀에 신청서를 제출하시면 됩니다.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </div>

            <Separator />

            {/* Related Links */}
            <div className="space-y-4">
              <h3 className="font-medium flex items-center gap-2">
                <ArrowRight className="h-4 w-4" />
                관련 문서
              </h3>
              
              <div className="space-y-2">
                {[
                  { title: '육아휴직 신청서 양식', type: 'form' },
                  { title: '휴직 관련 FAQ', type: 'faq' },
                  { title: '복직 절차 안내', type: 'guide' }
                ].map((item, index) => (
                  <Card 
                    key={index}
                    className="p-3 hover:bg-accent/50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm font-medium">{item.title}</span>
                      </div>
                      <ExternalLink className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </Card>
                ))}
              </div>
            </div>

            {/* Page Jump */}
            <div className="space-y-4">
              <h3 className="font-medium">페이지 이동</h3>
              
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm">
                  페이지 {evidence.page || 12}로 이동
                </Button>
                <Button variant="outline" size="sm">
                  섹션 3.1로 이동
                </Button>
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* Selected Text Actions */}
      {selectedText && (
        <div className="p-4 border-t bg-accent/20">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">선택된 텍스트</p>
              <p className="text-xs text-muted-foreground truncate">
                "{selectedText}"
              </p>
            </div>
            
            <div className="flex items-center gap-2 ml-4">
              <Button
                size="sm"
                onClick={() => handleCopyText(selectedText)}
                className="flex items-center gap-1"
              >
                <Copy className="h-3 w-3" />
                복사
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedText('')}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}