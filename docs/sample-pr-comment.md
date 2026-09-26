### 💉 Bug Vaccine: ⚠️ 5 past bugs could come back in this PR

**New code vs. company bug history**
Lines this PR adds match bugs the company has already fixed:

- `src/loyalty.js:5` **#41 Off-by-one in slice end** (invoice-kit): slice() end adjusted by 1: check that full pages keep their last item
  ```
  return entries.slice(from, from + perPage - 1);
  ```
  How it was fixed before: The end index of slice() is exclusive, so use slice(start, start + size) with no - 1.
- `src/loyalty.js:9` **#63 Float money math** (invoice-kit): money summed as floating-point numbers instead of integer cents
  ```
  return entries.reduce((sum, e) => sum + e.amount, 0);
  ```
  How it was fixed before: Convert to integer cents first: Math.round(price * 100) * qty, sum the cents, and divide by 100 once at the end.
- `src/loyalty.js:13` **#57 Missing null guard on nested customer field** (invoice-kit): nested customer field read without a null guard (?.)
  ```
  return `Hello ${customer.profile.firstName}`;
  ```
  How it was fixed before: Customers imported from other systems can lack nested objects. Use optional chaining with a default: customer.address?.city ?? 'Unknown'.

**Tests vs. past bugs in the changed files**
0/2 caught. These past bugs could return and no test would notice:

- **#63 Float money math** in `src/refunds.js`: New refundTotal() sums money: the #63 float bug would go unnoticed here
  ```diff
  - const cents = lines.reduce((sum, l) => sum + Math.round(l.amount * 100), 0);
  + return lines.reduce((sum, l) => sum + l.amount, 0);
  ```
- **#57 Missing null guard on nested customer field** in `src/refunds.js`: New refundContact() reads a nested customer field: the #57 crash would go unnoticed here
  ```diff
  - customer.contact?.email ?? 'billing@invoice-kit.example'
  + customer.contact.email
  ```
  Past incident: `docs/postmortems/2026-04-invoice-run-crash.md`

Suggested: add a test that fails when the change above is applied.
