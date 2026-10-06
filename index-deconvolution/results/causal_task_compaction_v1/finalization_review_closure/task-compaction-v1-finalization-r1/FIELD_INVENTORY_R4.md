# Field inventory, r4 additions (r3's FIELD_INVENTORY.md is unchanged and still governs every other field)

## seal.json (candidate) -- audited against the pinned authority
| field | rule | failure |
|---|---|---|
| file | present | absent -> INCOMPLETE (`seal|seal.json`); every one of the 60 entries is then also missing |
| top level | object with exactly `files`, `sha256` | missing / undeclared field -> INVALID |
| `files` | non-boolean int equal to 60 | INVALID `seal|files` |
| `sha256` | object | INVALID `seal|sha256` |
| `sha256[k]`, k outside the 60 authority paths | not allowed | INVALID `undeclared path` |
| `sha256[k]` value | 64 lowercase hex | INVALID `malformed hash` |
| `sha256[k]` value | equal to the authority's value | INVALID `contradicts the pinned authority` (both modes) |
| authority path absent from candidate | -- | INCOMPLETE `seal entry k` (both modes) |
| data file k | present | absent -> INCOMPLETE `sealed artifact k` |
| data bytes k | SHA-256 equal to the AUTHORITY value | INVALID in normal mode; recorded and bypassed in bypass mode |

Authority: `task-compaction-v1-r1/production/seal.json`, SHA-256 c97e8031..., which must equal the
`production/seal.json` entry of the original output manifest (SHA-256 d6aff053..., pinned in
audit_r4.py); each of its 60 values must equal that manifest's `production/<k>` entry.

## fixtures/FX1_identity.json
| field | rule |
|---|---|
| file | absent -> INCOMPLETE; malformed JSON -> INVALID |
| key set | exactly r3's FX_FIELDS (11 fields): missing / undeclared -> INVALID per field |
| `fixture_id` | str, exactly `"FX1_identity"` (type-exact) |
| `outputs` | exactly `[0,0,1,1]` (type-exact, elementwise path) |
| `transitions` | exactly `[[0,1,2,3]]` |
| `stages` | list of >= 2 int vectors of length 4 in [0,4) |
| `alpha` | int vector of length 4 in [0,4) |
| `K` | non-boolean int >= 1, equal to max(alpha)+1 |
| `decoder` | int vector >= 0 |
| `representatives` | int vector in [0,4) |
| `macro` | list of 1 int vector |
| `strict_rounds` | non-boolean int >= 0 |
| `coarsening` | non-null; one map per stage step; map d has length max(stages[d+1])+1 and values in [0, max(stages[d])] |
Then the inherited `schema_certificate` and the frozen `certificate` (validity, minimality) run;
values beyond schema (decoder, macro, representatives, coarsening, minimality) are judged by the
frozen certificate, not re-derived here.
