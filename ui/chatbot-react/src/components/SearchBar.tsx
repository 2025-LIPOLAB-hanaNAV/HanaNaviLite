import React, { useState, useRef } from 'react';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface SearchBarProps {
  onSearch: (query: string, files?: File[]) => void;
  onVoiceToggle?: (isActive: boolean) => void;
  placeholder?: string;
  isVoiceActive?: boolean;
  isLoading?: boolean;
  className?: string;
  variant?: 'default' | 'focused' | 'with-voice' | 'with-file';
}

interface AttachedFile {
  file: File;
  preview?: string;
}

export function SearchBar({ 
  onSearch, 
  onVoiceToggle,
  placeholder = "어디로 가시나요? (예: 육아휴직 급여 기준)",
  isVoiceActive = false,
  isLoading = false,
  className,
  variant = 'default'
}: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() || attachedFiles.length > 0) {
      onSearch(query, attachedFiles.map(af => af.file));
      setQuery('');
      setAttachedFiles([]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    addFiles(files);
  };

  const addFiles = (files: File[]) => {
    const newAttachedFiles: AttachedFile[] = files.map(file => ({
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined
    }));
    setAttachedFiles(prev => [...prev, ...newAttachedFiles]);
  };

  const removeFile = (index: number) => {
    setAttachedFiles(prev => {
      const updated = [...prev];
      if (updated[index].preview) {
        URL.revokeObjectURL(updated[index].preview!);
      }
      updated.splice(index, 1);
      return updated;
    });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
  };

  const getFileIcon = (file: File) => {
    if (file.type.startsWith('image/')) return 'upload';
    return 'file-text';
  };

  return (
    <div className={cn("w-full max-w-4xl", className)}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <div 
          ref={dropZoneRef}
          className={cn(
            "relative rounded-2xl border-2 transition-all duration-200",
            isDragOver 
              ? "border-primary bg-primary/5" 
              : variant === 'focused'
              ? "border-primary shadow-md"
              : "border-border bg-elevated",
            "focus-within:border-primary focus-within:shadow-md"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {isDragOver && (
            <div className="absolute inset-0 bg-primary/10 rounded-2xl flex items-center justify-center z-10">
              <div className="text-center">
                <Icon name="upload" size={32} className="text-primary mx-auto mb-2" />
                <p className="text-primary font-medium">파일을 여기에 놓으세요</p>
              </div>
            </div>
          )}
          
          <div className="flex items-center p-6 gap-4">
            <Icon name="search" size={24} className="text-muted-foreground flex-shrink-0" />
            
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              className="border-0 bg-transparent text-xl px-0 shadow-none focus-visible:ring-0 font-normal placeholder:text-muted-foreground/60 placeholder:font-normal py-2"
              disabled={isLoading}
            />
            
            <div className="flex items-center gap-3 flex-shrink-0">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,image/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                className="text-muted-foreground hover:text-foreground p-3"
              >
                <Icon name="file-text" size={20} />
              </Button>
              
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onVoiceToggle?.(!isVoiceActive)}
                className={cn(
                  "text-muted-foreground hover:text-foreground p-3",
                  isVoiceActive && "text-primary bg-primary/10"
                )}
              >
                {isVoiceActive ? <Icon name="mic" size={20} /> : <Icon name="mic-off" size={20} />}
              </Button>
              
              <Button 
                type="submit" 
                size="lg"
                disabled={(!query.trim() && attachedFiles.length === 0) || isLoading}
                className="button-primary text-white font-bold px-10 py-4 border-0 ml-2"
              >
                {isLoading ? '검색 중...' : '검색'}
              </Button>
            </div>
          </div>
        </div>
        
        {/* Attached Files */}
        {attachedFiles.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {attachedFiles.map((attachedFile, index) => {
              const iconName = getFileIcon(attachedFile.file);
              return (
                <Badge
                  key={index}
                  variant="secondary"
                  className="flex items-center gap-2 px-3 py-2 text-sm"
                >
                  <Icon name={iconName as any} size={16} />
                  <span className="truncate max-w-24">
                    {attachedFile.file.name}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-4 w-4 p-0 hover:bg-destructive/20"
                    onClick={() => removeFile(index)}
                  >
                    <Icon name="help-circle" size={12} />
                  </Button>
                </Badge>
              );
            })}
          </div>
        )}
      </form>
      
      {/* Voice Active Indicator */}
      {isVoiceActive && (
        <div className="flex items-center justify-center mt-4">
          <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full">
            <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
            <span className="text-sm text-primary font-medium">음성 입력 중...</span>
          </div>
        </div>
      )}
    </div>
  );
}