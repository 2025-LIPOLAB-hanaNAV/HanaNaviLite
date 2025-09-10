import React, { useEffect, useState } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface QualityMetrics {
  responseTime: number; // in seconds
  evidenceRate: number; // percentage
  piiRate: number; // percentage
  targetResponseTime: number;
  targetEvidenceRate: number;
}

interface QualityDashboardProps {
  metrics: QualityMetrics;
  isLoading?: boolean;
  className?: string;
}

export function QualityDashboard({ metrics, isLoading = false, className }: QualityDashboardProps) {
  const [animatedMetrics, setAnimatedMetrics] = useState({
    responseTime: 0,
    evidenceRate: 0,
    piiRate: 0,
  });

  useEffect(() => {
    if (!isLoading) {
      // Animate numbers counting up
      const duration = 1000;
      const steps = 30;
      const stepDuration = duration / steps;
      
      let currentStep = 0;
      const interval = setInterval(() => {
        currentStep++;
        const progress = currentStep / steps;
        
        setAnimatedMetrics({
          responseTime: metrics.responseTime * progress,
          evidenceRate: metrics.evidenceRate * progress,
          piiRate: metrics.piiRate * progress,
        });
        
        if (currentStep >= steps) {
          clearInterval(interval);
          setAnimatedMetrics({
            responseTime: metrics.responseTime,
            evidenceRate: metrics.evidenceRate,
            piiRate: metrics.piiRate,
          });
        }
      }, stepDuration);
      
      return () => clearInterval(interval);
    }
  }, [metrics, isLoading]);

  const getTrafficLightColor = (value: number, target: number, isLowerBetter = false) => {
    if (isLoading) return 'bg-muted animate-pulse';
    
    if (isLowerBetter) {
      if (value <= target) return 'bg-success';
      if (value <= target * 1.5) return 'bg-warning animate-pulse';
      return 'bg-danger animate-pulse';
    } else {
      if (value >= target) return 'bg-success';
      if (value >= target * 0.8) return 'bg-warning animate-pulse';
      return 'bg-danger animate-pulse';
    }
  };

  return (
    <Card className={cn("p-4 bg-elevated", className)}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium">품질 계기판</h3>
        <div className="flex gap-1">
          <div 
            className={cn(
              "w-3 h-3 rounded-full",
              getTrafficLightColor(animatedMetrics.responseTime, metrics.targetResponseTime, true)
            )} 
          />
          <div 
            className={cn(
              "w-3 h-3 rounded-full",
              getTrafficLightColor(animatedMetrics.evidenceRate, metrics.targetEvidenceRate)
            )} 
          />
          <div 
            className={cn(
              "w-3 h-3 rounded-full",
              animatedMetrics.piiRate === 0 ? 'bg-success' : 'bg-danger animate-pulse'
            )} 
          />
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10">
            <Icon name="timer" size={20} className="text-primary" />
          </div>
          <div>
            <div className="text-sm text-muted-foreground">응답시간</div>
            <div className="font-medium">
              {isLoading ? (
                <div className="h-5 w-12 bg-muted animate-pulse rounded" />
              ) : (
                <>
                  {animatedMetrics.responseTime.toFixed(1)}초
                  <span className="text-xs text-muted-foreground ml-1">
                    (목표 {metrics.targetResponseTime}초)
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-accent/10">
            <Icon name="book-open" size={20} className="text-accent" />
          </div>
          <div>
            <div className="text-sm text-muted-foreground">근거율</div>
            <div className="font-medium">
              {isLoading ? (
                <div className="h-5 w-12 bg-muted animate-pulse rounded" />
              ) : (
                <>
                  {Math.round(animatedMetrics.evidenceRate)}%
                  <span className="text-xs text-muted-foreground ml-1">
                    (목표 {metrics.targetEvidenceRate}%)
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-success/10">
            <Icon name="shield" size={20} className="text-success" />
          </div>
          <div>
            <div className="text-sm text-muted-foreground">PII 보호</div>
            <div className="font-medium">
              {isLoading ? (
                <div className="h-5 w-12 bg-muted animate-pulse rounded" />
              ) : (
                <>
                  {Math.round(animatedMetrics.piiRate)}%
                  {animatedMetrics.piiRate === 0 && (
                    <Badge variant="outline" className="ml-2 text-xs">
                      안전
                    </Badge>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}