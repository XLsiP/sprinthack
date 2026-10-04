// Reads the result a lookup site is showing, so the tracker can pre-fill its form.
//
// One reader per site in sites.js, keyed by the site's name. Each takes the page (`document` and
// its `location`) and returns:
//   null                 nothing to read yet
//   { open: url }        one person matched; go to their page
//   { several: true }    several people matched; the person at the keyboard picks one
//   { none: true }       the site says nobody matched
//   { name, expires, number, summary, hint? }   what the page shows. `expires` is YYYY-MM-DD or
//                        null; `number` is null where the site shows none (ARRT, ARDMS, NMTCB).
//                        `name` is only compared with the person looked up, then dropped.
// Nothing read here is saved by itself: the tracker shows it for the person to check first.
// If a site changes its page, this is the file to edit.
const BCT_READERS = (() => {
  const MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"];
  // Michigan's pages put invisible zero-width characters between letters; drop them.
  const clean = (text) => (text || "").replace(/[\u200b-\u200d\ufeff]/g, "").replace(/\s+/g, " ").trim();
  const pad = (n) => String(n).padStart(2, "0");
  const iso = (year, month, day) => (month >= 1 && month <= 12 ? `${year}-${pad(month)}-${pad(day)}` : null);
  const earliest = (dates) => dates.filter(Boolean).sort()[0] || null;

  /** 07/31/2027 */
  function usDate(text) {
    const m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(clean(text));
    return m ? iso(m[3], Number(m[1]), Number(m[2])) : null;
  }

  /** December 31 2026 */
  function longDate(text) {
    const m = /^([A-Za-z]+) (\d{1,2}),? (\d{4})$/.exec(clean(text));
    return m ? iso(m[3], MONTHS.indexOf(m[1].toLowerCase()) + 1, Number(m[2])) : null;
  }

  /** 03/2027, taken as the last day of that month. */
  function monthEnd(text) {
    const m = /^(\d{1,2})\/(\d{4})$/.exec(clean(text));
    return m ? iso(m[2], Number(m[1]), new Date(Number(m[2]), Number(m[1]), 0).getDate()) : null;
  }

  // ARRT: the "View Details" box. It gives the credentials and a "Valid Thru" month, but no ID number.
  function arrt(doc) {
    const modal = doc.querySelector("#divDetailsModal");
    const body = doc.querySelector("#divDetailsModalContent .modal-body");
    if (!body || (modal && !modal.classList.contains("in") && !modal.classList.contains("show"))) return null;
    const rows = {};
    for (const tr of body.querySelectorAll("table.table-condensed > tbody > tr")) {
      const th = tr.querySelector(":scope > th");
      const td = tr.querySelector(":scope > td");
      if (th && td) rows[clean(th.textContent)] = clean(td.textContent);
    }
    const credentials = rows["Credentials"];
    const validThru = rows["Valid Thru"];
    // A sanction or a lapsed registration is shown as a heading in the box.
    const headings = [...body.querySelectorAll("h3")].filter((h) => h.offsetParent !== null).map((h) => clean(h.textContent));
    if (!credentials && !validThru && !headings.length) return null;
    const expires = monthEnd(validThru);
    return {
      name: rows["Name"],
      expires,
      number: null,
      summary: [credentials, validThru && `valid thru ${validThru}`, ...headings].filter(Boolean).join(", "),
      hint: expires ? "ARRT shows only the month and year, so the last day of that month is filled in." : undefined,
    };
  }

  // ARDMS (Inteleos directory): one panel per person, one table row per credential.
  function ardms(doc) {
    const listing = doc.querySelector("#status-verif-listing");
    if (!listing) return null;
    const people = listing.querySelectorAll(".panel-item");
    if (people.length > 1) return { several: true };
    if (!people.length) return /no (results|records|matches)/i.test(listing.textContent) ? { none: true } : null;
    const table = people[0].querySelector("table.sv-listing-table");
    if (!table) return null;
    const heads = [...table.querySelectorAll("thead th")].map((th) => clean(th.textContent).replace(/:$/, "").toLowerCase());
    const rows = [...table.querySelectorAll("tbody tr")].map((tr) => {
      const cells = [...tr.querySelectorAll("td")].map((td) => clean(td.textContent));
      const cell = (name) => cells[heads.indexOf(name)] || "";
      return { credential: cell("credential"), specialty: cell("specialty"), until: cell("valid until"), status: cell("status") };
    });
    if (!rows.length) return null;
    const active = rows.filter((r) => /^active$/i.test(r.status));
    const heading = people[0].querySelector("h6");
    return {
      name: heading && heading.firstChild ? clean(heading.firstChild.textContent) : "",
      // With several credentials, the one that runs out first is the date to track.
      expires: earliest((active.length ? active : rows).map((r) => longDate(r.until))),
      number: null,
      summary: rows
        .map((r) => `${r.credential}${r.specialty ? ` (${r.specialty})` : ""}: ${r.status || "no status"}${r.until ? ` until ${r.until}` : ""}`)
        .join("; "),
    };
  }

  // NMTCB: a list of matching people, then one page per person.
  function nmtcb(doc, where) {
    const card = doc.querySelector(".details-card");
    if (card) {
      const blocks = {};
      for (const block of card.querySelectorAll(".details-block")) {
        const title = block.querySelector("h6");
        const value = block.querySelector(".details-value");
        if (title && value) blocks[clean(title.textContent).toLowerCase()] = value;
      }
      const through = blocks["certified through"];
      const dates = through
        ? [...through.querySelectorAll("time")].map((t) => (/^\d{4}-\d{2}-\d{2}$/.test(t.dateTime) ? t.dateTime : usDate(t.textContent)))
        : [];
      const status = clean((blocks["current status"] || blocks["certifications held"] || {}).textContent);
      return {
        name: clean((blocks["name"] || {}).textContent),
        expires: earliest(dates),
        number: null,
        summary: [status, through && `certified through ${clean(through.textContent)}`].filter(Boolean).join(", "),
      };
    }
    if (!/^\/verification\/results/i.test(where.pathname)) return null;
    const section = doc.querySelector("#main-section");
    if (!section) return null;
    const people = [...section.querySelectorAll("a[href]")].filter((a) => /^\/verification\/\d+$/.test(a.pathname));
    if (people.length === 1) return { open: people[0].href };
    return people.length ? { several: true } : { none: true };
  }

  // Michigan license lookup: a results table, or a single license page when only one matches.
  function michigan(doc, where) {
    const copy = doc.body.cloneNode(true);
    copy.querySelectorAll("script, style").forEach((el) => el.remove());
    const text = clean(copy.textContent);
    if (/LicenseeDetail/i.test(where.pathname)) {
      const field = (label, stop) => clean((new RegExp(`${label}:\\s*(.*?)\\s*${stop}:`).exec(text) || [])[1]);
      const number = field("License Number", "Name");
      if (!number) return null;
      const status = field("License Status", "County");
      const until = field("License Expiration Date", "License Status");
      return {
        name: field("Name", "License Issue Date"),
        expires: usDate(until),
        number,
        summary: [field("License Type", "License Number"), status, until && `expires ${until}`].filter(Boolean).join(", "),
      };
    }
    const rows = [...doc.querySelectorAll("tr.ACA_TabRow_Odd, tr.ACA_TabRow_Even")]
      .map((tr) => [...tr.querySelectorAll(":scope > td")].map((td) => clean(td.textContent)))
      .filter((cells) => cells.length >= 9);
    if (rows.length > 1) return { several: true };
    if (rows.length === 1) {
      const [type, license, a, b, c, , , status, until] = rows[0];
      return {
        name: [a, b, c].filter(Boolean).join(" "),
        expires: usDate(until),
        number: license || null,
        summary: [type, status, until && `expires ${until}`].filter(Boolean).join(", "),
      };
    }
    return /Your search returned no results/i.test(text) ? { none: true } : null;
  }

  return { ARRT: arrt, ARDMS: ardms, NMTCB: nmtcb, "Michigan LARA": michigan };
})();
