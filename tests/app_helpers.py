"""Pomočniki brskalniških testov: semenjenje IndexedDB, branje stanja, dotikalna kretnja (CDP)."""

import json
import time

from playwright.sync_api import Error as PlaywrightError

SEED_JS = """
async ({clients, tabs}) => {
  const { openDb, idbBackend } = await import("./data/idbBackend.js");
  const db = await openDb();
  const backend = idbBackend(db);
  const ids = {};
  let created = 1;
  for (const client of clients) {
    const id = client.id || "c-" + client.name;
    ids[client.name] = id;
    await backend.put("clients", { id, name: client.name, created: created++ });
    let n = 0;
    const noteIds = [];
    for (const note of client.notes || []) {
      const noteId = note.id || id + "-n" + n++;
      noteIds.push(noteId);
      await backend.put("notes", { id: noteId, clientId: id, date: note.date, created: created++, text: note.text, ...(note.title ? { title: note.title } : {}) });
    }
    if (client.current !== undefined) await backend.put("meta", { key: "current:" + id, noteId: noteIds[client.current] });
  }
  if (tabs) {
    const open = tabs.open.map((name) => ids[name]);
    await backend.put("meta", { key: "tabs", open, active: tabs.active ? ids[tabs.active] : null });
  }
  db.close();
  return ids;
}
"""

READ_JS = """
async () => {
  const { openDb, idbBackend } = await import("./data/idbBackend.js");
  const db = await openDb();
  const backend = idbBackend(db);
  const out = {
    clients: await backend.getAll("clients"),
    notes: await backend.getAll("notes"),
    meta: (await backend.getAll("meta")).filter((m) => m.key !== "backupKey"),
  };
  db.close();
  return out;
}
"""


def open_app(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#view .page, #view .note-page, #view .note-empty")


def seed(page, base_url, clients, tabs=None):
    """Zapiše stranke in zapise v IndexedDB aplikacije in naloži stran znova. Vrne {ime: id}."""
    page.goto(base_url)
    ids = page.evaluate(SEED_JS, {"clients": clients, "tabs": tabs})
    open_app(page, base_url)
    return ids


def client_menu(page, name, item):
    """Odpre meni stranke (⋯ v njeni vrstici) in tapne postavko (»Preimenuj«, »Izvozi zapise (besedilo)«,
    »Izbriši stranko«)."""
    page.get_by_role("button", name=f"Več za stranko: {name}", exact=True).click()
    page.locator("dialog.sheet[open] .sheet-item", has_text=item).click()


def data_menu(page, item):
    """Odpre meni »Več o podatkih« ob varnostni kopiji in tapne postavko."""
    page.get_by_role("button", name="Več o podatkih").click()
    page.locator("dialog.sheet[open] .sheet-item", has_text=item).click()


def note_menu(page, item):
    """Odpre meni zapisa (⋯ v glavi zapisa) in tapne postavko (»Izbriši zapis«)."""
    page.get_by_role("button", name="Več za zapis").click()
    page.locator("dialog.sheet[open] .sheet-item", has_text=item).click()


def open_client(page, name):
    """Dotik vrstice stranke odpre njene beležke."""
    page.get_by_role(
        "button", name=f"Odpri beležke stranke: {name}", exact=True
    ).click()


def wait_for_service_worker(page):
    """Počaka, da service worker nadzira stran (predpomnilnik je poln, ker install uspe šele po tem).
    Brez omejitve bi zgrešen dogodek obesil test; z omejitvijo je neuspeh viden in poimenovan."""
    page.evaluate(
        """async () => {
          const limit = (ms, what) =>
            new Promise((_, no) => setTimeout(() => no(new Error(what + " ni v " + ms + " ms")), ms));
          await Promise.race([navigator.serviceWorker.ready, limit(20000, "service worker ready")]);
          if (!navigator.serviceWorker.controller) {
            await Promise.race([
              new Promise((r) => navigator.serviceWorker.addEventListener("controllerchange", r, { once: true })),
              limit(20000, "controllerchange"),
            ]);
          }
        }"""
    )


def eventually(page, probe, timeout=10):
    """Ponavlja `probe()`, dokler ne vrne resnične vrednosti (napake med ponovnim nalaganjem strani se
    preskočijo). Zamenja wait_for_function za asinhrone preverbe, ki jih ta ne počaka."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = probe()
        except PlaywrightError:
            value = None
        if value:
            return value
        page.wait_for_timeout(50)
    raise AssertionError("stanje ni doseženo v {} s".format(timeout))


def worker_state(page):
    return page.evaluate(
        """async () => {
          const r = await navigator.serviceWorker.getRegistration();
          return { installing: Boolean(r.installing), waiting: Boolean(r.waiting) };
        }"""
    )


def cache_names(page):
    return sorted(page.evaluate("() => caches.keys()"))


def db_state(page):
    return page.evaluate(READ_JS)


def notes_of(page, client_name):
    state = db_state(page)
    client = next(c for c in state["clients"] if c["name"] == client_name)
    notes = [n for n in state["notes"] if n["clientId"] == client["id"]]
    return sorted(notes, key=lambda n: (n["date"], n["created"]))


WAIT_SAVED_JS = """
async ([name, texts, timeoutMs]) => {
  const { openDb, idbBackend } = await import("./data/idbBackend.js");
  const read = async () => {
    const db = await openDb();
    const backend = idbBackend(db);
    const client = (await backend.getAll("clients")).find((c) => c.name === name);
    const notes = (await backend.getAll("notes")).filter((n) => n.clientId === client?.id);
    db.close();
    notes.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.created - b.created));
    return notes.map((n) => n.text);
  };
  const want = JSON.stringify(texts);
  const deadline = Date.now() + timeoutMs;
  let have = await read();
  while (JSON.stringify(have) !== want && Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, 25));
    have = await read();
  }
  return have;
}
"""


def wait_for_saved(page, client_name, texts, timeout_ms=10000):
    """Počaka (v strani, brez fiksnega spanja), da so zapisi stranke po vrstnem redu v IndexedDB."""
    have = page.evaluate(WAIT_SAVED_JS, [client_name, texts, timeout_ms])
    assert have == texts, f"zapisi v bazi: {have!r}"


def active_tab(page):
    """Ime aktivnega zavihka (»Stranke« za seznam)."""
    return page.locator(".tab.is-active .tab-name").inner_text()


def wait_for_note(page, text):
    """Počaka, da je v urejevalniku trenutnega zapisa to besedilo."""
    page.wait_for_function(
        "(t) => document.querySelector('.plan-peek-blanket .md-input')?.value === t",
        arg=text,
    )


class Touch:
    """Dotikalna kretnja prek CDP Input.dispatchTouchEvent; stanje čaka na razrede, ne na čas."""

    def __init__(self, page):
        self.page = page
        self.cdp = page.context.new_cdp_session(page)
        self.x = self.y = 0

    def _send(self, kind, points):
        self.cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})

    def down(self, x, y):
        self.x, self.y = x, y
        self._send("touchStart", [{"x": x, "y": y}])

    def hold(self, x, y):
        """Pritisk, nato čakanje, da se zapis zoži (is-held)."""
        self.down(x, y)
        self.page.wait_for_selector(".plan-peek-blanket.is-held")

    def move_to(self, x, y, steps=6):
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            px = x0 + (x - x0) * i / steps
            py = y0 + (y - y0) * i / steps
            self._send("touchMove", [{"x": px, "y": py}])
        self.x, self.y = x, y

    def up(self):
        self._send("touchEnd", [])

    def pull(self, dx):
        """Poteg vstran od trenutnega položaja."""
        self.move_to(self.x + dx, self.y)

    def raise_(self, dy):
        """Poteg navzgor (drugi zamah kretnje L)."""
        self.move_to(self.x, self.y - dy)


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=1)
