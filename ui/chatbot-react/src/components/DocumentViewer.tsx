import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { 
  FileText, 
  Search, 
  Bookmark, 
  ZoomIn, 
  ZoomOut, 
  Download, 
  Share2,
  Eye,
  Table as TableIcon,
  Layers,
  Calendar,
  Building2,
  Lock,
  AlertTriangle
} from 'lucide-react';
import { cn } from './ui/utils';

interface DocumentPage {
  number: number;
  thumbnail: string;
  highlights: { text: string; position: { x: number; y: number } }[];
}

interface DocumentMeta {
  title: string;
  department: string;
  lastModified: string;
  version: string;
  author: string;
  accessLevel: 'public' | 'restricted' | 'confidential';
  pageCount: number;
  fileSize: string;
}

interface TableData {
  id: string;
  title: string;
  pageNumber: number;
  data: string[][];
  headers: string[];
}

interface BookmarkItem {
  id: string;
  title: string;
  pageNumber: number;
  type: 'section' | 'bookmark' | 'highlight';
}

export function DocumentViewer() {
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('document');
  const [selectedHighlight, setSelectedHighlight] = useState<string | null>(null);

  // Sample document data
  const documentMeta: DocumentMeta = {
    title: 'HR_휴가정책_v3.2.pdf',
    department: '인사팀',
    lastModified: '2025-08-15',
    version: '3.2',
    author: '김인사',
    accessLevel: 'public',
    pageCount: 24,
    fileSize: '2.4 MB'
  };

  const pages: DocumentPage[] = Array.from({ length: documentMeta.pageCount }, (_, i) => ({
    number: i + 1,
    thumbnail: `https://picsum.photos/200/300?random=${i}`,
    highlights: i === 11 ? [
      { text: '육아휴직', position: { x: 120, y: 150 } },
      { text: '근속 6개월 이상', position: { x: 200, y: 180 } }
    ] : []
  }));

  const bookmarks: BookmarkItem[] = [
    { id: '1', title: '1. 개요', pageNumber: 1, type: 'section' },
    { id: '2', title: '2. 연차휴가', pageNumber: 3, type: 'section' },
    { id: '3', title: '3. 육아휴직', pageNumber: 12, type: 'section' },
    { id: '4', title: '4. 병가', pageNumber: 18, type: 'section' },
    { id: '5', title: '급여 지급 기준', pageNumber: 12, type: 'highlight' },
    { id: '6', title: '신청 절차', pageNumber: 14, type: 'bookmark' }
  ];

  const tables: TableData[] = [
    {
      id: '1',
      title: '육아휴직 급여표',
      pageNumber: 13,
      headers: ['근속기간', '지급율', '최대기간'],
      data: [
        ['6개월 이상', '40%', '1년'],
        ['1년 이상', '50%', '1년'],
        ['3년 이상', '60%', '1년']
      ]
    },
    {
      id: '2',
      title: '연차 사용 기준',
      pageNumber: 5,
      headers: ['입사년차', '연차일수', '비고'],
      data: [
        ['1년차', '11일', '입사일 기준'],
        ['2년차', '15일', '근속년수 적용'],
        ['3년차 이상', '15일 + α', '근속가산']
      ]
    }
  ];

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  const handleZoom = (direction: 'in' | 'out') => {
    if (direction === 'in' && zoomLevel < 200) {
      setZoomLevel(prev => prev + 25);
    } else if (direction === 'out' && zoomLevel > 50) {
      setZoomLevel(prev => prev - 25);
    }
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Implement search logic
    console.log('Searching for:', query);
  };

  const getAccessLevelColor = (level: DocumentMeta['accessLevel']) => {
    switch (level) {
      case 'public':
        return 'text-success';
      case 'restricted':
        return 'text-warning';
      case 'confidential':
        return 'text-destructive';
      default:
        return 'text-muted-foreground';
    }
  };

  const getAccessLevelIcon = (level: DocumentMeta['accessLevel']) => {
    switch (level) {
      case 'public':
        return Eye;
      case 'restricted':
        return AlertTriangle;
      case 'confidential':
        return Lock;
      default:
        return Eye;
    }
  };

  const getBookmarkIcon = (type: BookmarkItem['type']) => {
    switch (type) {
      case 'section':
        return Layers;
      case 'highlight':
        return Search;
      case 'bookmark':
        return Bookmark;
      default:
        return Bookmark;
    }
  };

  return (
    <div className="h-full flex">
      {/* Left Sidebar */}
      <div className="w-80 border-r bg-elevated flex flex-col">
        {/* Document Info */}
        <div className="p-4 border-b">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <h2 className="font-medium truncate">{documentMeta.title}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    <Building2 className="h-3 w-3 mr-1" />
                    {documentMeta.department}
                  </Badge>
                  <Badge 
                    variant="outline" 
                    className={cn("text-xs", getAccessLevelColor(documentMeta.accessLevel))}
                  >
                    {React.createElement(getAccessLevelIcon(documentMeta.accessLevel), { className: "h-3 w-3 mr-1" })}
                    {documentMeta.accessLevel === 'public' && '공개'}
                    {documentMeta.accessLevel === 'restricted' && '제한'}
                    {documentMeta.accessLevel === 'confidential' && '기밀'}
                  </Badge>
                </div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              <div>페이지: {documentMeta.pageCount}</div>
              <div>크기: {documentMeta.fileSize}</div>
              <div>버전: v{documentMeta.version}</div>
              <div className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {new Date(documentMeta.lastModified).toLocaleDateString('ko-KR')}
              </div>
            </div>
            
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1">
                <Download className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" className="flex-1">
                <Share2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className="p-4 border-b">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="문서 내 검색..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Tabs for Navigation */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <div className="px-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="pages" className="text-xs">페이지</TabsTrigger>
              <TabsTrigger value="bookmarks" className="text-xs">북마크</TabsTrigger>
              <TabsTrigger value="tables" className="text-xs">표</TabsTrigger>
            </TabsList>
          </div>

          <div className="flex-1 overflow-hidden">
            {/* Pages Tab */}
            <TabsContent value="pages" className="h-full m-0 p-4">
              <ScrollArea className="h-full">
                <div className="grid grid-cols-3 gap-2">
                  {pages.map((page) => (
                    <Card
                      key={page.number}
                      className={cn(
                        "p-2 cursor-pointer transition-colors hover:bg-accent/50",
                        currentPage === page.number && "ring-2 ring-primary bg-primary/5"
                      )}
                      onClick={() => handlePageChange(page.number)}
                    >
                      <div className="aspect-[3/4] bg-muted rounded mb-2 relative">
                        <div className="absolute inset-0 bg-gradient-to-br from-slate-100 to-slate-200 rounded" />
                        {page.highlights.length > 0 && (
                          <div className="absolute top-1 right-1">
                            <div className="w-2 h-2 bg-primary rounded-full" />
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-center font-medium">{page.number}</p>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Bookmarks Tab */}
            <TabsContent value="bookmarks" className="h-full m-0 p-4">
              <ScrollArea className="h-full">
                <div className="space-y-2">
                  {bookmarks.map((bookmark) => {
                    const Icon = getBookmarkIcon(bookmark.type);
                    return (
                      <Card
                        key={bookmark.id}
                        className="p-3 cursor-pointer hover:bg-accent/50 transition-colors"
                        onClick={() => handlePageChange(bookmark.pageNumber)}
                      >
                        <div className="flex items-center gap-3">
                          <Icon className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium truncate">{bookmark.title}</p>
                            <p className="text-xs text-muted-foreground">
                              페이지 {bookmark.pageNumber}
                            </p>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </ScrollArea>
            </TabsContent>

            {/* Tables Tab */}
            <TabsContent value="tables" className="h-full m-0 p-4">
              <ScrollArea className="h-full">
                <div className="space-y-3">
                  {tables.map((table) => (
                    <Card 
                      key={table.id}
                      className="p-3 cursor-pointer hover:bg-accent/50 transition-colors"
                      onClick={() => handlePageChange(table.pageNumber)}
                    >
                      <div className="flex items-start gap-3">
                        <TableIcon className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium mb-1">{table.title}</p>
                          <p className="text-xs text-muted-foreground mb-2">
                            페이지 {table.pageNumber} • {table.data.length}행 × {table.headers.length}열
                          </p>
                          <div className="text-xs bg-muted/50 p-2 rounded">
                            <div className="grid grid-cols-3 gap-1 mb-1">
                              {table.headers.map((header, i) => (
                                <div key={i} className="font-medium truncate">
                                  {header}
                                </div>
                              ))}
                            </div>
                            {table.data.slice(0, 2).map((row, i) => (
                              <div key={i} className="grid grid-cols-3 gap-1 text-muted-foreground">
                                {row.map((cell, j) => (
                                  <div key={j} className="truncate">{cell}</div>
                                ))}
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Main Document Viewer */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="p-4 border-b bg-elevated flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                이전
              </Button>
              <span className="text-sm px-3 py-1 bg-muted rounded">
                {currentPage} / {documentMeta.pageCount}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(Math.min(documentMeta.pageCount, currentPage + 1))}
                disabled={currentPage === documentMeta.pageCount}
              >
                다음
              </Button>
            </div>
            
            <Separator orientation="vertical" className="h-6" />
            
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleZoom('out')}
                disabled={zoomLevel <= 50}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="text-sm px-2 py-1 bg-muted rounded min-w-16 text-center">
                {zoomLevel}%
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleZoom('in')}
                disabled={zoomLevel >= 200}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              OCR 지원
            </Badge>
          </div>
        </div>

        {/* Document Content */}
        <div className="flex-1 overflow-auto bg-slate-100 dark:bg-slate-900 p-4">
          <div className="max-w-4xl mx-auto">
            <Card 
              className="min-h-[800px] bg-white dark:bg-slate-800 shadow-lg relative"
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'top center' }}
            >
              <div className="p-8">
                {/* Document content simulation */}
                <div className="space-y-6">
                  <div className="text-center border-b pb-4">
                    <h1 className="text-xl font-bold">하나은행 휴가 정책</h1>
                    <p className="text-sm text-muted-foreground mt-2">
                      버전 3.2 | 인사팀 | 2025년 8월 15일
                    </p>
                  </div>
                  
                  {currentPage === 12 && (
                    <div className="space-y-4">
                      <h2 className="text-lg font-semibold">3. 육아휴직</h2>
                      
                      <div className="space-y-3">
                        <h3 className="font-medium">3.1 신청 자격</h3>
                        <div className="relative">
                          <p className="leading-relaxed">
                            <span 
                              className={cn(
                                "bg-primary/20 px-1 rounded",
                                selectedHighlight === 'eligible' && "bg-primary/40"
                              )}
                              onClick={() => setSelectedHighlight('eligible')}
                            >
                              근속 6개월 이상
                            </span>의 정규직 직원이 
                            <span 
                              className={cn(
                                "bg-primary/20 px-1 rounded",
                                selectedHighlight === 'leave' && "bg-primary/40"
                              )}
                              onClick={() => setSelectedHighlight('leave')}
                            >
                              육아휴직
                            </span>을 신청할 수 있으며, 
                            최대 1년까지 가능합니다. 육아휴직 기간 중에는 기본급의 40%를 
                            육아휴직급여로 지급하며, 매월 25일에 계좌로 입금됩니다.
                          </p>
                        </div>
                        
                        <h3 className="font-medium">3.2 신청 절차</h3>
                        <p className="leading-relaxed">
                          휴직 시작일 30일 전까지 인사팀에 신청서를 제출하시면 됩니다. 
                          온라인 시스템을 통해 신청이 가능하며, 필요 서류는 시스템에서 
                          자동으로 안내됩니다.
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {currentPage !== 12 && (
                    <div className="space-y-4">
                      <h2 className="text-lg font-semibold">
                        {currentPage}. 문서 내용 페이지 {currentPage}
                      </h2>
                      <p className="leading-relaxed text-muted-foreground">
                        이 페이지는 문서 뷰어의 데모 페이지입니다. 
                        실제 문서에서는 해당 페이지의 실제 내용이 표시됩니다.
                      </p>
                    </div>
                  )}
                </div>
              </div>
              
              {/* Page number indicator */}
              <div className="absolute bottom-4 right-4 text-xs text-muted-foreground">
                페이지 {currentPage}
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}