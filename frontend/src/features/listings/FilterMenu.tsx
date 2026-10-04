import { AnimatePresence, motion } from "motion/react";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { Icon } from "../../components/ui/Icon";
import styles from "./FilterBar.module.css";

interface FilterMenuProps {
  label: string;
  /** Shown on the pill instead of the label when a value is chosen, e.g. "£12.71/h+". */
  summary?: string;
  active: boolean;
  align?: "start" | "end";
  children: ReactNode;
}

/** A pill that opens a small popover of filter options (a bottom sheet on phones). */
export function FilterMenu({ label, summary, active, align = "start", children }: FilterMenuProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    const closeOnOutside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      trigger.current?.focus();
    };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div ref={root} className={styles.menu}>
      <button
        ref={trigger}
        type="button"
        className={`${styles.pill} ${active ? styles.pillActive : ""}`}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((value) => !value)}
      >
        {summary ?? label}
        <Icon name="chevronDown" size={14} className={styles.chevron} />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            id={panelId}
            role="group"
            aria-label={label}
            className={`${styles.popover} ${align === "end" ? styles.alignEnd : ""}`}
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, transition: { duration: 0.12 } }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className={styles.popoverHead}>
              <span>{label}</span>
              <button type="button" className={styles.done} onClick={() => setOpen(false)}>
                Done
              </button>
            </div>
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
