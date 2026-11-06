# Budget

A small offline web app to see where your money goes. Import your bank statements (C24 Bank PDF statements, or the CSV export from any online banking), and the app sorts every transaction into a category, shows your monthly totals and tracks your budgets.

## Features

- Import C24 Bank PDF statements (Kontoauszüge) directly, several at once; the totals are checked against each statement's summary
- Import CSV exports from German online banking (semicolon or comma, German or English number format, UTF-8 or Windows encoding)
- Columns are detected automatically from the header row; if a bank uses unusual names, you can pick the columns yourself in the preview
- Duplicates are skipped, so you can import overlapping date ranges again; pending (vorgemerkt) transactions are left out until they are booked
- Several accounts side by side (for example Girokonto and Revolut), each with its current balance: taken from C24 statements or a CSV balance column, or entered by hand
- Transfers between your own accounts are found automatically (same amount out of one account and into another within 4 days) and are not counted twice
- Automatic categories for common German merchants (REWE, Aldi, dm, Shell, Telekom, Netflix and many more)
- Your own rules: change a category once and let the app remember it for every transaction with the same text
- Monthly overview: income, spending, saving and what is left, per category with progress bars
- Monthly budgets and a savings goal, with a one-tap suggestion from your average of the last 3 months
- 6-month history chart
- Add cash transactions by hand; an option makes ATM withdrawals not count as spending, so cash is not counted twice
- Transfers between your own accounts can be marked as "not counted"
- Backup to a file and restore from it
- Light and dark mode, German interface

## Import your transactions

**C24 Bank:** Download your monthly statements (Kontoauszüge) as PDF and choose them in the app under Daten. You can pick several at once. If you import a preliminary statement (Vorläufiger Kontoauszug) and later the final one, only the new transactions are added.

**Other banks:** Most banks offer a CSV export in online banking under Umsätze, then Export or Download. Choose the date range you want (for example the last 3 or 6 months). Then open the app, go to Daten, and choose the file.

## Install on iPhone

1. Open the site in Safari.
2. Tap Share, then "Add to Home Screen".
3. Open it from the home screen. It now works offline.

## Privacy

All data is stored only on the device, in the browser's local storage. PDF and CSV files are read on the device. Nothing is sent to a server, and this repository contains no personal data.

## Publish with GitHub Pages

1. Create a new repository and upload all files from this folder (keep the `fonts` and `icons` folders).
2. In the repository, open Settings, then Pages, and choose "Deploy from a branch" with the `main` branch and the root folder.
3. After a minute the app is live at `https://<your-user>.github.io/<repository>/`.

When you change a file later, raise the number in `CACHE` in `sw.js` so phones load the new version.

## How it works

A single `index.html` with plain HTML, CSS and JavaScript, a web app manifest, and a service worker (`sw.js`) that caches the app for offline use. The fonts (Barlow, SIL Open Font License) are bundled in `fonts/`. PDF statements are read with [pdf.js](https://github.com/mozilla/pdf.js) 5.4.624 (Apache License 2.0), bundled in `vendor/pdfjs/` and loaded only when you pick a PDF.

Made with help from Claude (Anthropic).
