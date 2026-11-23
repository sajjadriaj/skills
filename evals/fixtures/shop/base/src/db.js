// Thin wrapper over the orders/carts tables (stubbed).
module.exports = {
  cartItems: async (userId) => [],
  createOrder: async (userId, amount) => ({ userId, amount }),
  couponByCode: async (code) => null,
  createCoupon: async (code, percent) => ({ code, percent }),
};
