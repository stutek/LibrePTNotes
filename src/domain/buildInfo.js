// src/domain/buildInfo.js — prikaz žiga gradnje.
import { formatDateTime } from "./dates.js";

// Commit in čas gradnje v KRAJEVNEM času naprave kot `YYYY-MM-DD HH:MM` (24-urno, ISO; AGENT_RULES).
// Žig je v UTC (`2026-10-06T19:01Z`); trener pozna svoj čas, ne UTC.
export function formatBuildInfo({ commit, builtAt }) {
  const built = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(builtAt || "") ? new Date(builtAt) : null;
  return built && !Number.isNaN(built.getTime())
    ? `${commit} · ${formatDateTime(built)}`
    : String(commit);
}
