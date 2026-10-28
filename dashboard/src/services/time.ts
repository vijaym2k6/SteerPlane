// The API stores times in UTC but sends them without a timezone suffix
// (e.g. "2026-10-28T16:10:37"). Browsers read such strings as local time,
// which shifts every timestamp by the viewer's UTC offset. Treat them as UTC.
export function parseApiDate(iso: string): Date {
    const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
    return new Date(hasZone ? iso : `${iso}Z`);
}
