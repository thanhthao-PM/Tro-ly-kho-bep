import React from 'react';

interface ToastProps {
  message: string | null;
}

export const Toast: React.FC<ToastProps> = ({ message }) => {
  return (
    <div
      className={`app-toast ${message ? 'show' : ''}`}
      role="status"
      aria-live="polite"
    >
      {message}
    </div>
  );
};
