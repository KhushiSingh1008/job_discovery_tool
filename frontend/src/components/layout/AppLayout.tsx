import { Link, NavLink, Outlet, ScrollRestoration } from "react-router";

import { useHoursSummary } from "../../api/queries";
import { useVisaSettings } from "../../hooks/useVisaSettings";
import { formatHours } from "../../lib/format";
import styles from "./AppLayout.module.css";

const NAV_ITEMS = [
  { to: "/", label: "Jobs", end: true },
  { to: "/tracker", label: "Tracker", end: false },
  { to: "/match", label: "Resume match", end: false },
];

/** Always-visible reminder of the visa hour limit, linking to the tracker. */
function HoursIndicator() {
  const [settings] = useVisaSettings();
  const { data } = useHoursSummary(settings);
  if (!data) return null;
  const label =
    data.cap_hours === null
      ? `${formatHours(data.committed_hours)} · no limit`
      : `${formatHours(data.committed_hours)} of ${formatHours(data.cap_hours)}`;
  return (
    <Link
      to="/tracker"
      className={`${styles.hours} ${styles[data.status]}`}
      title={`Weekly work hours: ${data.message}`}
    >
      <span className={styles.hoursDot} aria-hidden="true" />
      <span className={styles.hoursLabel}>{label}</span>
      <span className="visually-hidden"> weekly work hours</span>
    </Link>
  );
}

export function AppLayout() {
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" className={styles.brand} aria-label="GradGuide Jobs home">
            <span className={styles.mark} aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span className={styles.wordmark}>
              GradGuide <em>Jobs</em>
            </span>
          </Link>
          <nav className={styles.nav} aria-label="Main">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <HoursIndicator />
        </div>
      </header>

      <main id="main" className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <p>
          Listings are scraped from university, student and employer job boards and refreshed daily.
          Work-hour limits are a guide: always check your visa conditions on{" "}
          <a href="https://www.gov.uk/student-visa/work" target="_blank" rel="noreferrer">
            gov.uk
          </a>
          .
        </p>
      </footer>
      <ScrollRestoration />
    </div>
  );
}
