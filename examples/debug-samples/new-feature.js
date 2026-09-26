// Sample: a new "loyalty statement" feature a developer just wrote.
// It repeats two bugs the company has already fixed elsewhere.
export function statementPage(entries, pageNo, perPage) {
  const from = pageNo * perPage;
  return entries.slice(from, from + perPage - 1);
}

export function statementTotal(entries) {
  return entries.reduce((sum, e) => sum + e.amount, 0);
}

export function greeting(customer) {
  return `Hello ${customer.profile.firstName}`;
}
