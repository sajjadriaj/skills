// Cart totals. Prices are integer cents.
function subtotal(items) {
  return items.reduce((sum, it) => sum + it.price * it.qty, 0);
}

function total(items) {
  return subtotal(items);
}

module.exports = { subtotal, total };
