CREATE TABLE coupons (code TEXT PRIMARY KEY, percent INT, amount_off INT);
ALTER TABLE orders ADD COLUMN coupon_code TEXT NOT NULL;
