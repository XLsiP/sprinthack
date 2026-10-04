// Where each lookup site's name boxes are. If a site changes its page, this is the only file to edit.
// `last` and `first` are CSS selectors tried in order; if none match, content.js falls back to finding
// a text box whose label, name or placeholder mentions "last" or "first".
const BCT_SITES = [
  { name: "ARRT", hosts: ["arrt.org"], last: ["#lastname", "input[name='lastname']"], first: ["#firstname", "input[name='firstname']"] },
  { name: "NMTCB", hosts: ["nmtcb.org"], last: ["#last-name", "input[name='LastName']"], first: ["#first-name", "input[name='FirstName']"] },
  // ARDMS's directory now lives on inteleos.org. Its form has not been inspected, so this relies on the fallback.
  { name: "ARDMS", hosts: ["ardms.org", "inteleos.org"], last: [], first: [] },
];
