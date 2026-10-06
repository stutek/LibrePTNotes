// Datum ISO in 24-urna ura, ne glede na nastavitve telefona (AGENT_RULES): ročno, brez Intl.
const pad = (n) => String(n).padStart(2, "0");

export function formatDateTime(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

const DATE_TIME = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$/;

/** Vrne obrezan `YYYY-MM-DD HH:MM`, če je to veljaven koledarski datum in 24-urna ura, sicer null. */
export function parseDateTime(text) {
  const clean = typeof text === "string" ? text.trim() : "";
  const m = DATE_TIME.exec(clean);
  if (!m) return null;
  const [year, month, day, hour, minute] = m.slice(1).map(Number);
  const date = new Date(year, month - 1, day, hour, minute);
  const same =
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day &&
    date.getHours() === hour &&
    date.getMinutes() === minute;
  return same ? clean : null;
}
