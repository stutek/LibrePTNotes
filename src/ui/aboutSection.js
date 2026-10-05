import { formatBuildInfo } from "../domain/buildInfo.js";
// Podnožje seznama strank: različica gradnje in povezava do strani o zasebnosti.
import { BUILD_INFO } from "../version.js";
import { el } from "./dom.js";

export function renderAboutSection({ t }) {
  return el(
    "footer",
    { cls: "about" },
    el("a", { cls: "privacy-link", text: t("privacyLink"), attrs: { href: "./privacy.html" } }),
    el("span", { cls: "build-info", text: `${t("versionLabel")}: ${formatBuildInfo(BUILD_INFO)}` }),
  );
}
