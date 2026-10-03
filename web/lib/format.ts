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
