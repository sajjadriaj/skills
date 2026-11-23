// Cart totals. Prices are integer cents.
function subtotal(items) {
  return items.reduce((sum, it) => sum + it.price * it.qty, 0);
}

// coupon: { percent } or { amountOff } in cents
function total(items, coupon) {
  const sub = subtotal(items);
  if (!coupon) return sub;
  if (coupon.amountOff) return sub - coupon.amountOff;
  return Math.round(sub * (1 - coupon.percent / 100));
}

module.exports = { subtotal, total };
