"""Shared Google Form schema analysis and answer-randomness configuration.

Used by both the Tkinter GUI (gui_launcher.py) and the CLI bot
(gform_bot_playwright.py) so that analyzed data and randomness rules
behave identically in either entry point.
"""

import json
import random
import re

import requests

TYPE_LABELS = {
    0: "Short Text",
    1: "Long Text",
    2: "Multiple Choice",
    3: "Dropdown",
    4: "Checkboxes",
    5: "Linear Scale",
    6: "Date",
    7: "Grid / Matrix",
    8: "Section Header",
    9: "Time",
}

# Question types the bot picks through a div[role="radiogroup"].
RADIO_TYPES = {2, 5, 7}


# ── schema extraction ─────────────────────────────────────────────────────────

def analyze(url):
    """Fetch a Google Form and flatten it into displayable questions and units.

    Returns {"error": ...} on failure, otherwise a dict with:
      title, description, questions, units, reference_options
    """
    try:
        response = requests.get(url, timeout=10)
    except Exception as exc:
        return {"error": str(exc)}

    if response.status_code != 200:
        return {"error": f"Failed to fetch form. Status: {response.status_code}"}

    match = re.search(
        r"var FB_PUBLIC_LOAD_DATA_ = (.*?);</script>", response.text, re.DOTALL
    )
    if not match:
        return {"error": "Could not find form data. Is this a valid Google Form link?"}

    try:
        data = json.loads(match.group(1))
    except Exception as exc:
        return {"error": f"Could not parse form data: {exc}"}

    if not data or len(data) < 2 or data[1] is None:
        return {"error": "Form data structure is invalid."}

    title = data[1][8] if len(data[1]) > 8 else "Untitled Form"
    description = data[1][0] or ""
    questions_list = data[1][1] if len(data[1]) > 1 else []

    questions = []
    units = []

    for q in questions_list:
        if not q or len(q) < 4:
            continue

        label = q[1] or ""
        type_code = q[3]

        entry_id, required = None, False
        try:
            if q[4] and q[4][0]:
                entry_id = q[4][0][0]
                required = bool(q[4][0][2]) if len(q[4][0]) > 2 else False
        except (IndexError, TypeError):
            pass

        rows = _parse_rows(q, type_code)
        questions.append({
            "label": label,
            "type": TYPE_LABELS.get(type_code, f"Unknown ({type_code})"),
            "type_code": type_code,
            "entry_id": f"entry.{entry_id}" if entry_id is not None
                        else "No ID (Header/Info)",
            "required": required,
            "rows": rows,
        })

        if type_code in RADIO_TYPES:
            for row in rows:
                units.append({
                    "index": len(units),
                    "question": label,
                    "label": row["label"] or label,
                    "options": row["options"],
                    "entry_id": row["entry_id"],
                    "required": required,
                })

    return {
        "title": title,
        "description": description,
        "questions": questions,
        "units": units,
        "reference_options": _reference_options(units),
    }


def _parse_rows(question, type_code):
    """Return one entry per answerable row: grid = N rows, plain choice = 1 row."""
    body = question[4] if len(question) > 4 else None
    if not body:
        return []

    if type_code == 5:
        # Linear scale stores [entry_id, [min, max], required].
        row = body[0]
        try:
            low, high = row[1][0], row[1][1]
            return [{
                "entry_id": row[0],
                "label": "",
                "options": [str(v) for v in range(int(low), int(high) + 1)],
            }]
        except (IndexError, TypeError, ValueError):
            return []

    rows = []
    for row in body:
        if not row:
            continue
        try:
            row_entry_id = row[0]
        except IndexError:
            continue

        options = []
        if len(row) > 1 and isinstance(row[1], list):
            for option in row[1]:
                if isinstance(option, list):
                    options.append("" if not option or option[0] is None
                                   else str(option[0]))
                else:
                    options.append(str(option))

        row_label = ""
        try:
            if isinstance(row[3], list) and row[3]:
                row_label = row[3][0] or ""
        except IndexError:
            pass

        rows.append({"entry_id": row_entry_id, "label": row_label,
                     "options": options})

    return rows


def _reference_options(units):
    """The most common option list, used to label the global weights row."""
    best, best_count = [], 0
    for unit in units:
        count = sum(1 for other in units if other["options"] == unit["options"])
        if count > best_count:
            best, best_count = unit["options"], count
    return best


# ── randomness configuration ─────────────────────────────────────────────────

def default_pick(n):
    """Selection rule used when nothing has been customised.

    Kept byte-for-byte equivalent to the original bot behaviour so that an
    untouched config produces exactly the same runs as before.
    """
    if n == 5:
        return random.choice([0, 1, 2])
    if n == 2:
        return random.randint(0, 1)
    return random.randrange(n)


def _fit(weights, n):
    """Resample a weight list onto n options; None when nothing usable."""
    if n <= 0 or not weights:
        return None
    cleaned = [max(0.0, float(w)) for w in weights]
    if len(cleaned) == n:
        out = cleaned
    elif n == 1:
        out = [cleaned[0]]
    else:
        out = [cleaned[round(i * (len(cleaned) - 1) / (n - 1))] for i in range(n)]

    # An all-zero result is unusable: random.choices() would raise on it.
    return out if sum(out) > 0 else None


class AnswerConfig:
    """Global default mode plus per-unit weight overrides.

    mode:
      "default"  untouched -> legacy random rule (unchanged behaviour)
      "uniform"  every option equally likely
      "weighted" use self.weights
    overrides: unit index -> weight list (always wins over mode)
    Empty/zero weights are treated as inherit, so a half-filled config can
    never dead-end the picker.
    """

    MODES = ("default", "uniform", "weighted")

    def __init__(self, mode="default", weights=None, overrides=None):
        self.mode = mode if mode in self.MODES else "default"
        self.weights = _clean_list(weights)
        self.overrides = {
            int(idx): _clean_list(vals) for idx, vals in (overrides or {}).items()
        }

    @property
    def is_untouched(self):
        return self.mode == "default" and not self.overrides

    def resolve(self, idx, n):
        """Return (kind, weights) where kind is default/uniform/weighted."""
        if idx in self.overrides:
            fitted = _fit(self.overrides[idx], n)
            if fitted:
                return "weighted", fitted
        if self.mode == "weighted":
            fitted = _fit(self.weights, n)
            if fitted:
                return "weighted", fitted
            return "uniform", None
        if self.mode == "uniform":
            return "uniform", None
        return "default", None

    def to_dict(self):
        return {
            "mode": self.mode,
            "weights": list(self.weights),
            "overrides": {str(k): list(v) for k, v in self.overrides.items()},
        }

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(data.get("mode", "default"), data.get("weights"),
                   data.get("overrides"))

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)


def _clean_list(values):
    if not values:
        return []
    out = []
    for value in values:
        try:
            out.append(max(0.0, float(value)))
        except (TypeError, ValueError):
            out.append(0.0)
    return out


def make_picker(config):
    """Build pick(unit_index, n_options) -> option index for smart_fill.

    Falls back to the legacy default on any defect (bad config, unusable
    weights, out-of-range result) so a misconfiguration can never abort a run.
    """
    def pick(idx, n):
        if n <= 0:
            return 0

        try:
            kind, weights = config.resolve(idx, n)
        except Exception:
            return default_pick(n)

        if kind == "weighted" and weights:
            try:
                return random.choices(range(n), weights=weights, k=1)[0]
            except Exception:
                return default_pick(n)
        if kind == "uniform":
            return random.randrange(n)
        return default_pick(n)

    return pick
