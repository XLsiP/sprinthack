// The lookup sites the helper works on. If a site changes its search form, edit this file; what is
// read off each site's result page is in readers.js, under the same `name`.
//
// `last` and `first` are CSS selectors tried in order; if none match, content.js falls back to a text
// box whose label, name or placeholder mentions "last" or "first". A site with no `last` needs no
// filling in, because the tracker's link opens straight on the person's result. `postback` is set
// only for a site with no "I'm not a robot" check, where the helper can also run the search: it is
// the name the site's own Search button submits the form with. `then` and `pick` are added to the
// helper's messages where a site needs one more click from the person.
const BCT_SITES = [
  {
    name: "ARRT",
    hosts: ["arrt.org"],
    last: ["#lastname", "input[name='lastname']"],
    first: ["#firstname", "input[name='firstname']"],
    then: ", then View Details on the right person",
    pick: "Press View Details on the right person and the result will be read.",
  },
  {
    name: "ARDMS",
    hosts: ["myportal.inteleos.org"],
    pick: "Check the right one and enter the date in the tracker yourself.",
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
