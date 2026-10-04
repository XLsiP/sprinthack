/** API timestamps are UTC without a zone; show them as local `YYYY-MM-DD HH:MM`. */
export function checkedAt(timestamp: string): string {
  const d = new Date(`${timestamp}Z`);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Alert `sent_at` is the API server's local time without a zone (unlike `checked_at`); show it unconverted. */
export function sentAt(timestamp: string): string {
  return timestamp.slice(0, 16).replace("T", " ");
}

/**
 * A readable name from a manager's email, which is all the API has: `morgan.samplemgr@…` → "Morgan Samplemgr".
 * Short words such as `hr` are uppercased; anything that isn't an email is shown as is.
 */
export function managerName(email: string): string {
  const at = email.indexOf("@");
  if (at <= 0) return email;
  return email
    .slice(0, at)
    .split(/[._-]+/)
    .filter(Boolean)
    .map((w) => {
      if (w.length <= 2) return w.toUpperCase();
      const word = w[0].toUpperCase() + w.slice(1).toLowerCase();
      return word.startsWith("Mc") && word.length > 2 ? `Mc${word[2].toUpperCase()}${word.slice(3)}` : word;
    })
    .join(" ");
}
