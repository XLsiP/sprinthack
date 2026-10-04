// Fills in the person's name on a lookup page opened from the Credentialing Tracker.
//
// The tracker adds the name to the link after a "#": ...#bct-last=Smith&bct-first=Pat
// (the part after "#" is never sent to the lookup site). This script reads it and types the name
// into the search form. It never touches an "I'm not a robot" check. It presses Search only on a
// site that has no such check (see `postback` in sites.js); everywhere else the person does.
(() => {
  const params = new URLSearchParams(location.hash.replace(/^#/, ""));
  const last = params.get("bct-last");
  const first = params.get("bct-first") || "";
  if (!last) return;

  const site = BCT_SITES.find((s) => s.hosts.some((h) => location.hostname === h || location.hostname.endsWith("." + h)));
  if (!site) return;

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

  function notice(text) {
    const bar = document.createElement("div");
    bar.id = "bct-helper-notice";
    bar.setAttribute("role", "status");
    bar.textContent = text;
    bar.style.cssText =
      "position:fixed;z-index:2147483647;left:16px;right:16px;bottom:16px;max-width:560px;margin:0 auto;" +
      "padding:12px 16px;border-radius:8px;background:#111827;color:#fff;font:14px/1.4 system-ui,sans-serif;" +
      "box-shadow:0 4px 16px rgba(0,0,0,.3)";
    document.body.appendChild(bar);
    setTimeout(() => bar.remove(), 12000);
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
      notice(`Credentialing Tracker filled in "${who}". Tick "I'm not a robot" if asked, then press Search.`);
    }
    return true;
  }

  if (fill()) return;
  // Some pages build their form after loading; keep looking for a short while.
  const observer = new MutationObserver(() => {
    if (fill()) observer.disconnect();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
  setTimeout(() => observer.disconnect(), 20000);
})();
