### 💉 Bug Vaccine: ⚠️ 5 past bugs could come back in this PR

**New code vs. company bug history**
Lines this PR adds match bugs the company has already fixed:

- `src/loyalty.js:5` **#41 Off-by-one in slice end** (invoice-kit): slice() call whose end argument is reduced by 1 — the end index is already exclusive, so this drops the last element
  Suggested fix (the company's own past fix):
  ```diff
  - return entries.slice(from, from + perPage - 1);
  + return entries.slice(from, from + perPage);
  ```
- `src/loyalty.js:9` **#63 Float money math** (invoice-kit): reduce() accumulating a money field via direct property access (lowercase var.field, not Math.round) — float sum without integer-cent conversion
  Suggested fix (the company's own past fix):
  ```diff
  - return entries.reduce((sum, e) => sum + e.amount, 0);
  + const cents = entries.reduce((sum, e) => sum + Math.round(e.amount * 100), 0); return cents / 100;
  ```
- `src/loyalty.js:13` **#57 Missing null guard on nested customer field** (invoice-kit): two-level property access on customer object without optional chaining — crashes if the intermediate object is undefined
  Suggested fix (the company's own past fix):
  ```diff
  - return `Hello ${customer.profile.firstName}`;
  + return `Hello ${customer.profile?.firstName}`;
  ```

Apply every suggested fix, re-run the tests and re-check, in one step:
```
python bugvaccine.py patch . --base <base-branch> --apply
```

**Tests vs. past bugs in the changed files**
0/2 caught. These past bugs could return and no test would notice:

- **#63 Float money math** in `src/refunds.js`: 
  ```diff
  - sum + Math.round(l.amount * 100)
  + sum + l.amount * 100
  ```
- **#57 Missing null guard on nested customer field** in `src/refunds.js`: 
  ```diff
  - customer.contact?.email
  + customer.contact.email
  ```

Suggested: add a test that fails when the change above is applied.
