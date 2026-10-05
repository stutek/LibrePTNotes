// Prikaz žiga gradnje: commit in čas gradnje v UTC kot `YYYY-MM-DD HH:MM` (24-urno, ISO; AGENT_RULES).
export function formatBuildInfo({ commit, builtAt }) {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(builtAt || "");
  return match ? `${commit} · ${match[1]} ${match[2]} UTC` : String(commit);
}
