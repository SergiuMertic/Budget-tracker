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
- **Hand entries on cards (v15)**: the add form has a tap-to-pick list of accounts and cards and remembers the last one. A card without a balance starts at 0 owed. A card with a payment day (`opts.cardPaymentDays`) counts as paid in full on that day, so `balanceOf` restarts at 0 after it. A later CSV import replaces a hand entry with the same card and amount (3 days apart at most) and keeps its category. Known gap: the bank debit that settles a card is still counted as spending when the card side only has hand entries.

## Open tasks (in the owner's order of priority)

1. **More card imports**: Mastercard Gold (Advanzia) and Klarna. Ask the owner for a sample export before writing a parser. Follow the Amex approach: detect the file, turn the signs if needed, and use an account name that `isCardAcc` recognises so payments are matched.
2. **Household view**: import the spouse's Sparkasse CSV as a separate account (the Sparkasse layout is already recognised) and add a switch "Nur ich / Haushalt" that filters the overview by account. Transfers between the two accounts are matched automatically.
3. **Subscription overview**: list all `abos` with their monthly and yearly cost.
4. Known small gaps: fuel station brand "star" is not matched (too generic a word); the drugstore "Müller" is not matched (common surname).
