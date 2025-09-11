import React, { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

type Document = {
  id: number;
  file_name: string;
  file_type: string;
  file_size: number;
  status: 'processed' | 'failed' | 'processing';
  created_at: string;
  updated_at: string;
  processed_at?: string;
  keywords?: string;
  upload_token?: string;
  content_length: number;
};

type DocumentDetail = Document & {
  file_path: string;
  chunks: Array<{
    id: number;
    chunk_index: number;
    chunk_length: number;
    created_at: string;
  }>;
  chunk_count: number;
};

export function DocumentManager() {
  const resolveApiBase = () => {
    const env = (import.meta as any)?.env?.VITE_API_BASE_URL;
    if (env) return env;
    if (typeof window !== 'undefined') {
      const origin = window.location.origin;
      // 3000번 또는 3001번 포트에서 실행 중이면 프록시를 통해 /api 호출
      if (origin.includes(':3000') || origin.includes(':3001')) {
        return origin;
      }
      // 8020번 포트에서 직접 실행 중이면 그대로 사용
      if (origin.includes(':8020')) {
        return origin;
      }
      return 'http://localhost:8020';
    }
    return 'http://localhost:8020';
  };
  
  const API_BASE_URL = resolveApiBase();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', '100');
      if (statusFilter !== 'all') {
        params.set('status_filter', statusFilter);
      }
      
      const res = await fetch(`${API_BASE_URL}/api/v1/etl/documents?${params.toString()}`);
      const data = await res.json();
      
      if (res.ok && data.documents) {
        setDocuments(data.documents);
      } else {
        console.error('Failed to load documents:', data);
      }
    } catch (e) {
      console.error('Error loading documents:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocumentDetail = async (documentId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/etl/documents/${documentId}`);
      const data = await res.json();
      
      if (res.ok) {
        setSelectedDoc(data);
      } else {
        console.error('Failed to load document detail:', data);
        alert(`문서 상세 조회 실패: ${data.detail || '알 수 없는 오류'}`);
      }
    } catch (e) {
      console.error('Error loading document detail:', e);
      alert('문서 상세 조회 중 오류가 발생했습니다.');
    }
  };

  const deleteDocument = async (documentId: number) => {
    if (!confirm('정말로 이 문서를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      return;
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/etl/documents/${documentId}`, {
        method: 'DELETE'
      });
      const data = await res.json();
      
      if (res.ok) {
        alert('문서가 성공적으로 삭제되었습니다.');
        loadDocuments(); // 목록 새로고침
        if (selectedDoc?.id === documentId) {
          setSelectedDoc(null);
        }
      } else {
        alert(`문서 삭제 실패: ${data.detail || '알 수 없는 오류'}`);
      }
    } catch (e) {
      console.error('Error deleting document:', e);
      alert('문서 삭제 중 오류가 발생했습니다.');
    }
  };

  const reprocessDocument = async (documentId: number) => {
    if (!confirm('이 문서를 다시 처리하시겠습니까?')) {
      return;
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/etl/documents/${documentId}/reprocess`, {
        method: 'POST'
      });
      const data = await res.json();
      
      if (res.ok) {
        alert('문서 재처리가 시작되었습니다. 잠시 후 상태를 확인해주세요.');
        loadDocuments();
      } else {
        alert(`문서 재처리 실패: ${data.detail || '알 수 없는 오류'}`);
      }
    } catch (e) {
      console.error('Error reprocessing document:', e);
      alert('문서 재처리 중 오류가 발생했습니다.');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ko-KR');
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'processed':
        return <Badge className="bg-green-100 text-green-800">처리완료</Badge>;
      case 'failed':
        return <Badge className="bg-red-100 text-red-800">실패</Badge>;
      case 'processing':
        return <Badge className="bg-yellow-100 text-yellow-800">처리중</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredDocuments = documents.filter(doc =>
    searchTerm === '' || 
    doc.file_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.keywords && doc.keywords.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  useEffect(() => {
    loadDocuments();
  }, [statusFilter]);

  return (
    <div className="h-full flex">
      {/* 문서 목록 */}
      <div className="w-1/2 border-r flex flex-col">
        <div className="p-4 border-b bg-elevated">
          <div className="flex items-center gap-3 mb-3">
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="문서명 또는 키워드로 검색..."
              className="flex-1"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">전체</SelectItem>
                <SelectItem value="processed">처리완료</SelectItem>
                <SelectItem value="failed">실패</SelectItem>
                <SelectItem value="processing">처리중</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={loadDocuments} disabled={isLoading} variant="outline">
              <Icon name="refresh-cw" size={16} />
              새로고침
            </Button>
          </div>
          <div className="text-sm text-muted-foreground">
            총 {filteredDocuments.length}개 문서
          </div>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-muted-foreground">로딩 중...</div>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="flex items-center justify-center h-32">
              <div className="text-muted-foreground">등록된 문서가 없습니다.</div>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredDocuments.map((doc) => (
                <Card
                  key={doc.id}
                  className={cn(
                    "p-3 cursor-pointer hover:bg-muted/50 transition-colors",
                    selectedDoc?.id === doc.id && "ring-2 ring-primary"
                  )}
                  onClick={() => loadDocumentDetail(doc.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusBadge(doc.status)}
                        <Badge variant="outline" className="text-xs">
                          {doc.file_type.toUpperCase().replace('.', '')}
                        </Badge>
                      </div>
                      <div className="font-medium truncate text-sm">
                        {doc.file_name}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        크기: {formatFileSize(doc.file_size)} | 
                        생성: {formatDate(doc.created_at)}
                      </div>
                      {doc.content_length > 0 && (
                        <div className="text-xs text-muted-foreground">
                          콘텐츠: {doc.content_length.toLocaleString()} 글자
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          reprocessDocument(doc.id);
                        }}
                        disabled={doc.status === 'processing'}
                        className="text-xs px-2 py-1"
                        title="재처리"
                      >
                        🔄 재처리
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteDocument(doc.id);
                        }}
                        className="text-xs px-2 py-1 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                        title="삭제"
                      >
                        🗑️ 삭제
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 문서 상세 */}
      <div className="w-1/2 flex flex-col">
        {selectedDoc ? (
          <>
            <div className="p-4 border-b bg-elevated">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold truncate">{selectedDoc.file_name}</h3>
                  <div className="flex items-center gap-2 mt-2">
                    {getStatusBadge(selectedDoc.status)}
                    <Badge variant="outline">
                      {selectedDoc.file_type.toUpperCase().replace('.', '')}
                    </Badge>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => reprocessDocument(selectedDoc.id)}
                    disabled={selectedDoc.status === 'processing'}
                    className="px-3 py-2"
                  >
                    🔄 재처리
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => deleteDocument(selectedDoc.id)}
                    className="px-3 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200"
                  >
                    🗑️ 삭제
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-4">
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">기본 정보</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="font-medium">파일 크기:</span> {formatFileSize(selectedDoc.file_size)}
                    </div>
                    <div>
                      <span className="font-medium">콘텐츠 길이:</span> {selectedDoc.content_length.toLocaleString()} 글자
                    </div>
                    <div>
                      <span className="font-medium">생성일:</span> {formatDate(selectedDoc.created_at)}
                    </div>
                    <div>
                      <span className="font-medium">수정일:</span> {formatDate(selectedDoc.updated_at)}
                    </div>
                    {selectedDoc.processed_at && (
                      <div className="col-span-2">
                        <span className="font-medium">처리완료일:</span> {formatDate(selectedDoc.processed_at)}
                      </div>
                    )}
                  </div>
                </div>

                {selectedDoc.keywords && (
                  <div>
                    <h4 className="font-medium mb-2">키워드</h4>
                    <div className="flex flex-wrap gap-2">
                      {selectedDoc.keywords.split(',').map((keyword, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {keyword.trim()}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <h4 className="font-medium mb-2">청크 정보</h4>
                  <div className="text-sm text-muted-foreground mb-2">
                    총 {selectedDoc.chunk_count}개의 청크로 분할됨
                  </div>
                  {selectedDoc.chunks.length > 0 && (
                    <div className="space-y-2 max-h-64 overflow-auto">
                      {selectedDoc.chunks.map((chunk) => (
                        <div key={chunk.id} className="p-2 bg-muted/30 rounded text-sm">
                          <div className="flex justify-between">
                            <span>청크 #{chunk.chunk_index}</span>
                            <span>{chunk.chunk_length} 글자</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <h4 className="font-medium mb-2">파일 경로</h4>
                  <div className="text-xs text-muted-foreground bg-muted/30 p-2 rounded break-all">
                    {selectedDoc.file_path}
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            문서를 선택하여 상세 정보를 확인하세요.
          </div>
        )}
      </div>
    </div>
  );
}