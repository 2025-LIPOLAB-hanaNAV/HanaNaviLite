import React from 'react';
import { cn } from './ui/utils';
import { Icon } from './ui/Icon';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

interface QualityMetrics {
  responseTime: number; // in seconds
  accuracyRate: number; // percentage
  piiDetectionRate: number; // percentage
}

interface QualityWidgetProps {
  metrics: QualityMetrics;
  isLoading?: boolean;
  className?: string;
  variant?: 'horizontal' | 'vertical' | 'compact';
}

export function QualityWidget({ 
  metrics, 
  isLoading, 
  className, 
  variant = 'horizontal' 
}: QualityWidgetProps) {
  const formatTime = (seconds: number) => `${seconds.toFixed(1)}초`;
  const formatPercentage = (value: number) => `${Math.round(value)}%`;

  // Responsive loading states
  if (isLoading) {
    return (
      <div className={cn(
        "animate-pulse",
        {
          // Horizontal layout (desktop)
          "flex items-center gap-4 md:gap-6": variant === 'horizontal',
          // Vertical layout (mobile)
          "flex flex-col gap-3": variant === 'vertical',
          // Compact layout (minimal space)
          "grid grid-cols-3 gap-2": variant === 'compact'
        },
        className
      )}>
        {/* Loading skeletons */}
        {[1, 2, 3].map((i) => (
          <div key={i} className={cn(
            "flex items-center",
            variant === 'vertical' ? "gap-2 justify-between" : "gap-2"
          )}>
            <div className="h-4 w-8 bg-muted rounded animate-pulse" />
            <div className="h-3 w-12 bg-muted/70 rounded animate-pulse" />
          </div>
        ))}
      </div>
    );
  }

  const MetricItem = ({ 
    value, 
    label, 
    tooltip, 
    icon, 
    valueColor 
  }: {
    value: string;
    label: string;
    tooltip: string;
    icon?: React.ReactNode;
    valueColor?: string;
  }) => (
    <Tooltip>
      <TooltipTrigger asChild>
        <div className={cn(
          "group cursor-help transition-all duration-200 hover:scale-105",
          variant === 'vertical' 
            ? "flex items-center justify-between p-3 rounded-xl bg-card/50 hover:bg-card border border-border/50 hover:border-border"
            : "flex items-center gap-2"
        )}>
          <div className={cn(
            "flex items-center gap-2",
            variant === 'vertical' ? "flex-col items-start" : ""
          )}>
            <span 
              className={cn(
                "font-semibold transition-colors",
                variant === 'vertical' ? "text-lg md:text-xl" : "text-base md:text-lg"
              )}
              style={{ 
                color: valueColor || 'var(--foreground)'
              }}
            >
              {value}
            </span>
            {variant !== 'vertical' && (
              <span className={cn(
                "text-muted-foreground font-medium transition-colors group-hover:text-foreground",
                variant === 'compact' ? "text-xs" : "text-sm"
              )}>
                {label}
              </span>
            )}
          </div>
          
          {variant === 'vertical' && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">
                {label}
              </span>
              {icon}
            </div>
          )}
          
          {variant !== 'vertical' && icon}
        </div>
      </TooltipTrigger>
      <TooltipContent side={variant === 'vertical' ? 'left' : 'top'}>
        <p className="font-medium">{tooltip}</p>
      </TooltipContent>
    </Tooltip>
  );

  const Separator = () => (
    <div className={cn(
      "bg-border transition-colors",
      variant === 'vertical' ? "h-px w-full" : "w-px h-4"
    )} />
  );

  return (
    <TooltipProvider delayDuration={300}>
      <div className={cn(
        "transition-all duration-300",
        {
          // Horizontal layout - default for desktop
          "flex items-center gap-3 md:gap-6": variant === 'horizontal',
          // Vertical layout - better for mobile and sidebars
          "flex flex-col gap-3": variant === 'vertical',
          // Compact grid layout - for tight spaces
          "grid grid-cols-3 gap-2": variant === 'compact'
        },
        className
      )}>
        
        {/* Response Time Metric */}
        <MetricItem
          value={formatTime(metrics.responseTime)}
          label="응답시간"
          tooltip="평균 응답 시간"
          valueColor={metrics.responseTime < 2 ? 'var(--success)' : 
                     metrics.responseTime < 5 ? 'var(--warning)' : 'var(--danger)'}
        />

        {variant !== 'compact' && <Separator />}

        {/* Accuracy Rate Metric */}
        <MetricItem
          value={formatPercentage(metrics.accuracyRate)}
          label="정확도"
          tooltip="근거 기반 응답 정확도"
          valueColor={metrics.accuracyRate >= 90 ? 'var(--success)' : 
                     metrics.accuracyRate >= 70 ? 'var(--warning)' : 'var(--danger)'}
        />

        {variant !== 'compact' && <Separator />}

        {/* PII Detection Rate Metric */}
        <MetricItem
          value={formatPercentage(metrics.piiDetectionRate)}
          label="개인정보 탐지"
          tooltip="개인정보 탐지율 (낮을수록 좋음)"
          valueColor={metrics.piiDetectionRate === 0 ? 'var(--success)' : 'var(--warning)'}
          icon={metrics.piiDetectionRate === 0 ? (
            <Icon 
              name="shield-check" 
              size={variant === 'compact' ? 12 : 16} 
              className="text-success" 
              strokeWidth={1.5} 
            />
          ) : (
            <Icon 
              name="shield-alert" 
              size={variant === 'compact' ? 12 : 16} 
              className="text-warning" 
              strokeWidth={1.5} 
            />
          )}
        />
      </div>
    </TooltipProvider>
  );
}