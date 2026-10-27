# Khula Collective — install on a mobile phone

**Installable web app (PWA), not a native APK or an App Store listing.**

Website: https://khula-collective-production.up.railway.app
Dedicated install instructions: https://khula-collective-production.up.railway.app/app/static/install.html

## Android (Google Chrome / supported browsers)

1. Open the Khula website in **Google Chrome**.
2. Tap **📲 Install Khula on your phone** on the sign-in page.
3. If an **Install Khula on this device** button appears, tap it and confirm.
4. Otherwise use Chrome's **⋮ menu → Install app** or
   **Add to Home screen** (wording varies by browser/device).
5. Open the **Khula** icon on your phone's home screen.

Android install prompts depend on the browser and its engagement/install
eligibility rules. Some browsers may instead create a home-screen shortcut.

## iPhone (Safari)

1. Open the Khula website using **Safari**.
2. Tap **📲 Install Khula on your phone**.
3. In Safari choose **Share → Add to Home Screen**.
4. Select **Open as Web App** (where available), then **Add**.
5. Tap the **Khula** icon on your iPhone home screen.

The Safari menu location and wording vary by iOS version. Apple supplies
the installation action; Khula does not silently install itself.

## Safe installation and fraud prevention

**Only install the official web app over HTTPS.** The exact address must be:
`khula-collective-production.up.railway.app`. Verify it in your mobile
browser before selecting Install/Add to Home Screen. Do not use a shortened,
forwarded or look-alike link that points to a different host.

- **No unofficial APK/IPA:** This release does not distribute a native
  Android installer, iPhone installer or ZIP. An attachment claiming to be
  "Khula.apk" is **not** an official Khula release.
- **No bank login needed:** Installation does not ask for FNB internet
  banking credentials, an OTP, a PIN, card details or ID documents.
- **No automatic membership:** Installing the home-screen web app never
  bypasses the club's identity and administrator-approval process.
- **No private offline storage:** The install page registers no service
  worker. Private data must still be fetched from the approved online session.
- **Browser prompts vary:** An Add to Home Screen shortcut is possible even
  when an operating-system WebAPK is not supported; do not treat missing
  install prompts as a reason to sideload software.

## Security controls for the installation page

- HTTPS/TLS origin validated by an independent production GitHub runner; 
  redirects to another host fail the acceptance check.
- The reviewed install page uses an exact **SHA-256 CSP hash** for its
  own inline CSS and JavaScript; `unsafe-inline` and `unsafe-eval` are
  forbidden. Changing the script or CSS requires regenerating the CSP hash
  during a trusted Docker build or the validation fails.
- The installer forbids network fetches, workers, frames, forms, plugins,
  external styles/fonts and unreviewed inline event handlers.
- Its PWA manifest and PNG icons are served from the same HTTPS origin,
  with `X-Content-Type-Options: nosniff` confirmed in acceptance checks.
- Mobile Chromium tests simulate Android and iPhone browsers; they verify
  install guidance runs under the CSP without enabling a service worker.
- This does **not** mean that an independently signed APK exists or that
  the whole Streamlit platform has passed a penetration test. Strict HTTP
  security headers for all application routes, operator review, backups,
  privacy compliance, MFA and genuine bank permissions are separate tasks.

## What does the installed app do?

- Khula opens in a standalone, phone-friendly window with a branded icon.
- It uses the **same production member accounts** and administrator approvals
  as the website; installing the app does not register anyone or grant access.
- Members must be online to sign in, vote, view contributions and access
  other private club data.
- The PWA does **not** create a fake downloaded Android package. There is no
  Google Play/App Store listing or push notification subscription in this
  release.
- We intentionally **do not register a service worker** and do not build
  an offline cache of member profiles, passwords or bank/ledger data.
  No promises of usable offline financial dashboards are made.
- Existing privacy and legal sign-offs remain required for real-member
  registration. FNB data remains unconnected until separately authorised.

## Technical components

- Streamlit's approved static serving under `/app/static/`.
- Verified JSON manifest `/app/static/khula-manifest.json` with
  `name=Khula Collective`, `short_name=Khula`, `start_url=/`,
  `scope=/`, `display=standalone`, 192/512 pixel PNG and maskable icons.
- Original Python/Pillow-generated icons in the Docker build (no third-party
  images, fonts or brand marks).
- Build-time patch to the installed Streamlit `static/index.html` HTML
  head. The patch fails explicitly if a Streamlit upgrade changes the
  expected shell and must be reviewed before upgrading Streamlit.
- `scripts/check_public_pwa.py` independently checks the production HTML
  manifest link, install instructions and downloaded icon dimensions over HTTPS.
- No change to Railway member SQLite schema, secrets, service domain,
  persistent volume or financial API permissions.

## Acceptance before telling all members to install

1. GitHub CI generates branded PNGs and verifies Streamlit index compatibility.
2. Railway deploy is `SUCCESS` for the exact merged commit.
3. Public PWA workflow verifies HTTPS root HTML, JSON manifest, installer
   page and both icon sizes.
4. A real Android Chrome device and an iPhone Safari device confirm the
   resulting **home-screen name and icon** and that installed app loads Khula
   login; this requires actual device/browser testing.
5. Approved members sign in and sign out normally. Pending applicants
   must remain unable to access private data.
6. No private records appear in offline caches or are available after logout.

## References

- PWA manifest installability: https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable
- Streamlit static file serving: https://docs.streamlit.io/develop/concepts/configuration/serving-static-files
- iPhone installation: https://support.apple.com/guide/iphone/open-as-web-app-iphea86e5236/ios
