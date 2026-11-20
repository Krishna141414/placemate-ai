export function formatDate(value: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }): string {
  if (!value) return "No date";
  const date = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-IN", opts);
}

export function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Whole days from today to a YYYY-MM-DD date (negative when past). */
export function daysUntil(value: string | null | undefined): number | null {
  if (!value) return null;
  const target = new Date(`${value}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export function dueLabel(value: string | null | undefined): string {
  const days = daysUntil(value);
  if (days === null) return "No deadline";
  if (days < 0) return `Closed ${-days} day${days === -1 ? "" : "s"} ago`;
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `${days} days left`;
}

export const pct = (value: number | null | undefined, digits = 0) => (value == null ? "n/a" : `${(value * 100).toFixed(digits)}%`);

export const seconds = (ms: number | null | undefined) => (ms == null ? "n/a" : ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1)} s`);

export const STATUS_LABELS: Record<string, string> = {
  planned: "Planned",
  applied: "Applied",
  online_test: "Online test",
  interview: "Interview",
  offer: "Offer",
  rejected: "Rejected",
};
