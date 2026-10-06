// Dialog z geslom kopije (markup je v index.html): nastavi geslo ali vpiši tisto, s katerim je bila
// datoteka shranjena. Geslo je prikazano v celoti, ne s pikami: pika-geslo nihče ne prepiše na papir,
// papir pa je edina pot, ko telefona ni več. Shrani se samo ključ (data/backupKeyStore.js).
import {
  forgetBackupPassword,
  hasBackupPassword,
  setBackupPassword,
  unlockWithPassword,
} from "../data/backupKeyStore.js";
import { generatePassphrase, passphraseProblem } from "../data/passphraseKey.js";

const $ = (id) => document.getElementById(id);

export function setupPasswordDialog({ t, keyStore }) {
  const dialog = $("dialog-password");
  let pending = null; // resolve čakajočega klicatelja
  let envelope = null; // pri odklepanju: datoteka, katere sol da ključ
  let warnedAbout = null; // kratko geslo, na katero je bilo trenerju že povedano

  function status(key, error = false) {
    const line = $("pw-status");
    line.textContent = key ? t(key) : "";
    line.classList.toggle("is-error", error);
  }

  function settle(value) {
    warnedAbout = null;
    const resolve = pending;
    pending = null;
    envelope = null;
    if (dialog.open) dialog.close();
    resolve?.(value);
  }

  function show(unlocking, hasPassword = false) {
    $("pw-title").textContent = t(unlocking ? "pwUnlockTitle" : "pwTitle");
    $("pw-lead").textContent = t(unlocking ? "pwUnlockLead" : "pwLead");
    $("pw-label").textContent = t("pwLabel");
    $("pw-generate").textContent = t("pwNew");
    $("pw-copy").textContent = t("pwCopy");
    $("pw-warning").textContent = t("pwWriteDown");
    $("pw-remember-text").textContent = t("pwRemember");
    $("pw-cancel").textContent = t("pwCancel");
    $("pw-confirm").textContent = t(unlocking ? "pwOpen" : "pwSave");
    // Pri odklepanju generiranje geslo bi zamenjalo geslo, s katerim je bila datoteka zapisana.
    for (const id of ["pw-generate", "pw-copy", "pw-warning"]) $(id).hidden = unlocking;
    // Ponudba se pojavi samo na napravi brez gesla: obstoječega se ne prepisuje.
    $("pw-remember-row").hidden = !unlocking || hasPassword;
    $("pw-value").value = unlocking ? "" : generatePassphrase();
    status("");
    dialog.showModal();
  }

  $("pw-generate").addEventListener("click", () => {
    $("pw-value").value = generatePassphrase();
    status("");
  });
  $("pw-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("pw-value").value);
      status("pwCopied");
    } catch {
      status("pwCopyFailed", true); // geslo je na zaslonu, pot naprej obstaja
    }
  });
  $("pw-cancel").addEventListener("click", () => settle(null));
  // Escape zapre <dialog> brez pritiska na gumb; klicatelj mora vseeno dobiti odgovor.
  dialog.addEventListener("close", () => pending && settle(null));
  $("pw-confirm").addEventListener("click", async () => {
    const typed = $("pw-value").value.trim();
    if (!typed) return status("pwEmpty", true);
    // Pri nastavljanju: prekratko geslo se zavrne, kratko opozori in se sprejme ob ponovnem potrdilu.
    // Pri odklepanju geslo določa datoteka, zato ga ne ocenjujemo.
    if (!envelope) {
      const problem = passphraseProblem(typed);
      if (problem === "short") return status("pwTooShort", true);
      if (problem === "weak" && warnedAbout !== typed) {
        warnedAbout = typed;
        return status("pwWeak", true);
      }
    }
    try {
      if (envelope) {
        // Samo izpelje ključ; shranjevanje je stvar obnovitve, ko je geslo dokazano pravo.
        const unlocked = await unlockWithPassword(envelope, typed, keyStore);
        settle({ ...unlocked, remember: $("pw-remember").checked });
      } else {
        await setBackupPassword(typed, keyStore);
        settle(true);
      }
    } catch {
      status("pwFailed", true);
    }
  });

  return {
    /** Resolves true, ko je geslo shranjeno, false, če je trener zaprl dialog. */
    askToSet({ changing = false } = {}) {
      return new Promise((resolve) => {
        pending = resolve;
        show(false);
        if (changing) status("pwChangeWarning", true);
      });
    },
    /** Resolves ključ iz gesla ali null. Pravilnost gesla pokaže šele dešifriranje. */
    async askToUnlock(file) {
      const hasPassword = await hasBackupPassword(keyStore);
      return new Promise((resolve) => {
        pending = resolve;
        envelope = file;
        show(true, hasPassword);
      });
    },
    forget: () => forgetBackupPassword(keyStore),
  };
}
