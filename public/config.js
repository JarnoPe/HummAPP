// HummAPP julkisen verkkosivuston (hummapp.fi) konfiguraatio.
// Kun sivusto hostataan GitHub Pagesissa, aseta apiBaseUrl osoittamaan joko:
// 1) Synology NASin julkiseen HTTPS-osoitteeseen (esim. "https://api.hummapp.fi")
// 2) tai pilottipalvelimen osoitteeseen,
// tai jätä tyhjäksi ("") jos sivusto toimii samassa palvelimessa tai staattisena tilannekuvana (public-data.json).
window.HUMMAPP_PUBLIC_CONFIG = {
  apiBaseUrl: "",
  domainName: "hummapp.fi"
};
