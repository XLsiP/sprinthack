// Runs on a lookup page opened from the Credentialing Tracker. It does two things:
//
// 1. Fills in the person's name. The tracker adds it to the link after a "#":
//    ...#bct-last=Smith&bct-first=Pat&bct-id=12 (the part after "#" is never sent to the lookup
//    site). It never touches an "I'm not a robot" check, and presses Search only on a site that
//    has no such check (see `postback` in sites.js); everywhere else the person does.
// 2. Reads the result the page shows (readers.js) and hands it to the tracker, which pre-fills its
//    form for the person to check. Nothing is saved from here.
(() => {
  const site = BCT_SITES.find((s) => s.hosts.some((h) => location.hostname === h || location.hostname.endsWith("." + h)));
  if (!site) return;

  const params = new URLSearchParams(location.hash.replace(/^#/, ""));
  const last = params.get("bct-last");
  const first = params.get("bct-first") || "";
  const id = Number(params.get("bct-id"));

  // Which credential this tab is looking up. Kept for this tab only, so it survives the site moving
  // from its search page to its result page.
  const PENDING = "bct-pending";
  const MAX_AGE = 30 * 60 * 1000;
  if (Number.isInteger(id) && id > 0) {
    try {
      sessionStorage.setItem(PENDING, JSON.stringify({ id, last: last || "", at: Date.now(), opened: false }));
    } catch {}
  }

  function pending() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(PENDING));
      return saved && Date.now() - saved.at < MAX_AGE ? saved : null;
    } catch {
      return null;
    }
  }

  const describe = (el) =>
    [el.name, el.id, el.placeholder, el.getAttribute("aria-label"), el.labels && el.labels[0] && el.labels[0].textContent]
      .filter(Boolean)
      .join(" ");

  function findBox(selectors, pattern) {
    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    const boxes = [...document.querySelectorAll("input[type='text'], input:not([type]), input[type='search']")];
    return boxes.find((el) => el.offsetParent !== null && pattern.test(describe(el))) || null;
  }

  // Set the value the way typing would, so pages built with a framework notice the change.
  function type(el, value) {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set;
    setter.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  let hide;
  function notice(text) {
    let bar = document.getElementById("bct-helper-notice");
    if (!bar) {
      bar = document.createElement("div");
      bar.id = "bct-helper-notice";
      bar.setAttribute("role", "status");
      bar.style.cssText =
        "position:fixed;z-index:2147483647;left:16px;right:16px;bottom:16px;max-width:560px;margin:0 auto;" +
        "padding:12px 16px;border-radius:8px;background:#111827;color:#fff;font:14px/1.4 system-ui,sans-serif;" +
        "box-shadow:0 4px 16px rgba(0,0,0,.3)";
      document.body.appendChild(bar);
    }
    bar.textContent = text;
    clearTimeout(hide);
    hide = setTimeout(() => bar.remove(), 15000);
  }

  function fill() {
    const lastBox = findBox(site.last, /last|surname|family/i);
    if (!lastBox) return false;
    const firstBox = findBox(site.first, /first|given/i);
    type(lastBox, last);
    if (firstBox && first) type(firstBox, first);
    lastBox.scrollIntoView({ block: "center" });
    const who = [first, last].filter(Boolean).join(" ");
    const form = lastBox.form;
    const target = form && form.querySelector("input[name='__EVENTTARGET']");
    if (site.postback && target) {
      notice(`Credentialing Tracker is searching for "${who}".`);
      // Leave the name off the address so going back to this page does not search again.
      history.replaceState(null, "", location.pathname + location.search);
      // Submit the form the way the site's own Search button does.
      target.value = site.postback;
      HTMLFormElement.prototype.submit.call(form);
    } else {
      notice(`Credentialing Tracker filled in "${who}". Tick "I'm not a robot" if asked, then press Search${site.then || ""}.`);
    }
    return true;
  }

  if (last && site.last && !fill()) {
    // Some pages build their form after loading; keep looking for a short while.
    const observer = new MutationObserver(() => {
      if (fill()) observer.disconnect();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
    setTimeout(() => observer.disconnect(), 20000);
  }

  const reader = BCT_READERS[site.name];
  if (!reader || !pending()) return;
  // On a site where the helper runs the search, this page is about to be replaced by the result,
  // and the site may still be showing the outcome of an earlier search. Read the next page instead.
  if (last && site.postback) return;

  let sent = "";
  function read() {
    const lookup = pending();
    if (!lookup) return;
    let found;
    try {
      found = reader(document, location);
    } catch {
      return; // the site changed its page; the person types the result in as before
    }
    if (!found) return;
    if (found.open) {
      // Only once, so pressing Back to the list does not jump forward again.
      if (!lookup.opened) {
        sessionStorage.setItem(PENDING, JSON.stringify({ ...lookup, opened: true }));
        location.assign(found.open);
      }
      return;
    }
    const key = JSON.stringify(found);
    if (key === sent) return;
    sent = key;
    if (found.several) {
      notice(`Credentialing Tracker: several people match. ${site.pick || "Open the right person and the result will be read."}`);
      return;
    }
    // The name stays here: the tracker is only told whether it looked like the right person.
    const letters = (text) => (text || "").toLowerCase().replace(/[^a-z]/g, "");
    const { name, ...shown } = found;
    const mismatch = Boolean(name && lookup.last && !letters(name).includes(letters(lookup.last)));
    const result = { ...shown, mismatch, id: lookup.id, source: site.name, at: Date.now() };
    try {
      chrome.storage.local.set({ bctResult: result }, () => {
        if (mismatch) notice("Credentialing Tracker read this result, but the name here is not the one you were looking up. Check it is the right person.");
        else if (found.none) notice("Credentialing Tracker: no match on this page. Go back to the tracker tab to record it.");
        else if (found.expires) notice(`Credentialing Tracker read this result (expires ${found.expires}). Go back to the tracker tab to check it and save.`);
        else notice("Credentialing Tracker read this result but found no expiry date. Go back to the tracker tab and enter it.");
      });
    } catch {} // the extension was reloaded while this page was open
  }

  read();
  let timer;
  new MutationObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(read, 300);
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "style"] });
})();
