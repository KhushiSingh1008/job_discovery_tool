import { Link, NavLink, Outlet, ScrollRestoration } from "react-router";

import { useApplications, useHoursSummary } from "../../api/queries";
import { useVisaSettings } from "../../hooks/useVisaSettings";
import { formatHours } from "../../lib/format";
import { Icon } from "../ui/Icon";
import styles from "./AppLayout.module.css";

const NAV_ITEMS = [
  { to: "/", label: "Find jobs", end: true },
  { to: "/tracker", label: "My applications", end: false },
  { to: "/match", label: "Resume tools", end: false },
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

function SavedLink() {
  const { data } = useApplications();
  const saved = data?.filter((application) => application.status === "saved").length ?? 0;
  return (
    <Link to="/tracker" className={styles.saved} aria-label={`Saved jobs: ${saved}`}>
      <Icon name="bookmark" />
      {saved > 0 && (
        <span className={styles.savedCount} aria-hidden="true">
          {saved}
        </span>
      )}
    </Link>
  );
}

export function Logo() {
  return (
    <span className={styles.mark} aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
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
            <Logo />
            <span className={styles.wordmark}>
              Grad<span>Guide</span>
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
          <div className={styles.tools}>
            <HoursIndicator />
            <SavedLink />
          </div>
        </div>
      </header>

      <main id="main" className={styles.main}>
        <Outlet />
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span className={styles.footerBrand}>
            <Logo /> GradGuide Jobs
          </span>
          <p>
            Listings are scraped from university, student and employer job boards. Work-hour limits
            are a guide: always check your visa conditions on{" "}
            <a href="https://www.gov.uk/student-visa/work" target="_blank" rel="noreferrer">
              gov.uk
            </a>
            .
          </p>
        </div>
      </footer>
      <ScrollRestoration />
    </div>
  );
}
