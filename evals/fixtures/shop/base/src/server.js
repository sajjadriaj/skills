const express = require("express");
const { requireUser } = require("./auth");
const { total } = require("./cart");
const db = require("./db");

const app = express();
app.use(express.json());

app.post("/checkout", requireUser, async (req, res) => {
  const items = await db.cartItems(req.user.id);
  const amount = total(items);
  await db.createOrder(req.user.id, amount);
  res.json({ amount });
});

module.exports = app;
