# gvsigol_plugin_sysadmin

## Purpose

This plugin adds a **platform console** for **Django superusers**: operational tools that are not aimed at day-to-day dashboard users. It reuses the standard gvSIG Online dashboard chrome (`base.html`, including the usual left-hand menu when the user is staff), but it **does not register a sidebar entry** (there is no `dashboard_sysadmin_menu.html`). Superusers open it by browsing directly to the URL (typically `/<GVSIGOL_PATH>/sysadmin/`, e.g. `/gvsigonline/sysadmin/`).

The console currently groups two areas:

1. **Unit test runner** — discover, filter, and queue test runs for the current deployment.
2. **GolSettings** — operational control over **runtime configuration** stored in the database (see below), as opposed to **static** options that live only in `settings.py` / environment and require a redeploy to change.

---

## Unit tests

**Screen:** `/sysadmin/tests/` (plus the same path prefix as above).

The UI loads a **catalog of tests** discovered from installed apps (Django’s discovery machinery). You can:

- Filter by **whether a test needs a database**, by **topic** (`@tag` / heuristics), and by **search text**.
- Use **presets** (e.g. all visible tests, only no-DB, only DB, or select by app).
- Choose individual tests or whole modules, then **Run selection**.

Runs are executed **asynchronously via Celery**: the worker spawns a subprocess (`manage.py test …`) so the HTTP request is not blocked. Polling shows status, stdout/stderr, and a parsed summary when the run finishes. Only whitelisted labels from the current catalog can be queued; concurrent runs are limited (a new run is rejected while another is pending or running).

Recommended markers in test code: Django `@tag` (e.g. `env`, `geo`, `auth`, `integration`, `no_db`). Whether a test **needs a DB** is inferred from the test class base (`TestCase` / `TransactionTestCase` vs `SimpleTestCase` / `unittest.TestCase`).

Tests that hit the ORM expect a working **Django test database** (in typical gvSIG Online setups the test DB name is `test` with PostGIS).

---

## GolSettings and how values are resolved

**Goal:** Many deployment parameters are **static**: they are read from Django `settings.py` (often fed by environment variables) when the process starts, and changing them means editing config and **redeploying** or restarting workers. **GolSettings** is a complementary mechanism for values that should remain **adjustable while the platform is running**: they are stored as plain text rows in the database, scoped by **`plugin_name`** and **`key`**, and read through `GolSettings.objects.get_value(...)`. Plugins use this for options that operators may need to tune without touching the server filesystem or redeploying.

**Resolution order** (what `get_value(plugin_name, key, default=...)` returns):

1. **Database** — If a row exists for that `plugin_name` and `key`, its `value` field is returned (text as stored).
2. **Plugin defaults dict** — Otherwise, Django imports `<plugin_name>.settings` and looks up optional `GOL_SETTINGS_DEFAULTS`, which must be a mapping. If `key` is present and the entry is not `None`, that value is normalised with `str(...)` (same idea as storing text in the DB) and returned.
3. **Call-site default** — Otherwise the `default` argument passed into `get_value` is returned (typically a constant in the calling code).

Writing with `set_value` persists text in the DB (`str(value)`; `None` is stored as an empty string). That DB layer is the **strongest** precedence: it overrides `GOL_SETTINGS_DEFAULTS` until the row is removed or updated.

**Sysadmin screen** (`/sysadmin/settings/db/`): lists every stored row, supports **create**, **edit/save**, and **delete**. It only changes the database layer; it does not edit `GOL_SETTINGS_DEFAULTS` or `settings.py`. Use it when an operator needs a **runtime override** on top of whatever defaults the plugin ships with or passes as `default=` in code.

---

## Optional settings (reference)

These Django settings tune behaviour of the test runner integration:

- `GVSIGOL_SYSADMIN_TEST_RUN_TIMEOUT` — subprocess time limit in seconds (default 1800).
- `GVSIGOL_SYSADMIN_TEST_OUTPUT_MAX_CHARS` — cap on captured stdout/stderr (default about 1 MiB).
- `GVSIGOL_SYSADMIN_TEST_DISCOVERY_SKIP_APP_NAMES` — extra app name prefixes to skip during discovery.
- `GVSIGOL_SYSADMIN_TEST_DISCOVERY_ONLY_APP_NAMES` — if set, restrict discovery to these apps.
