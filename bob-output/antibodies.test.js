import { test } from 'node:test';
import assert from 'node:assert/strict';
import { page } from '../src/paginate.js';
import { billingCity } from '../src/customers.js';
import { invoiceTotal } from '../src/money.js';
import { reportPage, shippingLabel, taxTotal } from '../src/reports.js';

// ── Antibody A41: slice end is exclusive — every page keeps its last item ───

test('antibody A41: page() covers every item exactly once — full pages', () => {
  // 5 items, page size 2: pages [1,2], [3,4], [5]
  assert.deepEqual(page([1, 2, 3, 4, 5], 0, 2), [1, 2]);
  assert.deepEqual(page([1, 2, 3, 4, 5], 1, 2), [3, 4]);
  assert.deepEqual(page([1, 2, 3, 4, 5], 2, 2), [5]);
});

test('antibody A41: page() covers every item exactly once — page size 1', () => {
  assert.deepEqual(page(['a', 'b', 'c'], 0, 1), ['a']);
  assert.deepEqual(page(['a', 'b', 'c'], 1, 1), ['b']);
  assert.deepEqual(page(['a', 'b', 'c'], 2, 1), ['c']);
});

test('antibody A41: page() covers every item exactly once — single page covers all', () => {
  const items = [10, 20, 30];
  assert.deepEqual(page(items, 0, 3), [10, 20, 30]);
});

test('antibody A41: page() last page is partial when items do not divide evenly', () => {
  // 7 items, page size 3: pages [1,2,3], [4,5,6], [7]
  assert.deepEqual(page([1, 2, 3, 4, 5, 6, 7], 0, 3), [1, 2, 3]);
  assert.deepEqual(page([1, 2, 3, 4, 5, 6, 7], 1, 3), [4, 5, 6]);
  assert.deepEqual(page([1, 2, 3, 4, 5, 6, 7], 2, 3), [7]);
});

test('antibody A41: reportPage() covers every item exactly once — full pages', () => {
  const rows = ['r1', 'r2', 'r3', 'r4', 'r5'];
  assert.deepEqual(reportPage(rows, 0, 2), ['r1', 'r2']);
  assert.deepEqual(reportPage(rows, 1, 2), ['r3', 'r4']);
  assert.deepEqual(reportPage(rows, 2, 2), ['r5']);
});

test('antibody A41: reportPage() last item of a full page is included', () => {
  const rows = [1, 2, 3, 4, 5, 6];
  // With - 1 bug: page 0 of size 3 returns [1,2] not [1,2,3]
  assert.deepEqual(reportPage(rows, 0, 3), [1, 2, 3]);
  assert.deepEqual(reportPage(rows, 1, 3), [4, 5, 6]);
});

test('antibody A41: reportPage() single-item pages work correctly', () => {
  const rows = ['x', 'y', 'z'];
  assert.deepEqual(reportPage(rows, 0, 1), ['x']);
  assert.deepEqual(reportPage(rows, 1, 1), ['y']);
  assert.deepEqual(reportPage(rows, 2, 1), ['z']);
});

test('antibody A41: reportPage() partial last page is not empty', () => {
  // 5 rows, perPage 4: second page should have [5] not []
  const rows = [1, 2, 3, 4, 5];
  assert.deepEqual(reportPage(rows, 0, 4), [1, 2, 3, 4]);
  assert.deepEqual(reportPage(rows, 1, 4), [5]);
});

// ── Antibody A57: nested customer fields survive missing/null intermediaries ─

test('antibody A57: billingCity survives missing address (undefined)', () => {
  assert.equal(billingCity({}), 'Unknown');
});

test('antibody A57: billingCity survives null address', () => {
  assert.equal(billingCity({ address: null }), 'Unknown');
});

test('antibody A57: billingCity survives undefined address', () => {
  assert.equal(billingCity({ address: undefined }), 'Unknown');
});

test('antibody A57: billingCity returns city when address is present', () => {
  assert.equal(billingCity({ address: { city: 'Leeds' } }), 'Leeds');
  assert.equal(billingCity({ address: { city: 'NYC' } }), 'NYC');
  assert.equal(billingCity({ address: { city: '' } }), '');
});

test('antibody A57: shippingLabel survives missing shipping (undefined)', () => {
  // Must not throw; should use Unknown for city
  assert.doesNotThrow(() => shippingLabel({ name: 'Ada' }));
  assert.match(shippingLabel({ name: 'Ada' }), /Unknown/);
});

test('antibody A57: shippingLabel survives null shipping', () => {
  assert.doesNotThrow(() => shippingLabel({ name: 'Bob', shipping: null }));
  assert.match(shippingLabel({ name: 'Bob', shipping: null }), /Unknown/);
});

test('antibody A57: shippingLabel survives undefined shipping', () => {
  assert.doesNotThrow(() => shippingLabel({ name: 'Carol', shipping: undefined }));
  assert.match(shippingLabel({ name: 'Carol', shipping: undefined }), /Unknown/);
});

test('antibody A57: shippingLabel returns city when shipping is present', () => {
  const label = shippingLabel({ name: 'Ada', shipping: { city: 'York' } });
  assert.match(label, /Ada/);
  assert.match(label, /York/);
});

test('antibody A57: shippingLabel with missing city in shipping object', () => {
  // shipping exists but city is undefined
  assert.doesNotThrow(() => shippingLabel({ name: 'Dave', shipping: {} }));
  assert.match(shippingLabel({ name: 'Dave', shipping: {} }), /Unknown/);
});

// ── Antibody A63: money sums are exact to the cent — no IEEE 754 drift ──────

test('antibody A63: invoiceTotal is exact for every cent value 0.01–0.99', () => {
  // Classic float drift: 0.1 + 0.2 !== 0.3 without integer cents
  assert.equal(invoiceTotal([{ price: 0.1, qty: 1 }, { price: 0.2, qty: 1 }]), 0.3);
  assert.equal(invoiceTotal([{ price: 0.1, qty: 3 }]), 0.3);
  assert.equal(invoiceTotal([{ price: 0.07, qty: 1 }, { price: 0.03, qty: 1 }]), 0.10);
  assert.equal(invoiceTotal([{ price: 0.01, qty: 1 }]), 0.01);
  assert.equal(invoiceTotal([{ price: 0.99, qty: 1 }]), 0.99);
});

test('antibody A63: invoiceTotal exact for cent pairs across full 0.01-0.99 range', () => {
  // Sum of 0.01 + 0.02 + ... + 0.09 = 0.45
  const lines = [];
  for (let i = 1; i <= 9; i++) lines.push({ price: i / 100, qty: 1 });
  assert.equal(invoiceTotal(lines), 0.45);
});

test('antibody A63: invoiceTotal with qty multiplier stays exact', () => {
  assert.equal(invoiceTotal([{ price: 0.1, qty: 3 }]), 0.30);
  assert.equal(invoiceTotal([{ price: 0.33, qty: 3 }]), 0.99);
});

test('antibody A63: taxTotal is exact for every cent value and rate', () => {
  // 0.1 * 0.1 = 0.01 exactly; float drift could give 0.010000000000000002
  assert.equal(taxTotal([{ amount: 0.1 }], 0.1), 0.01);
  assert.equal(taxTotal([{ amount: 0.2 }], 0.5), 0.10);
  assert.equal(taxTotal([{ amount: 0.1 }], 0.3), 0.03);
});

test('antibody A63: taxTotal exact for pairs that drift as floats', () => {
  // 0.1 * 0.2 + 0.1 * 0.1 = 0.02 + 0.01 = 0.03
  assert.equal(
    taxTotal([{ amount: 0.1 }, { amount: 0.1 }], 0.2),
    0.04
  );
});

test('antibody A63: taxTotal with rate 0.2 on typical amounts stays exact', () => {
  assert.equal(taxTotal([{ amount: 19.99 }], 0.2), 4.00);
  assert.equal(taxTotal([{ amount: 0.05 }], 0.2), 0.01);
});
