// Refunds — added in PR #88.
export function refundTotal(lines) {
  const cents = lines.reduce((sum, l) => sum + Math.round(l.amount * 100), 0);
  return cents / 100;
}

export function refundContact(customer) {
  return customer.contact?.email ?? 'billing@invoice-kit.example';
}
