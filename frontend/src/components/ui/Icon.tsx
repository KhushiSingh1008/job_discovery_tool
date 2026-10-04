/** A small set of stroke icons drawn on a 20×20 grid, so they share weight and alignment. */
const PATHS = {
  search: (
    <>
      <circle cx="9" cy="9" r="5.5" />
      <path d="m13.2 13.2 3.6 3.6" />
    </>
  ),
  pin: (
    <>
      <path d="M10 17.5s5.5-5 5.5-9.2a5.5 5.5 0 1 0-11 0c0 4.2 5.5 9.2 5.5 9.2Z" />
      <circle cx="10" cy="8.3" r="2" />
    </>
  ),
  briefcase: (
    <>
      <rect x="2.75" y="6" width="14.5" height="10.5" rx="2" />
      <path d="M7 6V4.75A1.75 1.75 0 0 1 8.75 3h2.5A1.75 1.75 0 0 1 13 4.75V6M2.75 10.5h14.5" />
    </>
  ),
  clock: (
    <>
      <circle cx="10" cy="10" r="7.25" />
      <path d="M10 6v4.25l2.75 1.75" />
    </>
  ),
  bookmark: <path d="M5.5 3.25h9v14l-4.5-3.25-4.5 3.25z" />,
  share: (
    <>
      <circle cx="14.5" cy="4.75" r="2" />
      <circle cx="5.5" cy="10" r="2" />
      <circle cx="14.5" cy="15.25" r="2" />
      <path d="m7.3 9 5.4-3.2M7.3 11l5.4 3.2" />
    </>
  ),
  sparkle: (
    <path d="M10 2.75 11.6 8.4l5.65 1.6-5.65 1.6L10 17.25 8.4 11.6 2.75 10 8.4 8.4zM15.5 2.5v3M14 4h3" />
  ),
  arrowRight: <path d="M4 10h12m-4.5-4.5L16 10l-4.5 4.5" />,
  external: <path d="M8.5 4.5h-4v11h11v-4M11.5 3.5h5v5M16.5 3.5 9 11" />,
  close: <path d="m5 5 10 10M15 5 5 15" />,
  plus: <path d="M10 4.5v11M4.5 10h11" />,
  upload: (
    <path d="M10 13V3.5M6.25 7.25 10 3.5l3.75 3.75M3.5 12.5v2.75c0 .7.55 1.25 1.25 1.25h10.5c.7 0 1.25-.55 1.25-1.25V12.5" />
  ),
  file: (
    <>
      <path d="M11.5 2.75H6a1.75 1.75 0 0 0-1.75 1.75v11A1.75 1.75 0 0 0 6 17.25h8a1.75 1.75 0 0 0 1.75-1.75V7z" />
      <path d="M11.5 2.75V7h4.25M7.5 11h5M7.5 14h3.5" />
    </>
  ),
  check: <path d="m4.5 10.5 3.5 3.5 7.5-8" />,
  chevronDown: <path d="m5.5 8 4.5 4.5L14.5 8" />,
  filter: <path d="M3 5h14M6 10h8M8.5 15h3" />,
  shield: (
    <>
      <path d="M10 2.75 4 5v4.6c0 3.6 2.5 6.4 6 7.65 3.5-1.25 6-4.05 6-7.65V5z" />
      <path d="m7.4 10 1.9 1.9 3.4-3.6" />
    </>
  ),
  pound: <path d="M13.5 5.5A3 3 0 0 0 7.75 7v3.5c0 2.5-.75 4-2.25 5h9M5.5 10.5h6" />,
} as const;

export type IconName = keyof typeof PATHS;

interface IconProps {
  name: IconName;
  size?: number;
  className?: string;
  filled?: boolean;
}

export function Icon({ name, size = 18, className, filled = false }: IconProps) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
