import React from 'react';

export type IconName =
  | 'box'
  | 'book'
  | 'spark'
  | 'chart'
  | 'scan'
  | 'bell'
  | 'pen'
  | 'x'
  | 'arrow'
  | 'back'
  | 'send'
  | 'leaf'
  | 'plus'
  | 'trash'
  | 'up';

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
}

export const Icon: React.FC<IconProps> = ({ name, size = 20, className = '' }) => {
  const paths: Record<IconName, React.ReactNode> = {
    box: (
      <>
        <path d="M3 7l9-4 9 4v10l-9 4-9-4z" />
        <path d="M3 7l9 4 9-4" />
        <path d="M12 11v10" />
      </>
    ),
    book: (
      <>
        <path d="M5 4h11a3 3 0 013 3v13H8a3 3 0 01-3-3z" />
        <path d="M9 8h6" />
      </>
    ),
    spark: (
      <>
        <path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" />
        <path d="M19 17v4" />
        <path d="M17 19h4" />
      </>
    ),
    chart: (
      <>
        <path d="M5 20V10" />
        <path d="M12 20V4" />
        <path d="M19 20v-7" />
      </>
    ),
    scan: (
      <>
        <path d="M4 8V5a1 1 0 011-1h3" />
        <path d="M16 4h3a1 1 0 011 1v3" />
        <path d="M20 16v3a1 1 0 01-1 1h-3" />
        <path d="M8 20H5a1 1 0 01-1-1v-3" />
        <path d="M8 12h8" />
      </>
    ),
    bell: (
      <>
        <path d="M6 16v-5a6 6 0 0112 0v5l2 2H4z" />
        <path d="M10 21h4" />
      </>
    ),
    pen: (
      <>
        <path d="M4 20h4L19 9l-4-4L4 16z" />
        <path d="M13 7l4 4" />
      </>
    ),
    x: (
      <>
        <path d="M6 6l12 12" />
        <path d="M18 6L6 18" />
      </>
    ),
    arrow: (
      <>
        <path d="M5 12h14" />
        <path d="M13 6l6 6-6 6" />
      </>
    ),
    back: (
      <>
        <path d="M19 12H5" />
        <path d="M11 6l-6 6 6 6" />
      </>
    ),
    send: <path d="M4 12l16-8-6 16-3-7z" />,
    leaf: (
      <>
        <path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14z" />
        <path d="M5 19l8-8" />
      </>
    ),
    plus: (
      <>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </>
    ),
    trash: (
      <>
        <path d="M4 7h16" />
        <path d="M9 7V4h6v3" />
        <path d="M6 7l1 13h10l1-13" />
      </>
    ),
    up: (
      <>
        <path d="M12 16V4" />
        <path d="M7 9l5-5 5 5" />
        <path d="M5 20h14" />
      </>
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  );
};
