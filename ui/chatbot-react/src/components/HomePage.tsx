import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { SearchBar } from './SearchBar';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';
import { ImageWithFallback } from './figma/ImageWithFallback';

interface PopularQuestion {
  id: string;
  question: string;
  category: string;
  count: number;
}

interface DepartmentShortcut {
  id: string;
  name: string;
  icon: string;
  color: string;
  questions: string[];
}

interface PresetRoute {
  id: string;
  title: string;
  description: string;
  steps: number;
  category: string;
  icon: string;
}

interface HomePageProps {
  onSearch: (query: string, files?: File[]) => void;
  onQuestionClick: (question: string) => void;
  onPresetClick: (preset: PresetRoute) => void;
}

export function HomePage({ onSearch, onQuestionClick, onPresetClick }: HomePageProps) {
  const [selectedDepartment, setSelectedDepartment] = useState<string | null>(null);

  const popularQuestions: PopularQuestion[] = [
    { id: '1', question: '육아휴직 급여 지급 기준이 뭔가요?', category: '인사', count: 234 },
    { id: '2', question: '재택근무 신청 절차는 어떻게 되나요?', category: '인사', count: 189 },
    { id: '3', question: '경비처리 시스템 사용법을 알려주세요', category: '재무', count: 156 },
    { id: '4', question: 'VPN 접속이 안 될 때 해결방법', category: 'IT', count: 143 },
    { id: '5', question: '신용평가 시스템 권한 신청', category: '리스크', count: 98 },
  ];

  const departmentShortcuts: DepartmentShortcut[] = [
    {
      id: 'hr',
      name: '인사',
      icon: 'star',
      color: 'bg-blue-500',
      questions: ['휴가신청', '급여문의', '승진기준', '교육과정']
    },
    {
      id: 'finance',
      name: '재무',
      icon: 'arrow-right',
      color: 'bg-green-500',
      questions: ['경비처리', '예산신청', '회계처리', '지출승인']
    },
    {
      id: 'it',
      name: 'IT',
      icon: 'search',
      color: 'bg-purple-500',
      questions: ['시스템접근', 'VPN설정', '보안정책', '장비신청']
    },
    {
      id: 'risk',
      name: '리스크',
      icon: 'shield',
      color: 'bg-red-500',
      questions: ['신용평가', '위험관리', '규정준수', '내부통제']
    }
  ];

  const presetRoutes: PresetRoute[] = [
    {
      id: 'new-employee',
      title: '신규입사자 패스',
      description: '첫 출근부터 업무 시작까지 필요한 모든 절차',
      steps: 8,
      category: '인사',
      icon: '👋'
    },
    {
      id: 'expense-guide',
      title: '경비처리 가이드',
      description: '출장비부터 접대비까지 완벽 정리',
      steps: 5,
      category: '재무',
      icon: '💰'
    },
    {
      id: 'system-access',
      title: '시스템 접근 권한',
      description: '업무시스템 권한 신청 및 관리',
      steps: 6,
      category: 'IT',
      icon: '🔐'
    },
    {
      id: 'compliance-check',
      title: '규정 준수 체크',
      description: '컴플라이언스 관련 주요 체크포인트',
      steps: 7,
      category: '리스크',
      icon: '📋'
    }
  ];

  return (
    <div className="min-h-full bg-background">
      {/* Hero Section - Figma Inspired */}
      <div className="relative overflow-hidden min-h-[500px] flex items-center justify-center">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-accent/10 to-primary/5" />
        <div className="relative px-6 py-16 lg:py-24">
          <div className="max-w-5xl mx-auto text-center space-y-8">
            <div className="space-y-6">
              <div className="space-y-2">

                <h1 className="text-display font-extrabold text-foreground leading-tight">
                  어디로 떠나시겠어요?
                </h1>
              </div>
              <p className="text-subtitle max-w-3xl mx-auto">
                <span className="font-medium text-foreground">하나은행 직원만을 위한 스마트 정보 검색 시스템</span> 입니다. 
                <br />
                당신의 여정에 함께할게요.
              </p>
            </div>
            
            <div className="mt-12">
              <SearchBar
                onSearch={onSearch}
                placeholder="어디로 떠나시겠어요? (예: 육아휴직 급여 기준)"
                className="max-w-2xl mx-auto"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 pb-12 space-y-12">
        {/* Popular Questions */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <Icon name="arrow-right" size={24} className="text-primary" />
            <h2 className="text-2xl font-bold">인기 질문</h2>
          </div>
          
          <div className="grid gap-4">
            {popularQuestions.map((question) => (
              <Card 
                key={question.id}
                className="card-enhanced p-6 hover:shadow-xl cursor-pointer transition-all duration-300 hover:scale-[1.02]"
                onClick={() => onQuestionClick(question.question)}
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <p className="text-base font-semibold text-foreground mb-3">{question.question}</p>
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className="text-sm font-medium px-3 py-1">
                        {question.category}
                      </Badge>
                      <span className="text-sm text-muted-foreground font-medium">
                        {question.count}회 검색
                      </span>
                    </div>
                  </div>
                  <Icon name="arrow-right" size={20} className="text-muted-foreground" />
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Preset Routes */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <Icon name="arrow-right" size={24} className="text-primary" />
            <h2 className="text-2xl font-bold">상황별 프리셋 경로</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {presetRoutes.map((route) => (
              <Card 
                key={route.id}
                className="card-enhanced p-8 hover:shadow-xl cursor-pointer transition-all duration-300 group hover:scale-[1.02]"
                onClick={() => onPresetClick(route)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-4 mb-4">
                      <span className="text-4xl">{route.icon}</span>
                      <div>
                        <h3 className="text-xl font-bold group-hover:text-primary transition-colors mb-2">
                          {route.title}
                        </h3>
                        <Badge variant="outline" className="text-sm font-semibold px-3 py-1">
                          {route.category}
                        </Badge>
                      </div>
                    </div>
                    
                    <p className="text-base text-muted-foreground mb-4 leading-relaxed">
                      {route.description}
                    </p>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground font-medium">
                      <div className="flex items-center gap-2">
                        <Icon name="pin" size={16} />
                        {route.steps}단계
                      </div>
                    </div>
                  </div>
                  
                  <Icon name="arrow-right" size={20} className="text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </Card>
            ))}
          </div>
        </section>

        {/* Department Shortcuts */}
        <section>
          <div className="flex items-center gap-4 mb-8">
            <Icon name="settings" size={24} className="text-primary" />
            <h2 className="text-2xl font-bold">부서별 자주 찾는 항목</h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            {departmentShortcuts.map((dept) => {
              return (
                <Card
                  key={dept.id}
                  className={cn(
                    "card-enhanced p-6 cursor-pointer transition-all duration-300 hover:scale-105",
                    selectedDepartment === dept.id 
                      ? "ring-2 ring-primary bg-primary/10 shadow-xl" 
                      : "hover:shadow-lg"
                  )}
                  onClick={() => setSelectedDepartment(
                    selectedDepartment === dept.id ? null : dept.id
                  )}
                >
                  <div className="text-center space-y-4">
                    <div className={cn(
                      "w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-lg",
                      dept.color
                    )}>
                      <Icon name={dept.icon as any} size={28} className="text-white" />
                    </div>
                    <h3 className="text-lg font-bold">{dept.name}</h3>
                  </div>
                </Card>
              );
            })}
          </div>
          
          {selectedDepartment && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {departmentShortcuts
                .find(d => d.id === selectedDepartment)
                ?.questions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  className="button-primary text-white font-semibold py-3 px-4 border-0"
                  onClick={() => onQuestionClick(question)}
                >
                  {question}
                </Button>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}