import { test } from 'node:test';
import assert from 'node:assert/strict';
import { refundTotal, refundContact } from '../src/refunds.js';

test('refundTotal sums refunds', () => {
  assert.equal(refundTotal([{ amount: 5 }, { amount: 10 }]), 15);
});

test('refundContact returns the customer email', () => {
  assert.equal(refundContact({ contact: { email: 'a@b.example' } }), 'a@b.example');
});
