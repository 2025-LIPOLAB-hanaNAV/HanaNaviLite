import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { ScrollArea } from './ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

type HybridResult = {
  chunk_id: string;
  document_id?: number;
  title: string;
  content: string;
  snippet: string;
  vector_score: number;
  ir_score: number;
  fusion_score: number;
  rerank_score: number;
  rank: number;
  metadata?: {
    file_name?: string;
    file_type?: string;
    keywords?: string;
    chunk_index?: number;
    [k: string]: any;
  };
  source_types?: string[];
};

export function DocumentSearch() {
  const API_BASE_URL = 'http://localhost:8020';
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<HybridResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [topK, setTopK] = useState(20);
  const [fileTypeFilter, setFileTypeFilter] = useState<string>('all');
  const [adminBusy, setAdminBusy] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const doSearch = async () => {
    if (!query.trim()) return;
    setIsSearching(true);
    setResults([]);
    try {
      const params = new URLSearchParams({ query, top_k: String(topK) });
      const res = await fetch(`${API_BASE_URL}/api/v1/search/hybrid?${params.toString()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filters: fileTypeFilter !== 'all' ? { file_type: fileTypeFilter } : undefined,
        }),
      });
      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Search failed', e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setUploadMsg(null);
    try {
      const form = new FormData();
      form.append('file', files[0]);
      const res = await fetch(`${API_BASE_URL}/api/v1/etl/upload`, {
        method: 'POST',
        body: form,
      });
      const data = await res.json();
      if (res.ok) {
        setUploadMsg('업로드 완료. 백그라운드에서 파싱/인덱싱 중입니다. 잠시 후 검색에 반영됩니다.');
      } else {
        setUploadMsg(`업로드 실패: ${data?.detail || '알 수 없는 오류'}`);
      }
    } catch (e) {
      console.error('Upload failed', e);
      setUploadMsg('업로드 실패. 네트워크 또는 서버 오류.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const summarize = async (text: string) => {
    try {
      const params = new URLSearchParams({ text, style: 'executive' });
      const res = await fetch(`${API_BASE_URL}/api/v1/admin/summarize?${params.toString()}`, { method: 'POST' });
      const data = await res.json();
      return data?.summary as string;
    } catch (e) {
      console.error('Summarize failed', e);
      return '';
    }
  };

  const genQuestions = async (text: string, n = 3) => {
    try {
      const params = new URLSearchParams({ text, num_questions: String(n) });
      const res = await fetch(`${API_BASE_URL}/api/v1/admin/generate_questions?${params.toString()}`, { method: 'POST' });
      const data = await res.json();
      return (data?.questions as string[]) || [];
    } catch (e) {
      console.error('Question generation failed', e);
      return [];
    }
  };

  const clearCache = async () => {
    setAdminBusy(true);
    try {
      await fetch(`${API_BASE_URL}/api/v1/admin/clear_cache`, { method: 'POST' });
    } finally {
      setAdminBusy(false);
    }
  };

  const reindexAll = async () => {
    setAdminBusy(true);
    try {
      await fetch(`${API_BASE_URL}/api/v1/admin/reindex_documents`, { method: 'POST' });
    } finally {
      setAdminBusy(false);
    }
  };

  const prettyFileType = (ft?: string) => {
    if (!ft) return '기타';
    if (ft.startsWith('.')) return ft.slice(1).toUpperCase();
    return ft.toUpperCase();
  };

  const isImageType = (ft?: string) => {
    if (!ft) return false;
    const f = ft.toLowerCase();
    return ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'].includes(f);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="p-4 border-b bg-elevated flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-1">
          <div className="relative flex-1">
            <Icon name="search" size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="파싱된 문서 내용에서 검색..."
              className="pl-8"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  doSearch();
                }
              }}
            />
          </div>
          <Select value={String(topK)} onValueChange={(v) => setTopK(parseInt(v))}>
            <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
            <SelectContent>
              {[10, 20, 50].map(k => <SelectItem key={k} value={String(k)}>{k}개</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={fileTypeFilter} onValueChange={setFileTypeFilter}>
            <SelectTrigger className="w-36"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">모든 유형</SelectItem>
              <SelectItem value=".pdf">PDF</SelectItem>
              <SelectItem value=".docx">DOCX</SelectItem>
              <SelectItem value=".xlsx">XLSX</SelectItem>
              <SelectItem value=".txt">TXT</SelectItem>
              <SelectItem value=".md">MD</SelectItem>
              <SelectItem value=".jpg">이미지</SelectItem>
              <SelectItem value=".png">PNG</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={doSearch} disabled={isSearching} className="min-w-24">
            {isSearching ? '검색 중...' : '검색'}
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <input ref={fileInputRef} type="file" className="hidden" onChange={(e) => handleUpload(e.target.files)} />
          <Button variant="outline" onClick={() => fileInputRef.current?.click()} disabled={isUploading}>
            <Icon name="upload" size={16} />
            {isUploading ? '업로드 중...' : '업로드'}
          </Button>
          <Button variant="outline" onClick={clearCache} disabled={adminBusy}>
            캐시 비우기
          </Button>
          <Button variant="outline" onClick={reindexAll} disabled={adminBusy}>
            전체 재색인
          </Button>
        </div>
      </div>

      {uploadMsg && (
        <div className="p-3 bg-muted/30 border-b text-sm">{uploadMsg}</div>
      )}

      {/* Results */}
      <div className="flex-1 overflow-auto p-4">
        {results.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            파싱 문서 검색 결과가 여기에 표시됩니다.
          </div>
        ) : (
          <div className="grid gap-3">
            {results.map((r) => {
              const ft = r.metadata?.file_type;
              return (
                <Card key={r.chunk_id} className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline" className="text-xs">
                          {prettyFileType(ft)}
                        </Badge>
                        {isImageType(ft) && (
                          <Badge variant="outline" className="text-xs">OCR</Badge>
                        )}
                        <span className="text-xs text-muted-foreground">Rank {r.rank}</span>
                        <span className="text-xs text-muted-foreground">F:{r.fusion_score.toFixed(3)}</span>
                      </div>
                      <div className="font-medium truncate">
                        {r.metadata?.file_name || r.title || '제목 없음'}
                      </div>
                      <div className="text-sm text-muted-foreground mt-1 line-clamp-3">
                        {r.snippet || r.content?.slice(0, 240)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          const sum = await summarize(r.snippet || r.content || '');
                          if (sum) alert(sum);
                        }}
                      >
                        요약
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={async () => {
                          const qs = await genQuestions(r.snippet || r.content || '');
                          if (qs.length) alert(qs.map((q, i) => `${i + 1}. ${q}`).join('\n'));
                        }}
                      >
                        질문 생성
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

