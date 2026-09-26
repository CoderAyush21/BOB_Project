"""Builds `demo-repo/`: a small invoicing library with a realistic git history
of features and bug fixes. This is the patient Bug Vaccine immunises.

Usage:  python demo/build_demo_repo.py [target_dir]   (default: demo-repo)

The history is scripted so the demo is reproducible, but the bugs are the
kind real teams ship: an off-by-one, a missing null check, float money math.
Some fixes shipped with a regression test, some didn't. That's the point.
"""
import os
import shutil
import stat
import subprocess
import warnings
import sys
from pathlib import Path

TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else "demo-repo")

PACKAGE = """{
  "name": "invoice-kit",
  "version": "1.4.0",
  "private": true,
  "type": "module",
  "scripts": { "test": "node --test" }
}
"""

MONEY_BUGGY = """export function invoiceTotal(lines) {
  return lines.reduce((sum, l) => sum + l.price * l.qty, 0);
}
"""
MONEY_FIXED = """// Work in integer cents: float math drifts (0.1 + 0.2 !== 0.3).
export function invoiceTotal(lines) {
  const cents = lines.reduce((sum, l) => sum + Math.round(l.price * 100) * l.qty, 0);
  return cents / 100;
}
"""
MONEY_TEST = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { invoiceTotal } from '../src/money.js';

test('sums lines', () => {
  assert.equal(invoiceTotal([{ price: 10, qty: 2 }, { price: 5, qty: 1 }]), 25);
});

test('regression #63: no float drift', () => {
  assert.equal(invoiceTotal([{ price: 0.1, qty: 1 }, { price: 0.2, qty: 1 }]), 0.3);
});
"""

PAGE_BUGGY = """export function page(items, pageNo, size) {
  const start = pageNo * size;
  return items.slice(start, start + size - 1);
}
"""
PAGE_FIXED = """export function page(items, pageNo, size) {
  const start = pageNo * size;
  return items.slice(start, start + size);
}
"""
PAGE_TEST = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { page } from '../src/paginate.js';

test('regression #41: full pages keep their last item', () => {
  assert.deepEqual(page([1, 2, 3, 4, 5], 0, 2), [1, 2]);
  assert.deepEqual(page([1, 2, 3, 4, 5], 2, 2), [5]);
});
"""

CUST_BUGGY = """export function billingCity(customer) {
  return customer.address.city;
}
"""
CUST_FIXED = """export function billingCity(customer) {
  return customer.address?.city ?? 'Unknown';
}
"""
CUST_TEST = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { billingCity } from '../src/customers.js';

test('returns the billing city', () => {
  assert.equal(billingCity({ address: { city: 'Leeds' } }), 'Leeds');
});
"""

POSTMORTEM_57 = """# Postmortem: nightly invoice run crashed (#57)

**Date:** 2026-04-14 · **Severity:** SEV-2 · **Duration:** 3h 10m

## What happened
The nightly invoice run crashed with `TypeError: Cannot read properties of undefined (reading 'city')`.
312 invoices were not sent until the run was restarted by hand.

## Root cause
Customers imported from the new CRM can be created **without an address object**.
`billingCity()` read `customer.address.city` directly.

## Fix
Guard with optional chaining and fall back to `'Unknown'`.

## Follow-ups
- [ ] Add a regression test for customers with no address  ← *never done*
- [ ] Audit other code that reads nested customer fields
"""

REPORTS = """// Monthly reports. Added long after the #41/#57/#63 fixes.
export function reportPage(rows, pageNo, perPage) {
  const from = pageNo * perPage;
  return rows.slice(from, from + perPage);
}

export function shippingLabel(customer) {
  const city = customer.shipping?.city ?? 'Unknown';
  return `${customer.name} - ${city}`;
}

export function taxTotal(lines, rate) {
  const cents = lines.reduce((sum, l) => sum + Math.round(l.amount * rate * 100), 0);
  return cents / 100;
}
"""
REPORTS_TEST = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { reportPage, shippingLabel, taxTotal } from '../src/reports.js';

test('reportPage returns rows', () => {
  assert.ok(reportPage([1, 2, 3], 0, 10).length > 0);
});

test('shippingLabel includes name', () => {
  assert.match(shippingLabel({ name: 'Ada', shipping: { city: 'York' } }), /Ada/);
});

test('taxTotal computes tax', () => {
  assert.equal(taxTotal([{ amount: 100 }], 0.2), 20);
});
"""

HISTORY = [
    ("feat: invoice totals and billing city", {
        "package.json": PACKAGE, "src/money.js": MONEY_BUGGY, "src/customers.js": CUST_BUGGY,
        "test/customers.test.js": CUST_TEST,
        "README.md": "# invoice-kit\n\nInvoice helpers. Run tests with `npm test`.\n",
    }),
    ("feat: paginate invoice lists", {"src/paginate.js": PAGE_BUGGY}),
    ("fix: pagination dropped the last item of every page (#41)", {
        "src/paginate.js": PAGE_FIXED, "test/paginate.test.js": PAGE_TEST}),
    ("fix: crash when customer has no address (#57)", {
        "src/customers.js": CUST_FIXED, "docs/postmortems/2026-04-invoice-run-crash.md": POSTMORTEM_57}),
    ("fix: invoice totals off by a cent due to float math (#63)", {
        "src/money.js": MONEY_FIXED, "test/money.test.js": MONEY_TEST}),
    ("feat: monthly reports module", {"src/reports.js": REPORTS, "test/reports.test.js": REPORTS_TEST}),
]


def git(*args):
    subprocess.run(["git", *args], cwd=TARGET, check=True, capture_output=True)


def _force_remove(func, path, _exc):
    # git marks object files read-only; Windows refuses to delete those.
    os.chmod(path, stat.S_IWRITE)
    func(path)


def main():
    if TARGET.exists():
        with warnings.catch_warnings():  # onerror is deprecated in 3.12 but works on 3.9+
            warnings.simplefilter("ignore", DeprecationWarning)
            shutil.rmtree(TARGET, onerror=_force_remove)
    TARGET.mkdir(parents=True)
    git("init", "-q", "-b", "main")
    git("config", "user.name", "Invoice Kit Dev")
    git("config", "user.email", "dev@invoice-kit.example")
    git("config", "core.autocrlf", "false")  # keep LF so mutant 'find' strings match on Windows too
    for i, (message, files) in enumerate(HISTORY):
        for rel, content in files.items():
            path = TARGET / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        git("add", "-A")
        git("commit", "-q", "-m", message, "--date", f"2026-0{i + 1}-15T10:00:00")
    print(f"Built {TARGET}/ with {len(HISTORY)} commits")


if __name__ == "__main__":
    main()
