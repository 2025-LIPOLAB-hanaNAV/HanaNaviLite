import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Alert, AlertDescription } from './ui/alert';
import { 
  Settings, 
  Database, 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  TrendingUp, 
  Users, 
  FileText, 
  RefreshCw,
  BarChart3,
  Trophy,
  Zap,
  Shield
} from 'lucide-react';
import { cn } from './ui/utils';

interface KnowledgeConnector {
  id: string;
  name: string;
  type: 'SharePoint' | 'Confluence' | 'Drive';
  status: 'connected' | 'error' | 'syncing';
  documentCount: number;
  lastSync: string;
  errorCount: number;
}

interface QualityMetric {
  department: string;
  responseTimeTarget: number; // percentage achieving target
  evidenceRate: number;
  piiCompliance: number; // percentage achieving 0% PII
  overallScore: number;
  ranking: number;
}

interface UsageData {
  hour: string;
  queries: number;
  department: string;
}

export function AdminConsole() {
  const [activeTab, setActiveTab] = useState('overview');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const knowledgeConnectors: KnowledgeConnector[] = [
    {
      id: '1',
      name: 'HR SharePoint',
      type: 'SharePoint',
      status: 'connected',
      documentCount: 1247,
      lastSync: '2025-09-08T09:15:00',
      errorCount: 0
    },
    {
      id: '2',
      name: 'IT Confluence',
      type: 'Confluence',
      status: 'syncing',
      documentCount: 892,
      lastSync: '2025-09-08T08:30:00',
      errorCount: 0
    },
    {
      id: '3',
      name: 'Finance Drive',
      type: 'Drive',
      status: 'error',
      documentCount: 634,
      lastSync: '2025-09-07T14:20:00',
      errorCount: 3
    },
    {
      id: '4',
      name: 'Risk Management',
      type: 'SharePoint',
      status: 'connected',
      documentCount: 445,
      lastSync: '2025-09-08T09:00:00',
      errorCount: 0
    }
  ];

  const qualityLeague: QualityMetric[] = [
    {
      department: '인사팀',
      responseTimeTarget: 95,
      evidenceRate: 98,
      piiCompliance: 100,
      overallScore: 97.7,
      ranking: 1
    },
    {
      department: '리스크팀',
      responseTimeTarget: 88,
      evidenceRate: 96,
      piiCompliance: 100,
      overallScore: 94.7,
      ranking: 2
    },
    {
      department: 'IT팀',
      responseTimeTarget: 82,
      evidenceRate: 94,
      piiCompliance: 98,
      overallScore: 91.3,
      ranking: 3
    },
    {
      department: '재무팀',
      responseTimeTarget: 79,
      evidenceRate: 92,
      piiCompliance: 100,
      overallScore: 90.3,
      ranking: 4
    },
    {
      department: '영업팀',
      responseTimeTarget: 76,
      evidenceRate: 89,
      piiCompliance: 96,
      overallScore: 87.0,
      ranking: 5
    }
  ];

  const usageHeatmap: UsageData[] = [
    // Sample data for visualization
    { hour: '09:00', queries: 45, department: '인사' },
    { hour: '10:00', queries: 67, department: '재무' },
    { hour: '11:00', queries: 89, department: 'IT' },
    { hour: '14:00', queries: 123, department: '영업' },
    { hour: '15:00', queries: 98, department: '리스크' },
    { hour: '16:00', queries: 76, department: '인사' },
  ];

  const totalDocuments = knowledgeConnectors.reduce((sum, conn) => sum + conn.documentCount, 0);
  const connectedSources = knowledgeConnectors.filter(conn => conn.status === 'connected').length;
  const errorSources = knowledgeConnectors.filter(conn => conn.status === 'error').length;

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call
    setTimeout(() => {
      setIsRefreshing(false);
    }, 2000);
  };

  const getStatusColor = (status: KnowledgeConnector['status']) => {
    switch (status) {
      case 'connected':
        return 'text-success';
      case 'error':
        return 'text-destructive';
      case 'syncing':
        return 'text-warning';
      default:
        return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (status: KnowledgeConnector['status']) => {
    switch (status) {
      case 'connected':
        return CheckCircle;
      case 'error':
        return AlertTriangle;
      case 'syncing':
        return RefreshCw;
      default:
        return Clock;
    }
  };

  const getRankingIcon = (ranking: number) => {
    switch (ranking) {
      case 1:
        return '🥇';
      case 2:
        return '🥈';
      case 3:
        return '🥉';
      default:
        return `#${ranking}`;
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-medium flex items-center gap-2">
              <Settings className="h-6 w-6 text-primary" />
              운영자 콘솔
            </h1>
            <p className="text-muted-foreground mt-1">
              하나 내비 시스템 모니터링 및 관리
            </p>
          </div>
          
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            {isRefreshing ? '업데이트 중...' : '새로고침'}
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <div className="px-6 pt-4">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="overview">개요</TabsTrigger>
              <TabsTrigger value="knowledge">지식베이스</TabsTrigger>
              <TabsTrigger value="quality">품질 리그</TabsTrigger>
              <TabsTrigger value="analytics">분석</TabsTrigger>
            </TabsList>
          </div>

          <div className="p-6">
            {/* Overview Tab */}
            <TabsContent value="overview" className="space-y-6">
              {/* System Status Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">총 문서 수</p>
                      <p className="text-2xl font-medium">{totalDocuments.toLocaleString()}</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-primary" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">연결된 소스</p>
                      <p className="text-2xl font-medium">{connectedSources}/{knowledgeConnectors.length}</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                      <Database className="h-5 w-5 text-success" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">오류 발생</p>
                      <p className="text-2xl font-medium text-destructive">{errorSources}</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-destructive/10 flex items-center justify-center">
                      <AlertTriangle className="h-5 w-5 text-destructive" />
                    </div>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">시스템 상태</p>
                      <p className="text-2xl font-medium text-success">정상</p>
                    </div>
                    <div className="w-10 h-10 rounded-lg bg-success/10 flex items-center justify-center">
                      <CheckCircle className="h-5 w-5 text-success" />
                    </div>
                  </div>
                </Card>
              </div>

              {/* Recent Alerts */}
              <Card className="p-4">
                <h3 className="font-medium mb-4 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-warning" />
                  최근 알림
                </h3>
                <div className="space-y-3">
                  <Alert>
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      Finance Drive 커넥터에서 3건의 동기화 오류가 발생했습니다. (14:20)
                    </AlertDescription>
                  </Alert>
                  <Alert>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      HR SharePoint 동기화가 성공적으로 완료되었습니다. (09:15)
                    </AlertDescription>
                  </Alert>
                </div>
              </Card>
            </TabsContent>

            {/* Knowledge Base Tab */}
            <TabsContent value="knowledge" className="space-y-6">
              <Card className="p-4">
                <h3 className="font-medium mb-4 flex items-center gap-2">
                  <Database className="h-4 w-4 text-primary" />
                  지식 소스 상태
                </h3>
                
                <div className="space-y-4">
                  {knowledgeConnectors.map((connector) => {
                    const StatusIcon = getStatusIcon(connector.status);
                    return (
                      <Card key={connector.id} className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <StatusIcon className={cn(
                              "h-5 w-5",
                              getStatusColor(connector.status),
                              connector.status === 'syncing' && "animate-spin"
                            )} />
                            <div>
                              <h4 className="font-medium">{connector.name}</h4>
                              <p className="text-sm text-muted-foreground">
                                {connector.type} • {connector.documentCount.toLocaleString()} 문서
                              </p>
                            </div>
                          </div>
                          
                          <div className="text-right">
                            <Badge 
                              variant={connector.status === 'connected' ? 'default' : 'destructive'}
                              className="mb-1"
                            >
                              {connector.status === 'connected' && '연결됨'}
                              {connector.status === 'error' && '오류'}
                              {connector.status === 'syncing' && '동기화 중'}
                            </Badge>
                            <p className="text-xs text-muted-foreground">
                              최종 동기화: {new Date(connector.lastSync).toLocaleString('ko-KR')}
                            </p>
                            {connector.errorCount > 0 && (
                              <p className="text-xs text-destructive">
                                오류 {connector.errorCount}건
                              </p>
                            )}
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </Card>
            </TabsContent>

            {/* Quality League Tab */}
            <TabsContent value="quality" className="space-y-6">
              <Card className="p-4">
                <h3 className="font-medium mb-4 flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-warning" />
                  부서별 품질 리그 테이블
                </h3>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>순위</TableHead>
                      <TableHead>부서</TableHead>
                      <TableHead>3초 달성률</TableHead>
                      <TableHead>근거율</TableHead>
                      <TableHead>PII 0% 달성률</TableHead>
                      <TableHead>종합 점수</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {qualityLeague.map((metric) => (
                      <TableRow key={metric.department}>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{getRankingIcon(metric.ranking)}</span>
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">{metric.department}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={metric.responseTimeTarget} className="w-16 h-2" />
                            <span className="text-sm">{metric.responseTimeTarget}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={metric.evidenceRate} className="w-16 h-2" />
                            <span className="text-sm">{metric.evidenceRate}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Progress value={metric.piiCompliance} className="w-16 h-2" />
                            <span className="text-sm">{metric.piiCompliance}%</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge 
                            variant={metric.ranking <= 2 ? "default" : "secondary"}
                            className="font-medium"
                          >
                            {metric.overallScore.toFixed(1)}점
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            </TabsContent>

            {/* Analytics Tab */}
            <TabsContent value="analytics" className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Usage Heatmap */}
                <Card className="p-4">
                  <h3 className="font-medium mb-4 flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    시간대별 질문 열지도
                  </h3>
                  <div className="space-y-2">
                    {usageHeatmap.map((data, index) => (
                      <div key={index} className="flex items-center gap-3">
                        <span className="text-sm w-12">{data.hour}</span>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <Progress 
                              value={(data.queries / 150) * 100} 
                              className="flex-1 h-3" 
                            />
                            <span className="text-sm w-8">{data.queries}</span>
                          </div>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {data.department}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Card>

                {/* Top Queries */}
                <Card className="p-4">
                  <h3 className="font-medium mb-4 flex items-center gap-2">
                    <TrendingUp className="h-4 w-4 text-success" />
                    인기 질문 Top 5
                  </h3>
                  <div className="space-y-3">
                    {[
                      { query: '육아휴직 급여 기준', count: 234, change: '+12%' },
                      { query: '재택근무 신청 절차', count: 189, change: '+8%' },
                      { query: '경비처리 시스템', count: 156, change: '+5%' },
                      { query: 'VPN 접속 오류', count: 143, change: '-3%' },
                      { query: '신용평가 권한', count: 98, change: '+15%' }
                    ].map((item, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium">{item.query}</p>
                          <p className="text-xs text-muted-foreground">{item.count}회 검색</p>
                        </div>
                        <Badge 
                          variant={item.change.startsWith('+') ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {item.change}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}