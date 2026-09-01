# ETI PREZENSA — API contract

The single source of truth for `eti-dashboard` and `eti-mobile`, which cannot
see this repository. **Generated from the code on 2026-09-01** by reading the
URL resolver and instantiating every serializer — not from the other documents
in this folder, which are prose and can drift.

Re-generate the same way after any serializer change; see
[Keeping this file honest](#keeping-this-file-honest).

---

## Conventions

- **Every path keeps its trailing slash.** Django's `APPEND_SLASH` will redirect
  without one, and a redirect drops the body of a POST.
- **Auth** is `Authorization: Bearer <access>` on everything except
  `login/`, `refresh/` and `verify/`.
- **Admin** means the `EhAdmin` permission: `is_staff` **OR** `role == 'ADMIN'`.
- **Errors** are `{"detail": "<Tetun, displayable as-is>", "code": "<slug>"}`,
  sometimes with extra keys. Show `detail` to the user; branch on `code`.
- Times are `HH:MM:SS`, dates `YYYY-MM-DD`, timestamps ISO-8601 with offset.
- `null` means the server sent JSON null; `""` means an empty string. The two
  are not interchangeable — `obs` is `""` when unset, `rejeita_iha` is `null`.

### Closed value sets

| Field | Values |
|---|---|
| `role` | `ADMIN` · `PROFESSOR` |
| `sexu` | `MANE` · `FETO` · `""` |
| `status` | `PRESENT` · `ABSENT` · `LEAVE` · `MISSION` · `HOLIDAY` |
| `sesaun` | `DADER` (morning) · `LOROKRAIK` (afternoon) |
| `tipu` | `TAMA` (check in) · `FILA` (check out) |
| `kolumna` | `ORAS_DADER_TAMA` · `ORAS_DADER_FILA` · `ORAS_LOROKRAIK_TAMA` · `ORAS_LOROKRAIK_FILA` |
| `rejeita_motivu` | `FOTO_FALSU` · `DISTANSIA_DOOK` · `HOTU_HOTU` · `""` |
| `nivel_edukasaun` | `ENSINU_SEKUNDARIU` · `DIPLOMA` · `FINALISTA` · `UNIVERSITARIA` · `BACHARELATU` · `LICENCIADO` · `POST_GRADUACAO` · `MESTRADO` · `DOUTORAMENTU` · `""` |

Stored values are English; the `*_display` twin carries the Tetun label a user
reads. Never show a stored value.

---

## 1. Auth

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/login/` | no |
| POST | `/api/auth/refresh/` | no |
| POST | `/api/auth/verify/` | no |
| POST | `/api/auth/logout/` | yes |
| GET · PATCH | `/api/auth/me/` | yes |
| POST | `/api/auth/troka-password/` | yes |

**`POST /api/auth/login/`** — `{email, password}` → `{access, refresh, user}`,
where `user` is the [profile object](#profile-object). Access tokens last
15 minutes, refresh 30 days with rotation, so a refresh returns a **new**
refresh token that must replace the stored one.

Rate limited per client IP (`THROTTLE_LOGIN`, default `20/min`) — the whole
school shares one public address, so this budget is shared.

| Status | code | Meaning |
|---|---|---|
| 401 | — | wrong credentials, or the account is `is_active=false` |
| 429 | `login_barak_liu` | rate limit; `Retry-After` header carries the seconds |

**`POST /api/auth/logout/`** — `{refresh}` → 205 `{detail}`. 400 `token_not_valid`
if already blacklisted. Cannot revoke an access token already issued (≤15 min).

**`GET /api/auth/me/`** → the [profile object](#profile-object).
**`PATCH /api/auth/me/`** — multipart, field `foto` **required**; every other
field is ignored. Returns the full profile. `PUT` → 405.

**`POST /api/auth/troka-password/`** — `{password_tuan, password_foun, password_konfirma}`
→ `{detail, sesaun_taka, access, refresh}`.

Two client obligations: **store the returned pair** (every other session is
revoked, including this one's old tokens), and **tell the user their other
devices are signed out**.

| Status | code |
|---|---|
| 403 | `password_tuan_sala` |
| 400 | `password_la_hanesan` · `password_hanesan_tuan` · `password_fraku` · `password_presiza` |

### Profile object

`UserSerializer` — returned by `login`, `me`, and nested nowhere else.

```jsonc
{
  "id": 1, "numeru_id": 6, "email": "x@eti-dili.tl",
  "naran_kompletu": "Martinho Martins", "kargu": "Chefe Dep. TLP",
  "foto": "http://host/media/fotos/<uuid>.jpg",   // never null — see below
  "role": "PROFESSOR", "role_display": "Professór",
  "nivel_edukasaun": "LICENCIADO", "nivel_edukasaun_display": "Licenciado",
  "area_estudu": "Gestão Informática", "disiplina_hanorin": "Matematika"
}
```

**`foto` is never `null`.** An account with no photo of its own resolves to the
shared placeholder `…/media/fotos/default.jpg`. Clients may still keep their own
bundled fallback for offline use, but they no longer need one to avoid a gap.

---

## 2. Roster — admin only

| Method | Path |
|---|---|
| GET · POST | `/api/profesor/` |
| GET · PATCH · DELETE | `/api/profesor/{id}/` |
| POST | `/api/profesor/{id}/reset-password/` |

**`GET`** returns a bare array (no pagination) of roster rows: the profile object
**plus** `sexu`, `nu_kontaktu`, `is_active`. Includes **ADMIN accounts and
deactivated ones** — the director keeps a sheet like everyone else.

**`POST`** body: `numeru_id`, `naran_kompletu`, `email` (all required),
`kargu`, `nu_kontaktu`, `sexu`, `nivel_edukasaun`, `area_estudu`,
`disiplina_hanorin` (optional). → 201, roster row **plus `password_inisial`**,
shown once and never retrievable again.

**`PATCH`** takes any subset of the above plus `is_active`.

**`DELETE`** body `{password}` — the caller's own password. Irreversible:
cascades every sheet, day and punch, and deletes their photo files. The shared
placeholder is never deleted.

| Status | code | Applies to |
|---|---|---|
| 400 | `duplicate_numeru` · `duplicate_email` | POST, PATCH |
| 403 | `rasik` | DELETE / reset-password / deactivate **on yourself** |
| 403 | `eh_admin` | the same three **on another admin** |
| 403 | `password_sala` · 400 `password_presiza` | DELETE |
| 400 | `password_la_hanesan` · `password_fraku` | reset-password |

---

## 3. The teacher's own attendance — mobile

| Method | Path | Auth |
|---|---|---|
| GET | `/api/prezensa/ohin/` | yes |
| POST | `/api/prezensa/checkin/` | yes |
| POST | `/api/prezensa/checkout/` | yes |
| GET | `/api/prezensa/istoria/` | yes |
| GET | `/api/prezensa/` · `/api/prezensa/{id}/` | yes — self-scoped, no consumer |

**`GET /api/prezensa/ohin/`** → a [day object](#day-object) plus five extra keys:
`sesaun`, `oras_tama`, `oras_fila`, `bele_checkin`, `bele_checkout`. Creates
today's row on first access. The two `bele_*` booleans are what the buttons
should obey — do not re-derive them on the client.

**`POST /api/prezensa/checkin/` · `checkout/`** — **multipart**:

| Field | Type | Required |
|---|---|---|
| `foto` | image file | **yes** |
| `latitude` · `longitude` | decimal | **yes** |
| `presizaun` | float, metres | no |
| `sesaun` | `DADER`/`LOROKRAIK` | no — server decides from its clock |

→ 201: the same shape as `ohin/`, **plus `marka_foun`** (the punch just made,
a [punch object](#punch-object)).

More decimal places than six are **rounded, not rejected** — send what the GPS
gives you.

| Status | code | Meaning |
|---|---|---|
| 400 | `duplicate` | that session already has this punch. **Treat as success** — the punch exists |
| 400 | `no_checkin` | check out without a check in for that session |
| 400 | `no_session` | Saturday afternoon; the sheet has none |
| 400 | `dook_husi_eskola` | outside the geofence. Carries `distansia` in metres |

**`GET /api/prezensa/istoria/`** — `?fulan=&tinan=&semana=` (all optional;
`?profesor=<id>` is admin-only). Returns every working day of the month, marked
or not:

```jsonc
{ "profesor": "Martinho Martins", "kargu": "…",
  "fulan": 8, "fulan_display": "Agostu", "tinan": 2026, "semana": null,
  "rezumu": { "loron_servisu": 26, "marka_ona": 20, "seidauk_marka": 6,
              "marka_total": 74, "atrazadu": 3 },
  "loron": [ /* day objects, each with extra "semana" and "sabadu" */ ] }
```

An unmarked day has `id: null`, `status: null` and `marka: []`.

| Status | code |
|---|---|
| 400 | `invalid_period` · `invalid_profesor` |
| 403 | `?profesor=` used by a non-admin |

---

## 4. Whole-school reports — admin only

| Method | Path |
|---|---|
| GET | `/api/prezensa/ohin-hotu/` |
| GET | `/api/prezensa/hotu/` |

**`ohin-hotu/`** → `{data, loron, rezumu:{total, marka_ona, seidauk_marka},
profesor:[{profesor, prezensa, marka_ona}]}`. Teachers who have not punched are
included with `prezensa: null` — that absence is the point of the screen.

**`hotu/`** → `?data=YYYY-MM-DD` for one day, otherwise `?fulan=&tinan=&semana=`.
Rows are teacher-major then date-ascending, each carrying its own `data`.
`?marka=false` omits nested punches for a lighter first load. `?profesor=<id>`
narrows to one teacher and **400 `invalid_profesor`** if the id matches nobody.

⚠️ **Neither endpoint is paginated.** A month across the full staff is roughly
*teachers × working days* rows.

---

## 5. Hand-written days — admin only

**`POST /api/prezensa/status/`** — `{profesor, status, husi, too, obs?}` →
201 `{detail, profesor, status, husi, too, loron[], total}`.

Writes `status` **and the same `obs`** to every non-Sunday day in the range.
`status` may **not** be `PRESENT` — presence may only come from a punch.

**`DELETE /api/prezensa/status/`** — `{profesor, data}` → 204. Returns the day to
"no record" by deleting the row.

| Status | code |
|---|---|
| 400 | `invalid_profesor` · `invalid_period` |
| 400 | `iha_marka` — a day in the range already holds punches; **the whole request is refused** and `loron[]` lists the offending dates |
| 404 | DELETE on a day with no row |

---

## 6. Rejecting a day's evidence — admin only

**`POST /api/prezensa/{id}/rejeita/`** — JSON:

| Field | Type | Required | Notes |
|---|---|---|---|
| `motivu` | `FOTO_FALSU` · `DISTANSIA_DOOK` · `HOTU_HOTU` | **yes** | |
| `obs` | string | no, default `""` | the administrator's note |
| `marka` | integer | no | **validated then discarded** — see below |

→ 200, the full [day object](#day-object) with the rejection fields populated.

**`DELETE /api/prezensa/{id}/rejeita/`** → 200, the day object with them cleared.
Only a day *this endpoint* rejected can be restored, so a `LEAVE` day written
through `/status/` cannot be flipped to `PRESENT` through the wrong door.

| Status | code | Meaning |
|---|---|---|
| 400 | `la_iha_marka` | POST on a day with no punches. Use `/status/` for a hand-written absence |
| 400 | `marka_seluk` | the `marka` id does not belong to this day |
| 400 | `la_rejeita` | DELETE on a day that was never rejected |
| 403 | — | not an admin |
| 404 | — | no day with that id |

### What rejection actually does — read this before building UI

Verified against the running code, because it differs from how the feature is
often described:

1. **It is a property of the day, not of one punch.** `status` becomes `ABSENT`
   and the four `rejeita_*` fields are set on the **day**. The printed sheet has
   one status column per day, and the report aggregates per day.
2. **`marka` in the request is advisory only.** It is checked to belong to the
   day and then **never stored**. Nothing on the punch records that it was the
   one objected to, and no response field reflects it.
3. **Punch rows are untouched.** `Marka` has twelve fields and **none** records
   rejection: `id, prezensa, sesaun, tipu, oras, rejistu_iha, foto, latitude,
   longitude, presizaun, distansia_metru, iha_eskola`. There is no
   soft-invalidation flag.
4. **The slot does NOT reopen.** The punch survives, so a second punch for the
   same `(sesaun, tipu)` is refused with **`duplicate`**. Observed directly:

   ```
   rejeita -> 200   status=ABSENT   marka still present=1
   teacher punches that slot again -> REFUSED  code='duplicate'
   ```

   A rejected day therefore **cannot** be re-punched by the teacher. Any client
   that offers "punch again" after a rejection will produce a `duplicate` error.

> **OPEN QUESTION — not a documented behaviour.** The feature is sometimes
> described as "the slot reopens so the teacher can punch again", with the punch
> soft-invalidated. The code does none of that. Either the description or the
> code is wrong; this file records the code. Resolve before building client UI
> that depends on re-punching.

### Rejection fields on the day object

| Key | Type | When not rejected |
|---|---|---|
| `rejeita_motivu` | `FOTO_FALSU` · `DISTANSIA_DOOK` · `HOTU_HOTU` · `""` | `""` |
| `rejeita_motivu_display` | string \| null — the Tetun label | `null` |
| `rejeita_obs` | string | `""` |
| `rejeita_husi_naran` | string \| null — the admin's full name | `null` |
| `rejeita_iha` | ISO timestamp \| null | `null` |

**Renamed 2026-09-01.** Was `rejeisaun_motivu`, `rejeisaun_obs` and
`rejeisaun_motivu_display`. A hard cutover: the old keys are **no longer sent**.

`!!rejeita_motivu` is the single check for "is this day rejected". A rejected
day is `ABSENT` like any other absence, so this is the only thing separating the
two — badge it distinctly or the two become indistinguishable.

---

## 7. Punch photos

**`GET /api/marka/{id}/foto/`** — streams the image, `Content-Disposition:
attachment` with a readable filename. A teacher may fetch their own; an admin
anyone's.

| Status | code |
|---|---|
| 403 | `la_iha_permisaun` |
| 404 | `foto_lakon` — the row survives but the file is gone |

Prefer `foto_download` from the [punch object](#punch-object) over the raw
`foto` URL: it checks the token, and `MEDIA_ROOT` should not be public.

---

## 8. Configuration

**`GET /api/konfig/`** (any authenticated user) →

```jsonc
{ "nivel_edukasaun": [{"value","label"}], "area_estudu_sujere": ["…"],
  "sexu": [{"value","label"}],
  "oras_dader_tama": "08:00:00", "oras_dader_fila": "12:00:00",
  "oras_lorokraik_tama": "13:30:00", "oras_lorokraik_fila": "17:30:00",
  "limite_sesaun": "13:00:00",
  "eskola_raiu_metru": 100.0, "eskola_obriga_fatin": true }
```

Build pickers from this, not from a hardcoded list. The school's coordinates are
deliberately **not** served.

---

## 9. Monthly sheets

**`GET /api/lista-prezensa/`** · **`/{id}/`** — self-scoped.
`{id, profesor, kargu, fulan, fulan_display, tinan, prezensa: [day objects]}`.
`kargu` is **frozen** at the month the sheet was issued, so it may differ from
the teacher's current one. That is correct, not drift.

---

## Shared objects

### Day object

`PrezensaSerializer` — every key, in serializer order. All read-only.

| Key | Type |
|---|---|
| `id` | integer |
| `profesor` | string — the teacher's name |
| `data` | date |
| `loron` | string — Tetun weekday |
| `oras_dader_tama` · `oras_dader_fila` · `oras_lorokraik_tama` · `oras_lorokraik_fila` | time \| null |
| `status` | see closed sets |
| `status_display` | string — Tetun label |
| `obs` | string |
| `rejeita_motivu` · `rejeita_motivu_display` · `rejeita_obs` · `rejeita_husi_naran` · `rejeita_iha` | [above](#rejection-fields-on-the-day-object) |
| `marka` | array of punch objects |

The four `oras_*` keys are **derived from the punches, not stored**. Do not
expect a column of that name in any export or query.

### Punch object

`MarkaSerializer`. All read-only.

| Key | Type |
|---|---|
| `id` | integer |
| `sesaun` · `sesaun_display` | string |
| `tipu` · `tipu_display` | string |
| `kolumna` | which cell of the printed grid |
| `oras` | time — **server** clock, not the device |
| `oras_orariu` | time — the scheduled time for that cell |
| `atrazadu` | boolean on a `TAMA`, **null on a `FILA`** |
| `rejistu_iha` | timestamp |
| `foto` | raw MEDIA URL |
| `foto_download` | authenticated URL — prefer this |
| `naran_foto_download` | suggested filename |
| `latitude` · `longitude` | decimal string |
| `presizaun` | float \| null — device accuracy, never trusted for the geofence |
| `distansia_metru` | float \| null — from the school |
| `iha_eskola` | boolean \| null — null when no coordinates are configured |

---

## Keeping this file honest

```bash
python manage.py shell -c "
from attendance import serializers as s
print(list(s.PrezensaSerializer().fields))"
```

If that list and the [day object](#day-object) table disagree, this file is
wrong and the code is right.

## Not in this contract

- **No pagination anywhere.** Every list is a bare array.
- **No WebSocket or push.** Clients poll.
- **No student, course or lecture endpoints.** This API is staff attendance only.
