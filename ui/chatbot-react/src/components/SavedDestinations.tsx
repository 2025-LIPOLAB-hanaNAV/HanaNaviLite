import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { 
  BookMarked, 
  Search, 
  Edit3, 
  Pin, 
  PinOff, 
  FolderPlus, 
  Play, 
  Share2, 
  Trash2,
  Calendar,
  FileText,
  Tag,
  Filter,
  Grid3X3,
  List,
  Star,
  StarOff
} from 'lucide-react';
import { cn } from './ui/utils';

interface SavedDestination {
  id: string;
  title: string;
  summary: string;
  originalQuestion: string;
  evidenceCount: number;
  savedDate: string;
  tags: string[];
  category: string;
  isPinned: boolean;
  isStarred: boolean;
  personalNotes?: string;
  folder?: string;
}

interface SavedDestinationsProps {
  onDestinationClick?: (destination: SavedDestination) => void;
  onRerunJourney?: (destination: SavedDestination) => void;
}

export function SavedDestinations({ onDestinationClick, onRerunJourney }: SavedDestinationsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [editingDestination, setEditingDestination] = useState<SavedDestination | null>(null);
  const [destinations, setDestinations] = useState<SavedDestination[]>([
    {
      id: '1',
      title: '육아휴직 급여 지급 기준',
      summary: '근속 6개월 이상 직원, 기본급의 40%, 최대 1년까지 가능',
      originalQuestion: '육아휴직 급여 지급 기준이 뭔가요?',
      evidenceCount: 3,
      savedDate: '2025-09-07',
      tags: ['휴가', '급여', '복지'],
      category: '인사',
      isPinned: true,
      isStarred: true,
      personalNotes: '내년 3월에 신청 예정. 인사팀 김대리와 상담 완료.'
    },
    {
      id: '2',
      title: '재택근무 신청 절차',
      summary: '온라인 신청 시스템을 통해 주 2회까지 가능',
      originalQuestion: '재택근무 신청 절차는 어떻게 되나요?',
      evidenceCount: 2,
      savedDate: '2025-09-06',
      tags: ['재택근무', '신청절차'],
      category: '인사',
      isPinned: false,
      isStarred: false
    },
    {
      id: '3',
      title: '경비처리 시스템 사용법',
      summary: '모바일 앱을 통한 영수증 촬영 및 자동 처리 방법',
      originalQuestion: '경비처리 시스템 사용법을 알려주세요',
      evidenceCount: 4,
      savedDate: '2025-09-05',
      tags: ['경비', '시스템', '모바일'],
      category: '재무',
      isPinned: false,
      isStarred: true
    },
    {
      id: '4',
      title: 'VPN 접속 오류 해결',
      summary: '네트워크 설정 초기화 및 인증서 재설치 방법',
      originalQuestion: 'VPN 접속이 안 될 때 해결방법',
      evidenceCount: 2,
      savedDate: '2025-09-04',
      tags: ['VPN', '네트워크', '오류해결'],
      category: 'IT',
      isPinned: false,
      isStarred: false
    },
    {
      id: '5',
      title: '신용평가 시스템 권한',
      summary: '등급별 접근 권한 및 승인 절차 안내',
      originalQuestion: '신용평가 시스템 권한 신청',
      evidenceCount: 5,
      savedDate: '2025-09-03',
      tags: ['신용평가', '권한', '승인'],
      category: '리스크',
      isPinned: true,
      isStarred: false
    },
    {
      id: '6',
      title: '직원 할인 혜택',
      summary: '은행 상품 할인율 및 제휴사 할인 정보',
      originalQuestion: '직원 할인 혜택에 대해 알려주세요',
      evidenceCount: 3,
      savedDate: '2025-09-02',
      tags: ['할인', '복지', '혜택'],
      category: '복지',
      isPinned: false,
      isStarred: true
    }
  ]);

  const categories = ['all', '인사', '재무', 'IT', '리스크', '복지'];

  const filteredDestinations = destinations
    .filter(dest => {
      const matchesSearch = !searchQuery || 
        dest.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        dest.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
        dest.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesCategory = selectedCategory === 'all' || dest.category === selectedCategory;
      
      return matchesSearch && matchesCategory;
    })
    .sort((a, b) => {
      // Pinned items first
      if (a.isPinned && !b.isPinned) return -1;
      if (!a.isPinned && b.isPinned) return 1;
      
      // Then starred items
      if (a.isStarred && !b.isStarred) return -1;
      if (!a.isStarred && b.isStarred) return 1;
      
      // Finally by date (newest first)
      return new Date(b.savedDate).getTime() - new Date(a.savedDate).getTime();
    });

  const handleTogglePin = (id: string) => {
    setDestinations(prev => 
      prev.map(dest => 
        dest.id === id ? { ...dest, isPinned: !dest.isPinned } : dest
      )
    );
  };

  const handleToggleStar = (id: string) => {
    setDestinations(prev => 
      prev.map(dest => 
        dest.id === id ? { ...dest, isStarred: !dest.isStarred } : dest
      )
    );
  };

  const handleEditSave = (updatedDestination: SavedDestination) => {
    setDestinations(prev => 
      prev.map(dest => 
        dest.id === updatedDestination.id ? updatedDestination : dest
      )
    );
    setEditingDestination(null);
  };

  const handleDelete = (id: string) => {
    setDestinations(prev => prev.filter(dest => dest.id !== id));
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ko-KR', { 
      month: 'short', 
      day: 'numeric' 
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-medium flex items-center gap-2">
              <BookMarked className="h-6 w-6 text-primary" />
              저장된 방문지
            </h1>
            <p className="text-muted-foreground mt-1">
              {filteredDestinations.length}개의 방문지가 저장되어 있습니다
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            >
              {viewMode === 'grid' ? <List className="h-4 w-4" /> : <Grid3X3 className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        
        {/* Search and Filters */}
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="방문지 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex items-center gap-2">
            {categories.map((category) => (
              <Button
                key={category}
                variant={selectedCategory === category ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {category === 'all' ? '전체' : category}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {filteredDestinations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
              <BookMarked className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-2">
              <h3 className="font-medium">방문지를 찾을 수 없습니다</h3>
              <p className="text-muted-foreground">
                다른 검색어를 시도해보거나 필터를 조정해보세요.
              </p>
            </div>
          </div>
        ) : (
          <div className={cn(
            viewMode === 'grid' 
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
              : "space-y-4"
          )}>
            {filteredDestinations.map((destination) => (
              <Card 
                key={destination.id} 
                className={cn(
                  "p-4 hover:shadow-md transition-all duration-200 group cursor-pointer",
                  destination.isPinned && "ring-2 ring-primary/20 bg-primary/5"
                )}
                onClick={() => onDestinationClick?.(destination)}
              >
                {/* Card Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {destination.isPinned && (
                        <Pin className="h-4 w-4 text-primary flex-shrink-0" />
                      )}
                      <h3 className="font-medium truncate group-hover:text-primary transition-colors">
                        {destination.title}
                      </h3>
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {destination.category}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center gap-1 ml-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleStar(destination.id);
                      }}
                      className={cn(
                        "h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity",
                        destination.isStarred && "opacity-100 text-yellow-500"
                      )}
                    >
                      {destination.isStarred ? (
                        <Star className="h-4 w-4 fill-current" />
                      ) : (
                        <StarOff className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Summary */}
                <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                  {destination.summary}
                </p>

                {/* Tags */}
                {destination.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {destination.tags.slice(0, 3).map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                    {destination.tags.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{destination.tags.length - 3}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(destination.savedDate)}
                    </div>
                    <div className="flex items-center gap-1">
                      <FileText className="h-3 w-3" />
                      근거 {destination.evidenceCount}개
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 px-2"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingDestination(destination);
                          }}
                        >
                          <Edit3 className="h-3 w-3" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle>방문지 편집</DialogTitle>
                        </DialogHeader>
                        {editingDestination && (
                          <EditDestinationForm
                            destination={editingDestination}
                            onSave={handleEditSave}
                            onCancel={() => setEditingDestination(null)}
                          />
                        )}
                      </DialogContent>
                    </Dialog>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRerunJourney?.(destination);
                      }}
                    >
                      <Play className="h-3 w-3" />
                    </Button>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleTogglePin(destination.id);
                      }}
                    >
                      {destination.isPinned ? (
                        <PinOff className="h-3 w-3" />
                      ) : (
                        <Pin className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>

                {/* Personal Notes Preview */}
                {destination.personalNotes && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <p className="text-xs text-muted-foreground italic line-clamp-1">
                      📝 {destination.personalNotes}
                    </p>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Edit Destination Form Component
interface EditDestinationFormProps {
  destination: SavedDestination;
  onSave: (destination: SavedDestination) => void;
  onCancel: () => void;
}

function EditDestinationForm({ destination, onSave, onCancel }: EditDestinationFormProps) {
  const [formData, setFormData] = useState(destination);
  const [newTag, setNewTag] = useState('');

  const handleAddTag = () => {
    if (newTag.trim() && !formData.tags.includes(newTag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, newTag.trim()]
      }));
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove)
    }));
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium mb-2 block">제목</label>
        <Input
          value={formData.title}
          onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
        />
      </div>
      
      <div>
        <label className="text-sm font-medium mb-2 block">요약</label>
        <Textarea
          value={formData.summary}
          onChange={(e) => setFormData(prev => ({ ...prev, summary: e.target.value }))}
          rows={3}
        />
      </div>
      
      <div>
        <label className="text-sm font-medium mb-2 block">개인 노트</label>
        <Textarea
          value={formData.personalNotes || ''}
          onChange={(e) => setFormData(prev => ({ ...prev, personalNotes: e.target.value }))}
          placeholder="개인적인 메모를 추가하세요..."
          rows={2}
        />
      </div>
      
      <div>
        <label className="text-sm font-medium mb-2 block">태그</label>
        <div className="space-y-2">
          <div className="flex gap-2">
            <Input
              placeholder="새 태그 추가..."
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
            />
            <Button type="button" onClick={handleAddTag}>추가</Button>
          </div>
          <div className="flex flex-wrap gap-1">
            {formData.tags.map((tag) => (
              <Badge
                key={tag}
                variant="secondary"
                className="cursor-pointer"
                onClick={() => handleRemoveTag(tag)}
              >
                {tag} ×
              </Badge>
            ))}
          </div>
        </div>
      </div>
      
      <div className="flex justify-end gap-2 pt-4">
        <Button variant="outline" onClick={onCancel}>취소</Button>
        <Button onClick={() => onSave(formData)}>저장</Button>
      </div>
    </div>
  );
}