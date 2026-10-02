import { useVisaRules } from "../../api/queries";
import type { VisaSettings } from "../../api/types";
import { useSyncedState } from "../../hooks/useSyncedState";
import styles from "./Tracker.module.css";

interface VisaSettingsBarProps {
  settings: VisaSettings;
  onChange: (settings: VisaSettings) => void;
}

/** Choose the visa whose hour limit applies, or set a personal limit. */
export function VisaSettingsBar({ settings, onChange }: VisaSettingsBarProps) {
  const { data: rules } = useVisaRules();
  const [override, setOverride] = useSyncedState(settings.capOverride?.toString() ?? "");

  const commitOverride = () => {
    const value = override.trim() === "" ? null : Number(override);
    const valid = value === null || (Number.isFinite(value) && value >= 0 && value <= 168);
    if (valid && value !== settings.capOverride) onChange({ ...settings, capOverride: value });
    if (!valid) setOverride(settings.capOverride?.toString() ?? "");
  };

  const selected = `${settings.country}|${settings.visaType}`;

  return (
    <div className={styles.settings}>
      <label className={styles.field}>
        <span>Your visa</span>
        <select
          value={selected}
          onChange={(event) => {
            const [country = "UK", visaType = "student"] = event.target.value.split("|");
            onChange({ ...settings, country, visaType });
          }}
        >
          {rules?.rules.map((rule) => (
            <option
              key={`${rule.country}|${rule.visa_type}`}
              value={`${rule.country}|${rule.visa_type}`}
            >
              {rule.label}
            </option>
          )) ?? <option value={selected}>UK Student visa</option>}
        </select>
      </label>
      <label className={styles.field}>
        <span>Personal limit (hours/week)</span>
        <input
          type="number"
          inputMode="decimal"
          min={0}
          max={168}
          step={0.5}
          placeholder="Use visa limit"
          value={override}
          onChange={(event) => setOverride(event.target.value)}
          onBlur={commitOverride}
          onKeyDown={(event) => event.key === "Enter" && commitOverride()}
        />
      </label>
    </div>
  );
}
