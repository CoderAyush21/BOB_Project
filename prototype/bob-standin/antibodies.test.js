// PROTOTYPE STAND-IN for IBM Bob's output in step 5 ("Antibodies").
// In the real submission run, Bob writes this file (bob-prompts/03-vaccinate.md).
//
// Antibodies test the bug PATTERN, not the single mutant that exposed it:
// many inputs, boundaries, every function the pattern applies to. An earlier
// mutant-specific version scored 100% on the known mutants but only 50% on
// held-out mutants; this version is what that lesson produced.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { page } from '../src/paginate.js';
import { billingCity } from '../src/customers.js';
import { invoiceTotal } from '../src/money.js';
import { reportPage, shippingLabel, taxTotal } from '../src/reports.js';

const cents = Array.from({ length: 99 }, (_, i) => (i + 1) / 100); // 0.01 … 0.99

// A41 — off-by-one in pagination: pages must tile the list exactly, for every size.
function assertPagesTile(paginate) {
  for (let n = 0; n <= 12; n++) {
    const items = Array.from({ length: n }, (_, i) => i);
    for (let size = 1; size <= 5; size++) {
      const pages = Math.ceil(n / size);
      const joined = Array.from({ length: pages }, (_, p) => paginate(items, p, size)).flat();
      assert.deepEqual(joined, items, `n=${n} size=${size}`);
    }
  }
}

test('antibody A41: page() covers every item exactly once', () => assertPagesTile(page));
test('antibody A41: reportPage() covers every item exactly once', () => assertPagesTile(reportPage));

// A57 — missing null guard on nested customer fields: every reader survives missing objects.
test('antibody A57: billingCity survives missing or null address', () => {
  for (const c of [{}, { address: null }, { address: undefined }]) {
    assert.equal(billingCity(c), 'Unknown');
  }
});

test('antibody A57: shippingLabel survives missing or null shipping', () => {
  for (const shipping of [undefined, null]) {
    assert.equal(shippingLabel({ name: 'Ada', shipping }), 'Ada - Unknown');
  }
});

// A63 — float money math: every cent value, alone and in pairs, must add up exactly.
test('antibody A63: invoiceTotal is exact for every cent value and pair', () => {
  for (const a of cents) {
    assert.equal(invoiceTotal([{ price: a, qty: 1 }]), a);
    for (const b of cents) {
      assert.equal(invoiceTotal([{ price: a, qty: 1 }, { price: b, qty: 1 }]),
        Math.round((a + b) * 100) / 100);
    }
  }
});

test('antibody A63: taxTotal is exact for every cent value and pair', () => {
  for (const a of cents) {
    assert.equal(taxTotal([{ amount: a }], 1), a);
    for (const b of cents) {
      assert.equal(taxTotal([{ amount: a }, { amount: b }], 1), Math.round((a + b) * 100) / 100);
    }
  }
});
