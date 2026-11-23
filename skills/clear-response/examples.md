# clear-response examples

## Debug

**Before**

> The heap snapshot shows retained closures from the EventEmitter listeners registered in the request handler; since `on()` is called per request without `off()`, the listener array grows unbounded and GC can't reclaim the captured req/res objects. Also you're on Node 18 which is EOL. Move the subscription to module scope or use `once()`.

**After**

**Gist:** Your server adds a new "listener" (a function waiting for an event) on every request and never removes it, so memory fills up until it crashes.

**Must know:**
- 🟠 The server will keep crashing under load until this is fixed. Every restart only buys time.
- 🟡 Node 18 no longer gets security fixes. Not the cause of this bug, but plan an upgrade.

```
 request ─► handler ─► emitter.on(...)   ◄── added every time
                          │
                          ▼
              listeners: [f, f, f, f, ...]  grows forever
                          │
                          ▼
              memory full ─► crash
```

**Detail:** Each listener holds a closure (a function that keeps references to variables around it), here the `req`/`res` objects, so the garbage collector (automatic memory cleanup) can't free them.

```diff
- app.get('/x', (req, res) => { bus.on('done', () => res.send()) })
+ app.get('/x', (req, res) => { bus.once('done', () => res.send()) })
```

🟠 suspected, not confirmed: verify by watching `bus.listenerCount('done')` climb under load.

## Development

**Before**

> Add a unique partial index on `lower(email)` where `deleted_at IS NULL` and backfill with a dedupe migration before enforcing.

**After**

**Gist:** Make the database itself refuse two accounts with the same email, but clean up existing duplicates first or the change will fail.

**Must know:**
- 🔴 If duplicates exist when you add the rule, the migration fails partway. Run the cleanup first, and back up the users table, because merging duplicate accounts can't be undone.

```
 1. find duplicates ─► 2. merge/delete ─► 3. add unique rule
                                            (DB enforces it)
```

**Detail:** "Unique partial index" = a rule that only applies to some rows; here, only active (not deleted) users, compared case-insensitively via `lower(email)`.

## Planning

**Before**

> Option 1: keep cookies + server sessions in Redis. Option 2: JWT with refresh rotation. JWT is stateless but revocation is hard. Recommend option 1.

**After**

**Gist:** Keep logins stored on the server (sessions) rather than switching to self-contained tokens (JWT); it's simpler and lets you log someone out instantly.

**Must know:**
- 🟠 With JWT, a stolen or leaked token keeps working until it expires. You can't instantly kick a user out without extra machinery.

**Paths:**

```
 now ─┬─► A: server sessions ─► ◆ mobile app later? ─► add tokens
      │                                                for mobile
      │
      └─► B: JWT ─► ◆ need instant logout? ─► add denylist
                                              = sessions again
```

- 🟢 A costs one session store (Redis, an in-memory database). Risk 🟡: store goes down = everyone logged out.
- 🟠 B costs refresh-token rotation logic. Risk 🟠: leaked tokens stay valid until expiry.
- Divergence: if you ship a mobile app later, A forks to adding tokens for mobile only; B was already there.

**Pick:** A. You get instant logout for free, and the mobile fork is cheap to take later.
