import { TIME_STEP_MINUTES } from "../../lib/constants";
import { decimalToTime, timeToDecimal } from "../../lib/dateTime";

export function Field({ label, children }) {
  return (
    <div className="input-group">
      <label className="input-label">{label}</label>
      {children}
    </div>
  );
}

export function NumberField({ label, value, onChange, step = "0.5", min = "0" }) {
  return (
    <Field label={label}>
      <input type="number" min={min} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </Field>
  );
}

export function DateField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="date" value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

export function TimeField({ label, value, onChange }) {
  return (
    <Field label={label}>
      <input type="time" step={TIME_STEP_MINUTES * 60} value={value} onChange={(event) => onChange(event.target.value)} />
    </Field>
  );
}

export function TimePreferenceField({ label, value, onChange }) {
  return (
    <TimeField
      label={label}
      value={decimalToTime(value)}
      onChange={(rawValue) => {
        const parsed = timeToDecimal(rawValue);
        if (parsed !== null) {
          onChange(parsed);
        }
      }}
    />
  );
}
