// Datum ISO in 24-urna ura, ne glede na nastavitve telefona (AGENT_RULES): ročno, brez Intl.
const pad = (n) => String(n).padStart(2, "0");

export function formatDateTime(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
