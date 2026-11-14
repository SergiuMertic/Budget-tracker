# Budget: notes for coding agents

Read this before changing anything. It describes how the app is built, the rules for releasing it, and what is planned next.

## What it is

An offline web app (PWA) for personal finances, with a German interface. You import bank statements and it sorts transactions into categories, tracks balances and budgets, and shows monthly results.

- Live: https://sergiumertic.github.io/Budget-tracker/ (GitHub Pages, branch `main`, root folder)
- Pushing to `main` deploys. The Pages build takes about a minute.
- No build step, no framework, no dependencies besides the bundled pdf.js.
- All user data stays in the browser (localStorage). Nothing is sent anywhere.

## Files

| File | What it is |
|---|---|
| `index.html` | The whole app: CSS, markup and one script (about 2.900 lines) |
| `sw.js` | Service worker: caches the app for offline use (network first for the page) |
| `manifest.webmanifest` | PWA manifest |
| `icons/` | App icons |
| `fonts/` | Barlow fonts (SIL Open Font License) |
| `vendor/pdfjs/` | pdf.js 5.4.624 legacy build (Apache 2.0), loaded only when a PDF is picked |
| `vendor/tesseract/` | tesseract.js 7.0.0 + core (Apache 2.0) and German data `deu.traineddata.gz` (best_int), about 9 MB, loaded only when a receipt is only a picture; `sw.js` keeps it after first use (not in `ASSETS`) |
| `tests/` | Smoke test with synthetic data (see Testing) |

## Release checklist (every change)

1. Raise `APP_VERSION` in `index.html` (shown at the bottom of the page).
2. Raise `CACHE` in `sw.js` to the same number (`budget-vN`). Without this, phones keep the old version.
3. If you add a static file, add it to `ASSETS` in `sw.js`.
4. Run `python tests/smoke_test.py`.
5. Check the page at 390 px width in light and dark mode.
6. Commit and push to `main`.

## Privacy rules (the repository is public)

- Never commit personal data: bank statements, backups, CSV exports, IBANs, real amounts, names of real people, or anything taken from the owner's data.
- Rules for specific people (family and friends) live only in the user's own backup file, as user rules with `f: 'n'` (match on the name field only). Do not add them to `DEFAULT_RULES`.
- The account holder's name is read from the statements at runtime (`S.owner`) and stays on the device.
- Test only with synthetic data in the repository. The owner keeps real files in a separate private folder outside the repository.

## Interface text

German, short and plain. Use a normal hyphen or a sentence break instead of long dashes. Amounts use `de-DE` formatting (1.234,56 €). Dates are shown as dd.mm.yyyy.

## How `index.html` is organised

Search for these section markers in the script:

| Marker | Contents |
|---|---|
| `Icons` | Inline SVG strings (`ICON`) |
| `Categories` | `BASE_CATS`: `{ id, name, kind, color, icon }`. `kind` is `out` (spending), `save` (saving), `in` (income) or `skip` (not counted) |
| `Default rules` | `DEFAULT_RULES`: `[categoryId, sign, ...keywords]`. Sign `'+'` only money in, `'-'` only money out, `''` both. **Order matters: the first match wins.** Keywords are whole words after `normText`/`catText` |
| `State` | `S` (all state), `rebuildCats`, `rebuildRules`, `categorize` |
| `Transfers between own accounts` | `linkTransfers`, `linkStrength`, `labelPair`, `relabelLinks`, `cleanLinks`, `unlink` |
| `Saving` | `save`, `cleanData` (validates storage and backups), `loadData`, `migrateAccounts` |
| `Months` | Payday months: `buildPeriods`, `periodOf`, `periodStart`, `periodRange` |
| `Numbers` | `monthStats`, `averages` |
| `CSV import` | `parseCSV`, `sniffDelim`, `ROLE` (header names), `detectRoles`, `detectFuzzy`, `sniffColumns`, `parseDate`, `parseAmount`, `isAmexFile`, `readCSVFile`, `buildImport`, `markDuplicates`, `importBalances`, `commitImport` |
| `PDF statements (C24 Bank)` | `loadPdfJs`, `pageLines`, `parseC24`, `readPdfFiles` |
| `Accounts` | `accounts`, `balanceOf` |
| `Rendering` | `renderOverview`, `renderAvailable`, `renderBalances`, `renderChart`, `renderTx`, `renderBudgets`, `renderData`, `renderImport`, `render` |
| `Actions` | Sheets, manual entries, cash account, Trinkgeld import, balances, settings |
| `Backup` | Export and import of the JSON backup |

### Stored data (`localStorage['budget.data.v1']`)

```
{ v: 1, tx: [...], budgets: { catId: cents }, rules: [...], cats: [...],
  bal: { accountName: { d: 'YYYY-MM-DD', a: cents } },
  opts: { cashManual, payday, cashSince }, owner: 'Name from statements' }
```

Transaction fields:

| Field | Meaning |
|---|---|
| `id` | Unique id |
| `d` | Booking date `YYYY-MM-DD` |
| `a` | Amount in cents, negative = money out |
| `n`, `p`, `t` | Name (other party), purpose text, booking type |
| `acc` | Account name, e.g. `C24 Girokonto`, `American Express`, `Bargeld` |
| `c` | Category id |
| `src` | `r` default rule, `u` user rule, `f` no rule matched (shown as "ohne Kategorie"), `m` set by hand, `t` linked transfer |
| `k` | Duplicate key: `account|date|amount|normText(name + purpose)` |
| `l` | Link id shared by both sides of a transfer |

Backups are `{ app: 'budget', version: 1, exportedAt, data: <same as above> }`.

### Behaviour to keep in mind

- **Categories are worked out again on every start** (`recategorizeAll` in `loadData`) for everything except `src` `m` and `t`. Improving `DEFAULT_RULES` therefore updates old transactions too.
- **Duplicates:** re-importing the same statement must add nothing. Changing `normText`, `dupKey`, account names or how name and purpose are parsed changes the keys and breaks this. `catText` (used for matching only) may change; `normText` should not.
- **Transfers:** the same amount out of one account and into another. Strength 2 (one side names the other account's bank or card) allows up to 10 days apart; strength 1 (both look like transfers) allows 4 days. Linked pairs become `umbuchung`, except that a transfer into a C24 savings pocket counts as `sparen` on the main account side.
- **Balances:** `S.bal[account]` is the balance at the end of day `d`. Bookings after that day are added. C24 statements set it from `Endsaldo` when the totals check out; CSVs set it from a balance column.
- **Verfügbar** (top of the overview) = all balances except savings (`isSavingsAcc`) and cards (`isCardAcc`). Cards are shown as "Kreditkarten offen".
- **Cash account** (`Bargeld`): when on, ATM withdrawals and deposits after `opts.cashSince` get the category `cashmove` (not counted) and move money in or out of the cash balance.
- **Payday months** (`opts.payday`): a month starts on the day the largest `gehalt` payment arrived, if that is on or after the 15th.
- **C24 PDFs:** two layouts are supported (2024/25 with "- 9,95 €", 2026 with "-9,95 €"). The parser checks the totals against "Zusammenfassung" and shows the result in the preview.
- **American Express CSV:** purchases are positive in the file, so signs are turned round (`map.invert`). Short format (`Datum,Beschreibung,Betrag`) and detailed format are both recognised.

## Testing

`tests/smoke_test.py` serves the folder locally, opens the app in headless Chromium with Playwright and checks CSV imports from several bank layouts, duplicates, the Amex import with transfer matching, balances, Verfügbar, the cash account and the backup round trip. It uses only the synthetic files in `tests/fixtures/`.

```
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/smoke_test.py
```

Every line should start with `PASS`, and the last line should be `errors: none`.

## Completed

- **"Bis zum Gehalt" (v13)**: the overview estimates the next payday and recurring debits, uses the current tracked card balance for linked settlements and unlinked card debits with a matching issuer, supports a device-only monthly automatic payment day per card, shows the remaining free amount, and warns when a forecast debit may overdraw its account.

- **Subscription overview (v14)**: "Abos" card on the Budgets tab. Groups `abos` payments by payee, detects monthly, quarterly, half-yearly and yearly charges, shows cost per month and year, and lists ended ones apart.
- **Hand entries on cards (v15)**: the add form has a tap-to-pick list of accounts and cards and remembers the last one. A card without a balance starts at 0 owed. A card with a payment day (`opts.cardPaymentDays`) counts as paid in full on that day, so `balanceOf` restarts at 0 after it. A later CSV import replaces a hand entry with the same card and amount (3 days apart at most) and keeps its category.
- **Card settlements with hand entries (v16)**: `markHandSettlements` (runs at the start of `render`) turns an unlinked bank debit that names a card (brand match) into `umbuchung`, flagged `hs`, when the card has a hand entry within 45 days before it, so the purchases are not counted twice. It is undone automatically when the hand entries are gone, and the payday forecast still treats it as a recurring debit.

- **v17**: forecast tests no longer depend on today's date. Hand entries can be edited (amount, date, account) in the transaction sheet, and the Umsätze filter has "Von Hand eingetragen". Subscriptions show the next expected charge and "Teurer geworden". Cards show their automatic debit date in the balance list. Budget rows say "schneller als der Monat" when spending runs ahead of the month. A backup reminder shows after 30 days (date kept in `localStorage['budget.lastBackup']`, not in the data). Rules added for the drugstore Müller (full phrases only) and "STAR TANK".
- **Household view (v17)**: an account can be marked as the partner's in its balance sheet (`opts.partnerAccs`). With at least one, the overview shows "Nur ich / Haushalt" (`opts.household`). "Nur ich" leaves partner accounts out of stats, lists, balances, subscriptions and the forecast; salary detection (payday months) always uses only own accounts. Known limit: a transfer between you and the partner is linked as `umbuchung`, so it counts in neither view.

- **Visuals (v18)**: spending ring (`renderDonut`, top 5 categories plus "Übrige", tappable), change against the month before per category (`cdelta`), insight sentences (`renderInsights`: budget pace, big rise against last month, subscription price rise, renewal within 7 days), daily spending pace and a step-line balance chart to payday in "Bis zum Gehalt" (`renderPaydayChart`). All plain SVG. Note: SVG elements have no `.hidden` property, use `toggleAttribute('hidden', ...)`.

- **Budget split (v19)**: the Budgets tab lists only categories you can steer (`canBudget`). Fixed costs (`FIXED_CATS`: wohnen, versicherung, handy, kredit, gebuehren, abos) sit in a collapsed "Fixkosten" card with their 3-month average and a total, and `NO_BUDGET_CATS` (bargeld, eigene) are left out. Budget totals, the overview budget line and "Leere Budgets füllen" ignore fixed categories. Ended subscriptions are no longer shown in the Abos card.

- **Abos card collapsible (v20)**: the Abos card is a `<details>` like Fixkosten, closed by default, with the monthly total in its header. Content inside a closed `<details>` has empty `innerText`, so tests use `textContent` or open it first.

- **Money on the Budgets tab (v21)**: the card "Auf deinen Konten" (`renderBudgetCash`, called from `renderBudgetSummary`) shows the spendable balances (no savings, cards listed as "Kreditkarten offen", partner accounts only in Haushalt), the fixed debits until payday (same forecast as the overview), what the budgets and savings goal still allow this month, and what is left after that. It updates as you type a budget.

- **Swipe between tabs (v22)**: a horizontal swipe (at least 70 px, mostly horizontal, under 0.7 s) moves to the next or previous tab in the order Übersicht, Umsätze, Budgets, Daten. Ignored while a sheet is open, in fields, and within 24 px of the screen edge (so the iOS back gesture still works).

- **Expected income (v23)**: the Budgets tab has a card "Erwartetes Einkommen" where you enter income that has not arrived yet (for example the partner's salary or Weihnachtsgeld) with a label, a net amount and a date (`opts.expected`, max 20, saved in the backup). Items dated today or later count in "Danach übrig" of the card "Auf deinen Konten"; older ones are shown muted and ignored.

- **Three additions (v24)**:
  - **Sonstiges breakdown** (`sonstigesBreakdown`, `renderSonstiges`): in Umsätze, when the category filter is Sonstiges and nothing is searched, a card lists the biggest payees of the last 6 months. Tapping one searches for it, so a rule can be made from its transaction.
  - **Yearly costs** (`periodicCosts`, `renderPeriodic`, v25: only yearly): payments about once a year with a steady amount, in bill-like categories (`YEARLY_CATS`: abos, versicherung, mobil, gebuehren, wohnen, handy, freizeit) and at least 15 €, shown in a collapsed Budgets card with the monthly share. A single payment counts when the payee is a known yearly bill (`YEARLY_HINT`, for example Hauptzollamt). Yearly subscriptions appear here and in the Abos card. A due payment within 30 days also appears as an insight.
  - **Monthly review** (`openReview`): the button "Monatsrückblick" on the Overview opens a sheet for the shown month with result, change against last month, fixed versus other costs, top 3 categories, budgets kept and the biggest single expense.

- **Subscriptions split by price (v26)**: `subscriptions()` now makes one subscription per payee and repeating price, so several services under one payee (all App Store charges are booked as APPLE.COM/BILL) stay apart. A later single charge at a similar price within 60 days continues the earlier one (price change). Intervals: monthly (median gap 24 to 45 days), every 2 months, quarterly, half-yearly, yearly. Gaps under 24 days are purchases, not a subscription; 2 to 6 month intervals need at least 3 charges and must be regular (v27, found with real App Store purchases on the Amex). "ADAC" is a yearly-bill hint (single payment counts).

- **Card width fix (v28)**: on an iPhone the open Abos card was wider than the screen (a long unbreakable payee name stretched the card's grid column, and the page shrank to fit). `.card` now has `grid-template-columns: minmax(0, 1fr)`, and the collapsible cards (`.fixed-card`, which are `<details>`) are `display: block`. Chromium and Playwright's WebKit never showed the problem, so the fix could not be reproduced there; a smoke test checks for horizontal overflow at 360 px. Keep any new card's columns `minmax(0, 1fr)`.
- **Kfz-Steuer category (v29)**: vehicle tax (Hauptzollamt, HZA, Kfz-Steuer) now goes to "Gebühren & Steuern" (fixed, no budget) instead of "Auto & Mobilität", so one yearly payment no longer distorts the flexible Auto budget. It still shows in "Jährliche Kosten" (`gebuehren` is in `YEARLY_CATS`).
- **Beige theme (v30)**: palette only, no layout change. Light = sand/beige page, cream cards, sage accent, sand header with dark text; dark = warm espresso instead of black/teal. All colors stay in the `:root` tokens (and the two dark blocks), so a future retune only touches those. Theme-color metas and `manifest.webmanifest` match the header.
- **Simple overview (v31)**: the Übersicht tab opens in a simple view (Verfügbar, Übrig, Bis zum Gehalt, hints, Ausgaben nach Kategorie, one "Ausgabe von Hand eintragen" button). Everything else carries the class `adv` and is hidden by `body.simple` until "Mehr anzeigen" is tapped. The choice is `S.opts.simple` (undefined = simple), kept per device and in backups. New overview parts that are not essential must get `class="adv"`. The smoke test's init script reads saved data without a choice as the full view, so older checks keep working; the simple view has its own checks.
- **No header brand (v32)**: logo and "Budget" title removed from the top so the app looks like an app; the page starts with the tabs. `<h1>` stays as `sr-only` for screen readers. `.band` is only a status-bar spacer in the page color.
- **Clearer overview (v33)**: a headline card (`#nowCard`, `renderNow`) leads the overview: the money free until payday as one big number (falls back to the account balance without a payday, or asks for a balance), a plain sentence (per day, days left) and one status line (Aufpassen / Über Budget / Fast aufgebraucht / Alles im Plan). The old Verfügbar block and the Bis-zum-Gehalt card are `adv` (full view only). `paydayInfo` carries the payday result to `renderNow`. "Ausgabe von Hand eintragen" is a floating button (`.fab`); the backup reminder moved below the category list; labels use everyday words (Auf dem Konto, Noch zu zahlen, Zum Ausgeben).
- **Credit cards, budget offer, receipts (v34)**: (1) `renderCards` / `#cardsCard`: per card what is still to pay and the debit day, total, and what is left on the accounts afterwards (shown in the simple view). (2) `#budgetOffer`: when no budgets exist, the overview offers `suggestBudgets()` in one tap. (3) Receipt split: in a payment's sheet, "Kassenbon (PDF) aufteilen" reads a receipt PDF with pdf.js (`parseReceipt`: article lines `name price`, discounts merge into the article above, Pfand stays food, stops at SUMME), guesses a category per article by keyword (`RC_DROGERIE`, `RC_SHOP`, else food), lets the user fix each one, then `applySplit` keeps the original entry (same duplicate key, largest category, field `s0` = original amount) and adds one child entry per other category (`so` = parent id, key `split|id|cat`, type "Kassenbon"). `unsplit` restores it. Deleting a part undoes the whole split. Only payments (negative, not transfers, not hand entries) can be split. The parser was written without a real receipt: when the owner shares one (never commit it), check it against `parseReceipt` and extend the keyword lists.
- **Guides, goals, sharing (v35)**: (1) `#importHint` on the overview when the newest bank entry is over 7 days old; an import guide (`#importGuide`, per bank, only generic menu wording because the exact bank menus were not verified) in the Daten tab; the welcome card has three steps. (2) Quick-add: `previousHandEntry` takes over category and card of an earlier hand entry with the same description (`addAccTouched` stops it overriding a card chosen in the sheet); `#addNameList` offers the 12 most used descriptions. (3) Savings goals in `S.opts.goals` `{ id, n, a, s, d }` (cleaned in `cleanData`, max 12): card on the Budgets tab, compact list on the overview, `goalSub` shows what is left and the monthly amount until the date. (4) `Stand teilen` builds a short text from `snap` (filled by `renderNow`, `renderCards` and `renderOverview`) and uses the share sheet, or copies it. Nothing is sent anywhere by the app itself.
- **Sheets close by swipe (v36)**: every `dialog.sheet` closes by tapping the dimmed area or by pulling it down (touch handlers near the end of the script, `requestClose` fires the dialog's own `cancel` first so `txSheet` still saves its rule). The pull starts anywhere on the sheet when it is scrolled to the top, except on inputs, selects and the receipt list. Checked with synthetic touch events only, not on a real iPhone.
- **Receipt photos and manual split (v37)**: Lidl's downloadable receipt is a PDF made of a picture, which pdf.js cannot read. `readReceipt` now tries the PDF text first; if nothing is found (or the file is a photo, `image/*`) it renders the page(s) to a canvas (`pdfPageCanvas` / `imageCanvas`, grey + contrast stretch in `boostCanvas`) and runs tesseract.js in a worker on the device (`ocrReceipt`, `makeOcrWorker`; page segmentation mode 6 so the price stays on the article's line; SIMD core when `SIMD_OK`). `ocrPages` fixes `1.29` / `1 ,29` to `1,29`, then the same `parseReceipt` runs. `parseReceipt` also joins a price that stands alone on its line with the name above it (weighed goods: name, `0,894 kg x 1,69 EUR/kg`, price) and no longer drops names containing `%` ("Milch 3,5%"). If OCR finds nothing, `openManualSplit` opens. `shManualBtn` / `#splitSheet` splits a payment by hand: amount that was food plus a category for the rest, applied with the same `commitSplit` / `applySplit`. `#ocrSheet` shows progress and cannot be swiped away (its `cancel` is prevented; the Abbrechen button stops the worker). Tested only with synthetic images (clean and a blurred, tilted one), not with a real Lidl receipt: when the owner shares one (never commit it), check the OCR output and adjust the cleanup in `ocrPages` and the keyword lists.

## Open tasks (in the owner's order of priority)

1. **More card imports**: Mastercard Gold (Advanzia) and Klarna. Ask the owner for a sample export before writing a parser. Follow the Amex approach: detect the file, turn the signs if needed, and use an account name that `isCardAcc` recognises so payments are matched.
2. **Household view**: built in v17. Still to do with real data: import the spouse's Sparkasse CSV and check the numbers.
3. **Subscription overview**: done in v14 and v17.
4. Known small gaps: only the phrases "STAR TANK" and "MUELLER DROGERIE" (and a few similar) are matched, not the bare words.
