import React from 'react';
import { Button } from './ui/button';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';

interface FigmaInspiredButtonProps {
  children: React.ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  icon?: string;
}

export function FigmaInspiredButton({
  children,
  href,
  onClick,
  variant = 'primary',
  size = 'md',
  className,
  icon = 'arrow-right'
}: FigmaInspiredButtonProps) {
  const sizeClasses = {
    sm: 'px-6 py-3 text-base',
    md: 'px-8 py-4 text-lg',
    lg: 'px-12 py-6 text-xl'
  };

  const buttonElement = (
    <Button
      onClick={onClick}
      className={cn(
        'button-primary text-white font-bold border-0 transition-all duration-300 hover:scale-105',
        sizeClasses[size],
        variant === 'secondary' && 'bg-white text-primary hover:bg-gray-50',
        className
      )}
    >
      <span className="flex items-center gap-3">
        {children}
        <Icon name={icon as any} size={size === 'lg' ? 20 : size === 'md' ? 18 : 16} />
      </span>
    </Button>
  );

  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className="inline-block">
        {buttonElement}
      </a>
    );
  }

  return buttonElement;
}