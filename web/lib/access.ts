// The shared access password for the API, kept for the browser session only.

const KEY = "beacon.access";
let memory = ""; // fallback when sessionStorage is blocked

export function getAccessPassword(): string {
  try {
    return sessionStorage.getItem(KEY) ?? memory;
  } catch {
    return memory;
  }
}

export function setAccessPassword(password: string) {
  memory = password;
  try {
    sessionStorage.setItem(KEY, password);
  } catch {
    // Storage blocked; `memory` carries it until the page reloads.
  }
}
