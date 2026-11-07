import React from 'react';

export type TagTone = 'ok' | 'warn' | 'bad' | 'neutral';

interface StatusTagProps {
  tone: TagTone;
  children: React.ReactNode;
  className?: string;
}

export const StatusTag: React.FC<StatusTagProps> = ({ tone, children, className = '' }) => {
  const toneClasses: Record<TagTone, string> = {
    ok: 'tag-ok',
    warn: 'tag-warn',
    bad: 'tag-bad',
    neutral: 'tag-neutral',
  };

  return (
    <span className={`status-tag ${toneClasses[tone]} ${className}`}>
      {children}
    </span>
  );
};
