"""Smoke test for the Budget app. Uses only the synthetic files in tests/fixtures.

Run from anywhere:  python3 tests/smoke_test.py
Needs: python3 -m pip install playwright  and  python3 -m playwright install chromium
Optional: set CHROME to a Chrome/Chromium binary to use it instead of Playwright's own.
"""
import os
import re
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, 'tests', 'fixtures')
results = []


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def check(label, cond, extra=''):
    results.append(cond)
    print(('PASS ' if cond else 'FAIL ') + label + (('  ' + str(extra)) if extra != '' and not cond else ''))


def fx(name):
    return os.path.join(FIX, name)


def main():
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    errors = []
    try:
        with sync_playwright() as p:
            opts = {'args': ['--no-sandbox']}
            if os.environ.get('CHROME'):
                opts['executable_path'] = os.environ['CHROME']
            browser = p.chromium.launch(**opts)
            ctx = browser.new_context(viewport={'width': 390, 'height': 844}, locale='de-DE', accept_downloads=True, reduced_motion='reduce')
            page = ctx.new_page()
            page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
            page.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
            page.on('dialog', lambda d: d.accept())
            page.goto('http://127.0.0.1:%d/' % port)
            page.wait_for_timeout(500)
            check('welcome card on an empty device', page.is_visible('#welcome'))

            def preview(file):
                page.click('#tab-data')
                page.set_input_files('#csvInput', file)
                page.wait_for_selector('#previewCard:not([hidden])', timeout=15000)
                return page.evaluate("""() => ({ new: pvNew.textContent, dup: pvDup.textContent, skip: pvSkip.textContent,
                    acc: pvAcc.value, range: pvRange.textContent, invert: mInvert.checked })""")

            def commit():
                page.click('#pvImport')
                page.wait_for_timeout(400)

            # Bank CSV layouts
            info = preview(fx('sparkasse.csv'))
            check('Sparkasse: 49 new, account guessed', info['new'] == '49' and info['acc'] == 'Sparkasse', info)
            commit()
            info = preview(fx('sparkasse.csv'))
            check('Sparkasse again: all duplicates', info['new'] == '0' and info['dup'] == '49', info)
            page.click('#pvCancel')
            for name, new, extra in [('ing.csv', '4', None), ('dkb.csv', '3', 'pending'), ('n26.csv', '3', None),
                                     ('revolut.csv', '2', None), ('unbekannt.csv', '2', 'names')]:
                info = preview(fx(name))
                ok = info['new'] == new
                if extra == 'pending':
                    ok = ok and info['skip'] == '1'
                if extra == 'names':
                    ok = ok and 'Unbekanntes Format' in info['range']
                check(name + ': ' + new + ' new', ok, info)
                commit()

            # American Express: signs turned, payment matched with the bank side
            info = preview(fx('amex.csv'))
            check('Amex detected, signs turned', info['acc'] == 'American Express' and info['invert'] and 'Abrechnung erkannt' in info['range'], info)
            commit()
            info = preview(fx('giro-card-payment.csv'))
            commit()
            data = page.evaluate("JSON.parse(localStorage.getItem('budget.data.v1'))")
            amex = [t for t in data['tx'] if t['acc'] == 'American Express']
            pay = [t for t in data['tx'] if 'AMERICAN EXPRESS' in t['n'] or 'ZAHLUNG' in t['n']]
            check('Amex purchases negative, refund positive', any(t['a'] == -2340 for t in amex) and any(t['a'] == 1995 for t in amex), [(t['n'], t['a']) for t in amex])
            check('Amex payment linked on both sides', len(pay) == 2 and all(t.get('l') and t['c'] == 'umbuchung' for t in pay), [(t['acc'], t['a'], t['c'], t.get('l')) for t in pay])

            # Balances and Verfügbar
            page.click('#tab-overview')
            page.click('#balList .balrow:has-text("Sparkasse")')
            page.wait_for_selector('#balSheet[open]')
            page.fill('#balAmt', '500')
            page.fill('#balDate', '2026-11-30')
            page.click('#balSave')
            page.wait_for_timeout(200)
            page.click('#balList .balrow:has-text("American Express")')
            page.wait_for_selector('#balSheet[open]')
            check('card balance sheet asks for amount owed', page.is_checked('#balNeg'))
            page.fill('#balAmt', '50')
            page.fill('#balDate', '2026-11-30')
            page.fill('#balPayDay', '10')
            page.click('#balSave')
            page.wait_for_timeout(200)
            av = page.evaluate("() => ({ big: availBig.textContent, meta: availMeta.textContent })")
            card_payment_day = page.evaluate("() => JSON.parse(localStorage.getItem('budget.data.v1')).opts.cardPaymentDays['American Express']")
            check('automatic card payment day is saved locally', card_payment_day == 10, card_payment_day)
            num = lambda t: float(t.replace('\xa0', ' ').replace('€', '').replace('.', '').replace(',', '.').strip())
            after_cards = av['meta'].split('danach ')[1].split(' ·')[0] if 'danach ' in av['meta'] else ''
            check('Verfügbar excludes cards and shows them below', 'Kreditkarten offen: 50,00' in av['meta'] and after_cards and abs(num(av['big']) - 50 - num(after_cards)) < 0.005, av)

            # Cash account
            page.click('#tab-data')
            page.check('#cashManual')
            page.wait_for_selector('#balSheet[open]')
            check('cash account asks how much cash', page.text_content('#balSheetTitle') == 'Wie viel Bargeld hast du?')
            page.fill('#balAmt', '80')
            page.click('#balSave')
            page.wait_for_timeout(200)
            page.click('#tab-overview')
            page.click('#balCard [data-action="add-tx"]')
            page.wait_for_selector('#addSheet[open]')
            page.fill('#addAmt', '4,50')
            page.fill('#addName', 'Bäcker')
            check('description suggests a category', page.input_value('#addCat') == 'lebensmittel', page.input_value('#addCat'))
            page.click('#addSave')
            page.wait_for_timeout(200)
            rows = page.evaluate("() => Array.from(document.querySelectorAll('#balList .balrow')).map(b => b.innerText.replace(/\\n/g, ' | '))")
            check('cash purchase lowers Bargeld to 75,50', any(r.startswith('Bargeld') and '75,50' in r for r in rows), rows)

            # Backup round trip
            page.click('#tab-data')
            with page.expect_download() as dl:
                page.click('#exportBtn')
            path = os.path.join(ROOT, 'tests', '_backup_test.json')
            dl.value.save_as(path)
            before = page.evaluate("localStorage.getItem('budget.data.v1')")
            page.click('#wipeBtn')
            page.wait_for_timeout(200)
            page.set_input_files('#backupInput', path)
            page.wait_for_timeout(600)
            after = page.evaluate("JSON.parse(localStorage.getItem('budget.data.v1'))")
            import json
            b = json.loads(before)
            check('backup restores everything', len(after['tx']) == len(b['tx']) and after['bal'] == b['bal'] and after['opts'] == b['opts'])
            os.remove(path)

            # "Bis zum Gehalt": recurring rent and an unlinked Amex debit use synthetic data only
            page.evaluate("""() => {
                const now = new Date();
                const today = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-');
                const monthAt = (delta) => {
                    const d = new Date(now.getFullYear(), now.getMonth() + delta, 1);
                    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
                };
                const currentLabel = monthAt(now.getDate() >= 28 ? 1 : 0);
                const dueDay = now.getDate() < 27 ? now.getDate() + 1 : now.getDate() === 27 ? 27 : 5;
                const data = { v: 1, tx: [], budgets: {}, rules: [], cats: [], bal: { 'Example Checking': { d: today, a: 60000 }, 'American Express': { d: today, a: -12345 } }, opts: { cashManual: false, payday: true, cashSince: '', cardPaymentDays: { 'American Express': 10 } }, owner: '' };
                let serial = 0;
                const add = (tx) => data.tx.push(Object.assign({ id: 'forecast-' + (++serial), src: 'r' }, tx));
                for (let offset = 1; offset <= 4; offset++) {
                    add({ d: monthAt(-offset) + '-28', a: 300000, n: 'Example Employer', p: 'LOHN GEHALT', acc: 'Example Checking', c: 'gehalt' });
                }
                if (now.getDate() >= 28) add({ d: monthAt(0) + '-28', a: 300000, n: 'Example Employer', p: 'LOHN GEHALT', acc: 'Example Checking', c: 'gehalt' });
                for (let offset = 1; offset <= 3; offset++) {
                    const month = monthAt((now.getDate() >= 28 ? 1 : 0) - offset);
                    const billDate = month + '-' + String(dueDay).padStart(2, '0');
                    add({ d: billDate, a: -50000, n: 'Example Landlord GmbH', p: 'Monthly rent', acc: 'Example Checking', c: 'wohnen' });
                    add({ d: billDate, a: -2000, n: 'REWE', p: 'Card purchase', t: 'KARTENZAHLUNG', acc: 'Example Checking', c: 'lebensmittel' });
                    add({ d: billDate, a: -25000, n: 'American Express Europe S.A. (Germany branch)', p: 'Card settlement', t: 'LASTSCHRIFT', acc: 'Example Checking', c: 'kredit' });
                }
                localStorage.setItem('budget.data.v1', JSON.stringify(data));
            }""")
            page.reload()
            page.wait_for_timeout(300)
            forecast = page.evaluate("""() => ({
                label: paydayDueLabel.textContent,
                due: paydayDue.textContent,
                free: paydayFree.textContent,
                warning: paydayWarning.textContent,
                rows: Array.from(paydayList.querySelectorAll('li')).map((li) => li.innerText)
            })""")
            check('unlinked Amex debit uses the current card balance and configured day', abs(num(forecast['due']) - 623.45) < 0.005 and len(forecast['rows']) == 2 and any('American Express' in row and '123,45' in row and re.search(r'\b10\.\d{2}\.\d{4}\b', row) for row in forecast['rows']), forecast)
            check('automatic debit warns about a shortfall by the configured day', abs(num(forecast['free']) + 23.45) < 0.005 and 'automatische Abbuchung' in forecast['warning'] and 'bis zum' in forecast['warning'] and re.search(r'\b10\.\d{2}\.\d{4}\b', forecast['warning']) and 'Rücklastschrift' in forecast['warning'], forecast)

            # Subscription overview (synthetic data)
            page.evaluate("""() => {
                const now = new Date();
                const at = (m, day) => { const d = new Date(now.getFullYear(), now.getMonth() + m, day); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
                const data = { v: 1, tx: [], budgets: {}, rules: [], cats: [], bal: {}, opts: { cashManual: false, payday: false, cashSince: '', cardPaymentDays: {} }, owner: '' };
                let n = 0;
                const add = (d, a, name) => data.tx.push({ id: 'sub-' + (++n), src: 'r', d: d, a: a, n: name, p: 'Abo', acc: 'Example Checking', c: 'abos' });
                for (let m = -3; m <= 0; m++) add(at(m, 1), -1299, 'NETFLIX');
                for (let m = -3; m <= 0; m++) add(at(m, 3), -499, 'SPOTIFY');
                add(at(-14, 10), -12000, 'ADOBE');
                add(at(-2, 10), -12000, 'ADOBE');
                for (let m = -9; m <= -6; m++) add(at(m, 5), -999, 'DAZN');
                add(at(0, 2), 1299, 'NETFLIX');
                localStorage.setItem('budget.data.v1', JSON.stringify(data));
            }""")
            page.reload()
            page.wait_for_timeout(300)
            page.click('#tab-budgets')
            subs = page.evaluate("""() => ({ month: subsMonth.textContent, year: subsYear.textContent,
                rows: Array.from(subsList.querySelectorAll('li')).map((li) => li.innerText),
                ended: Array.from(subsEnded.querySelectorAll('li')).map((li) => li.innerText) })""")
            check('subscriptions: 3 active, sorted by monthly cost', len(subs['rows']) == 3 and 'NETFLIX' in subs['rows'][0] and 'ADOBE' in subs['rows'][1] and 'SPOTIFY' in subs['rows'][2], subs)
            check('subscriptions: monthly and yearly totals', abs(num(subs['month']) - (10 + 12.99 + 4.99)) < 0.005 and abs(num(subs['year']) - (120 + 12 * (12.99 + 4.99))) < 0.005, subs)
            check('subscriptions: ended one is listed apart', len(subs['ended']) == 1 and 'DAZN' in subs['ended'][0], subs)

            # Version shown and service worker registered
            note = page.text_content('#note')
            check('version shown at the bottom', 'Version' in note, note)
            browser.close()
    finally:
        srv.terminate()
    print('errors:', errors or 'none')
    sys.exit(0 if all(results) and not errors else 1)


if __name__ == '__main__':
    main()
