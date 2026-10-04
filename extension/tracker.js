// Runs on the Credentialing Tracker itself. Passes the result read on a lookup page (content.js)
// to the tracker's Verify form, which shows it pre-filled for the person to check and save.
// The result holds the tracker's row number, the dates and the credential text; never a name.
(() => {
  function send(result) {
    if (result) window.postMessage({ from: "bct-helper", type: "result", result }, location.origin);
  }

  function latest() {
    try {
      chrome.storage.local.get("bctResult", (items) => send(items && items.bctResult));
    } catch {} // the extension was reloaded while this page was open; reload the page
  }

  // The form asks when it opens, and the helper also tells it as soon as a new result is read.
  window.addEventListener("message", (event) => {
    if (event.source !== window || event.origin !== location.origin) return;
    if (event.data && event.data.from === "bct-page" && event.data.type === "request") latest();
  });
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === "local" && changes.bctResult) send(changes.bctResult.newValue);
    });
  } catch {}
})();
