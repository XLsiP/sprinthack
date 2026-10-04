// The lookup sites whose search form the helper fills in. If a site changes its page, edit this file.
//
// `last` and `first` are CSS selectors tried in order; if none match, content.js falls back to a text
// box whose label, name or placeholder mentions "last" or "first". `postback` is set only for a site
// with no "I'm not a robot" check, where the helper can also run the search: it is the name the
// site's own Search button submits the form with.
//
// ARDMS and NMTCB are not here because the tracker's link opens straight on the person's result.
const BCT_SITES = [
  {
    name: "ARRT",
    hosts: ["arrt.org"],
    last: ["#lastname", "input[name='lastname']"],
    first: ["#firstname", "input[name='firstname']"],
  },
  {
    name: "NMTCB",
    hosts: ["nmtcb.org"],
    last: ["#last-name", "input[name='LastName']"],
    first: ["#first-name", "input[name='FirstName']"],
  },
  {
    name: "Michigan LARA",
    hosts: ["aca-prod.accela.com"],
    last: ["#ctl00_PlaceHolderMain_refLicenseeSearchForm_txtLastName"],
    first: ["#ctl00_PlaceHolderMain_refLicenseeSearchForm_txtFirstName"],
    postback: "ctl00$PlaceHolderMain$btnNewSearch",
  },
];
