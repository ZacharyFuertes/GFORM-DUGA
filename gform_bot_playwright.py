import asyncio
import random
import argparse
import logging
from collections import Counter, defaultdict
from datetime import datetime
from playwright.async_api import async_playwright

from form_schema import AnswerConfig, default_pick, make_picker

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeXyKpROVhz6hnbLiNWpiSStdk-mGtFUnx9IG-juDXVCzovAg/viewform?usp=dialog"

MALE_NAMES = [
    "Jose Miguel Reyes", "Juan Carlos Santos", "Rafael Angelo Cruz",
    "Miguel Antonio Garcia", "Carlos Eduardo Bautista", "Angelo Luis Mendoza",
    "Pedro Javier Rodriguez", "Roberto Emilio Aquino", "Francisco Dela Cruz",
    "Andres Paolo Lopez", "Nathaniel Reyes", "Joshua Miguel Santos",
    "Adrian Cruz", "Matthew Garcia", "Lorenzo Bautista", "Gabriel Mendoza",
    "Rafael Santos", "Daniel Aquino", "Kenneth Dela Cruz", "Vincent Rodriguez",
    "Marco Fernandez", "Luis Morales", "Ramon Villanueva", "Diego Ramos",
    "Samuel Gonzales"
]

FEMALE_NAMES = [
    "Maria Elena Reyes", "Ana Patricia Santos", "Sophia Isabel Cruz",
    "Cristina Mae Garcia", "Beatriz Angela Bautista", "Andrea Nicole Mendoza",
    "Jasmine Reyes", "Katrina Santos", "Isabella Cruz", "Angelica Lopez",
    "Patricia Aquino", "Daniela Fernandez", "Sophia Morales", "Mikaela Dela Cruz",
    "Alessandra Rodriguez", "Lauren Bautista", "Hannah Garcia", "Nicole Villanueva",
    "Samantha Ramos", "Adrienne Gonzales", "Julia Perez", "Camille Torres",
    "Francesca Rivera", "Mariel Santos", "Bianca Mendoza"
]

DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]

def build_name_pool():
    """Create a shuffled pool of (name, gender) tuples. No repeats until pool is exhausted."""
    pool = [(n, "Male") for n in MALE_NAMES] + [(n, "Female") for n in FEMALE_NAMES]
    random.shuffle(pool)
    return pool

def generate_email(name):
    """Generate a realistic email based on a name."""
    clean_name = name.lower().replace(" ", ".")
    domain = random.choice(DOMAINS)
    suffix = random.choice(["", str(random.randint(1, 99))])
    return f"{clean_name}{suffix}@{domain}"

def short_value(label, fallback):
    """Radio aria-labels repeat the whole question; keep only the leading value."""
    head = (label or "").split(",")[0].strip()
    return head or fallback

def summarize_answers(answers):
    """Collapse [(question, value), ...] into a 'v, v, v' list. No truncation."""
    values = [v for _, v in answers]
    return ", ".join(values) if values else "no answers"

def _as_number(value):
    """Return value as a float, or None when it is not a plain number."""
    try:
        return float(str(value).strip().split(",")[0])
    except (TypeError, ValueError):
        return None

class RunStats:
    """Accumulates per-run counts so the whole batch can be summarized at the end."""

    def __init__(self):
        self.total = 0
        self.success = 0
        self.failed = 0
        self.errors = 0
        self.names = []
        self.answers = Counter()
        self.per_question = defaultdict(list)

    def record(self, ok, name, answers, error=False):
        self.total += 1
        if ok:
            self.success += 1
        else:
            self.failed += 1
        if error:
            self.errors += 1
        if name:
            self.names.append(name)
        for qi, (_, value) in enumerate(answers or [], 1):
            self.answers[value] += 1
            self.per_question[qi].append(value)

    @staticmethod
    def _pct(part, whole):
        return f"{(part / whole * 100):.1f}%" if whole else "-"

    def table(self):
        """Build the end-of-run report as a list of (line, is_heading) pairs."""
        W = 46
        rule = "-" * W
        out = [(rule, True), ("  RUN SUMMARY", True), (rule, True), ("", False)]

        out.append((f"  {'Submissions':<16}{self.total:>6}", False))
        out.append((f"  {'Submitted':<16}{self.success:>4}  "
                    f"{self._pct(self.success, self.total):>6}", False))
        out.append((f"  {'Failed':<16}{self.failed:>4}  "
                    f"{self._pct(self.failed, self.total):>6}", False))
        if self.errors:
            out.append((f"  {'Errors':<16}{self.errors:>6}", False))
        out.append((f"  {'Unique names':<16}{len(set(self.names)):>6}", False))

        total_answers = sum(self.answers.values())
        per_run = f"{total_answers / self.total:.1f}" if self.total else "-"
        out.append((f"  {'Answers logged':<16}{total_answers:>6}   "
                    f"({per_run}/run)", False))
        out.append(("", False))

        out.append(("  ANSWER DISTRIBUTION", True))
        if not total_answers:
            out.append(("    no answers recorded", False))
        for value, n in self.answers.most_common():
            label = str(value)[:20]
            out.append((f"    {label:<20}{n:>6}  "
                        f"{self._pct(n, total_answers):>6}", False))
        out.append(("", False))

        numeric = {qi: [_as_number(v) for v in vals]
                   for qi, vals in self.per_question.items()}
        numeric = {qi: vals for qi, vals in numeric.items()
                   if vals and all(v is not None for v in vals)}
        if numeric:
            out.append(("  AVERAGE PER QUESTION", True))
            cells = [f"Q{qi} {sum(vals) / len(vals):.2f}"
                     for qi, vals in sorted(numeric.items())]
            for i in range(0, len(cells), 3):
                out.append(("    " + "   ".join(cells[i:i + 3]), False))
            out.append(("", False))

        out.append((rule, True))
        return out

async def smart_fill(page, assigned_name, name_written, pick=None, counter=None):
    """Dynamically find and fill all visible fields on the current page.

    pick(unit_index, n_options) -> option index comes from AnswerConfig and
    lets the user drive submission randomness. counter is the running index of
    radiogroups across the whole submission; the original selection rule is
    used whenever pick is absent or returns nothing usable.
    """
    data_used = {"name_written": name_written, "email": None, "answers": []}
    
    # Find all radio groups (Linear Scale / Multiple Choice / Grid)
    radiogroups = await page.locator('div[role="radiogroup"]').all()
    
    for gi, rg in enumerate(radiogroups, 1):
        radios = await rg.locator('div[role="radio"]').all()
        if not radios: continue

        unit_index = 0 if counter is None else counter[0]
        n = len(radios)
        idx = None
        if pick is not None:
            try:
                idx = pick(unit_index, n)
            except Exception as exc:
                logging.warning("picker failed at unit %d (%s); using default",
                                unit_index, exc)
        if not isinstance(idx, int) or not 0 <= idx < n:
            idx = default_pick(n)
        if counter is not None:
            counter[0] = unit_index + 1

        question = (await rg.get_attribute("aria-label") or "").strip() or f"question {gi}"
        option = (await radios[idx].get_attribute("aria-label") or "").strip()
        choice = short_value(option, f"option {idx + 1} of {n}")
        data_used["answers"].append((question, choice))

        await radios[idx].click()
        await page.wait_for_timeout(random.randint(100, 300))


    # Find all text inputs
    text_inputs = await page.locator('input[type="text"], textarea').all()
    for ti in text_inputs:
        if await ti.is_visible():
            name_attr = (await ti.get_attribute("name") or "").lower()
            aria_label = (await ti.get_attribute("aria-label") or "").lower()
            
            # Email detection
            if "email" in name_attr or "email" in aria_label:
                if not data_used["email"]:
                    fake_name = random.choice(MALE_NAMES + FEMALE_NAMES)
                    data_used["email"] = generate_email(fake_name)
                    await ti.fill(data_used["email"])
            # Name detection or generic
            elif not data_used["name_written"]:
                await ti.fill(assigned_name)
                data_used["name_written"] = True
            else:
                await ti.fill(f"Test Response {random.randint(100, 999)}")
            await page.wait_for_timeout(random.randint(100, 300))
    return data_used

async def submit_form(context, i, count, name_pool, url, pick=None):
    page = await context.new_page()
    submission_data = {"name": None, "email": None, "reason": None, "answers": []}
    assigned_name, _ = name_pool.pop() if name_pool else (None, None)
    # Radiogroup numbering persists across Next pages within this submission.
    unit_counter = [0]
    try:
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        max_pages = 10 
        for _ in range(max_pages):
            step_data = await smart_fill(page, assigned_name,
                                         submission_data["name"] is not None,
                                         pick, unit_counter)
            if step_data["name_written"]:
                submission_data["name"] = assigned_name
            if step_data["email"]:
                submission_data["email"] = step_data["email"]
            submission_data["answers"].extend(step_data["answers"])
            
            btns = await page.locator('div[role="button"]').all()
            next_btn = None
            submit_btn = None
            
            for btn in btns:
                text = (await btn.inner_text()).lower()
                if "next" in text or "susunod" in text:
                    next_btn = btn
                if "submit" in text or "isumite" in text:
                    submit_btn = btn
            
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(2000)
                break
            elif next_btn:
                await next_btn.click()
                await page.wait_for_timeout(1000)
            else:
                break

        if submission_data["name"] is None:
            submission_data["reason"] = "no text field found on form"

        content = await page.content()
        ok = "recorded" in content.lower() or "tugon" in content.lower()
        label = submission_data["name"] or submission_data["reason"]
        summary = summarize_answers(submission_data["answers"])
        logging.info("[%d/%d] %s %s -> %s",
                     i, count, "OK  " if ok else "FAIL", label, summary)
        return ok, submission_data

    except Exception as e:
        logging.error("[%d/%d] FAIL %s -> %s", i, count, assigned_name or "?", e)
        return False, submission_data
    finally:
        await page.close()

async def main():
    parser = argparse.ArgumentParser(
        description="Google Form automation bot",
        epilog="Without --config the original random selection is used.",
    )
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--url", type=str, required=True)
    parser.add_argument(
        "--config", type=str, default=None, metavar="FILE",
        help="JSON answer config from the GUI (answer_config.json) "
             "controlling submission randomness",
    )
    parser.add_argument(
        "--save-config", type=str, default=None, metavar="FILE",
        help="Write the default answer config to FILE as a starting point",
    )
    args = parser.parse_args()

    if args.save_config:
        AnswerConfig().save(args.save_config)
        logging.info("Wrote default answer config to %s", args.save_config)

    config = AnswerConfig()
    if args.config:
        try:
            config = AnswerConfig.load(args.config)
        except Exception as exc:
            logging.error("Could not read config %s (%s); using defaults.",
                          args.config, exc)
    picker = make_picker(config)

    mode = "default" if config.is_untouched else config.mode
    logging.info("Starting %d iterations on %s (randomness: %s, overrides: %d)...",
                 args.count, args.url, mode, len(config.overrides))
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        name_pool = build_name_pool()
        stats = RunStats()
        for i in range(1, args.count + 1):
            if not name_pool:
                name_pool = build_name_pool()
            ok, data = await submit_form(context, i, args.count, name_pool,
                                         args.url, pick=picker)
            stats.record(ok, data.get("name"), data.get("answers"))
            await asyncio.sleep(random.uniform(1.0, 3.0))

        for line, _ in stats.table():
            logging.info("%s", line)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
