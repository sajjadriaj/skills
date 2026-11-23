const express = require("express");
const { requireUser } = require("./auth");
const { total } = require("./cart");
const db = require("./db");

const app = express();
app.use(express.json());

app.post("/checkout", requireUser, async (req, res) => {
  const items = await db.cartItems(req.user.id);
  const coupon = req.body.coupon ? await db.couponByCode(req.body.coupon) : null;
  const amount = total(items, coupon);
  await db.createOrder(req.user.id, amount, coupon && coupon.code);
  res.json({ amount });
});

// Admin: create a coupon
app.post("/coupons", async (req, res) => {
  if (req.headers["x-admin-key"] !== process.env.COUPON_ADMIN_KEY) return res.status(403).end();
  const c = await db.createCoupon(req.body.code, req.body.percent);
  res.json(c);
});

module.exports = app;
