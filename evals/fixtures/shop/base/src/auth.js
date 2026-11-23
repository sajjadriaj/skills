function requireUser(req, res, next) {
  if (!req.headers.authorization) return res.status(401).end();
  req.user = { id: req.headers.authorization.slice(7) };
  next();
}
module.exports = { requireUser };
