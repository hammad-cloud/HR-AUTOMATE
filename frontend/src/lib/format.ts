const currency = new Intl.NumberFormat("en-PK", {
  style: "currency",
  currency: "PKR",
  maximumFractionDigits: 0,
});

export function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "Restricted";
  return currency.format(Number(value));
}

export function formatDate(iso: string, options: Intl.DateTimeFormatOptions = {}): string {
  return new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...options,
  });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatMonth(iso: string): string {
  return formatDate(iso.length === 7 ? `${iso}-01` : iso, { day: undefined, month: "long" });
}

export function formatDays(value: string | number): string {
  const n = Number(value);
  return `${Number.isInteger(n) ? n : n.toFixed(1)} day${n === 1 ? "" : "s"}`;
}

/** "19–21 Oct 2026", "26 Oct – 3 Nov 2026", "29 Dec 2026 – 2 Jan 2027": repeat only what differs. */
export function dateRange(start: string, end: string): string {
  if (start === end) return formatDate(start);
  const [sy, sm] = start.split("-");
  const [ey, em] = end.split("-");
  if (sy !== ey) return `${formatDate(start)} – ${formatDate(end)}`;
  if (sm !== em) return `${formatDate(start, { year: undefined })} – ${formatDate(end)}`;
  return `${formatDate(start, { month: undefined, year: undefined })}–${formatDate(end)}`;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
