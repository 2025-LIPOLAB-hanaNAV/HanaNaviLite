import React, { useState } from 'react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Icon } from './ui/Icon';
import { cn } from './ui/utils';
import { DocumentSearch } from './DocumentSearch';
import { DocumentManager } from './DocumentManager';

export function DocumentHub() {
  const [activeTab, setActiveTab] = useState<'search' | 'manage'>('search');

  const tabs = [
    { id: 'search' as const, label: '문서 검색', icon: 'search' },
    { id: 'manage' as const, label: '문서 관리', icon: 'folder' },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Tab Header */}
      <div className="border-b bg-elevated">
        <div className="flex items-center px-6 py-3">
          <div className="flex items-center gap-1">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2",
                  activeTab === tab.id && "bg-primary text-primary-foreground"
                )}
              >
                <Icon name={tab.icon} size={16} />
                {tab.label}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'search' && <DocumentSearch />}
        {activeTab === 'manage' && <DocumentManager />}
      </div>
    </div>
  );
}