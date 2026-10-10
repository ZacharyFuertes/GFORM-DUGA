import { defaultPick } from "@gform/core";
import type { BrowserContext, Page } from "playwright-core";
import { buildNamePool, generateEmail, shortValue, MALE_NAMES, FEMALE_NAMES } from "./people.ts";
import type { Name } from "./people.ts";

export type Picker = (idx: number, n: number) => number;
export type EventLevel = "info" | "ok" | "warn" | "err";

export interface SubmissionData {
  name: string | null;
  email: string | null;
  reason: string | null;
  answers: Array<[question: string, choice: string]>;
}

interface SmartFillResult {
  nameWritten: boolean;
  email: string | null;
  answers: Array<[question: string, choice: string]>;
}

/**
 * Dynamically fill every visible field on the current page.
 * Mirrors `smart_fill` from gform_bot_playwright.py.
 */
export async function smartFill(
  page: Page,
  assignedName: string | null,
  nameWritten: boolean,
  pick: Picker | null,
  counter: number[],
): Promise<SmartFillResult> {
  const result: SmartFillResult = {
    nameWritten,
    email: null,
    answers: [],
  };

  const radiogroups = await page.locator('div[role="radiogroup"]').all();
  for (let gi = 0; gi < radiogroups.length; gi++) {
    const rg = radiogroups[gi] as NonNullable<(typeof radiogroups)[number]>;
    const radios = await rg.locator('div[role="radio"]').all();
    if (radios.length === 0) continue;

    const unitIndex = counter[0];
    const n = radios.length;
    let idx: number | undefined;
    if (pick) {
      try {
        idx = pick(unitIndex, n);
      } catch {
        // fall through to default
      }
    }
    if (typeof idx !== "number" || !Number.isInteger(idx) || idx < 0 || idx >= n) {
      idx = defaultPick(n);
    }
    counter[0] = unitIndex + 1;

    const question = ((await rg.getAttribute("aria-label")) ?? "").trim() || `question ${gi + 1}`;
    const option = ((await radios[idx]!.getAttribute("aria-label")) ?? "").trim();
    const choice = shortValue(option, `option ${idx + 1} of ${n}`);
    result.answers.push([question, choice]);

    await radios[idx]!.click();
    await page.waitForTimeout(100 + Math.floor(Math.random() * 201));
  }

  const textInputs = await page.locator('input[type="text"], textarea').all();
  for (const ti of textInputs) {
    if (!(await ti.isVisible())) continue;
    const nameAttr = ((await ti.getAttribute("name")) ?? "").toLowerCase();
    const ariaLabel = ((await ti.getAttribute("aria-label")) ?? "").toLowerCase();

    if (nameAttr.includes("email") || ariaLabel.includes("email")) {
      if (!result.email) {
        const names = MALE_NAMES.concat(FEMALE_NAMES);
        const fakeName = names[Math.floor(Math.random() * names.length)] as string;
        result.email = generateEmail(fakeName);
        await ti.fill(result.email);
      }
    } else if (!result.nameWritten) {
      await ti.fill(assignedName ?? "Test Response");
      result.nameWritten = true;
    } else {
      await ti.fill(`Test Response ${Math.floor(Math.random() * 900) + 100}`);
    }
    await page.waitForTimeout(100 + Math.floor(Math.random() * 201));
  }

  return result;
}

/**
 * One full submission across up to 10 Next pages.
 * Mirrors `submit_form` from gform_bot_playwright.py.
 */
export async function submitForm(
  context: BrowserContext,
  i: number,
  count: number,
  namePool: Name[],
  url: string,
  pick: Picker | null,
  onFail: (message: string) => void,
): Promise<{ ok: boolean; data: SubmissionData }> {
  const page = await context.newPage();
  const submission: SubmissionData = {
    name: null,
    email: null,
    reason: null,
    answers: [],
  };
  const assignedName = namePool.length > 0 ? namePool.pop()![0] : null;

  // Radiogroup numbering persists across Next pages within one submission.
  const unitCounter = [0];

  try {
    await page.goto(url);
    // networkidle can hang on real Google Forms (they keep connections open
    // for long-polling); domcontentloaded + settle is more reliable.
    await page.waitForLoadState("domcontentloaded");
    await page.waitForTimeout(2500);

    // Google Forms ships radios aria-disabled and only enables them once its
    // JS hydrates the page. Give it a short grace window; only if radios stay
    // disabled (and a visible radiogroup exists) fail fast with a clear reason
    // instead of burning ~30s per attempt on click timeouts.
    const hasVisibleRadios = await page.evaluate(() => {
      for (const rg of Array.from(document.querySelectorAll('div[role="radiogroup"]'))) {
        const rect = rg.getBoundingClientRect();
        if (
          (rect.width > 0 && rect.height > 0) &&
          rg.querySelectorAll('div[role="radio"]').length > 0
        ) {
          return true;
        }
      }
      return false;
    });
    if (hasVisibleRadios) {
      try {
        await page.waitForSelector('div[role="radio"]:not([aria-disabled="true"]):visible', {
          timeout: 8000,
        });
      } catch {
        const gate = await page.evaluate(() => {
          const rgs = document.querySelectorAll('div[role="radiogroup"]');
          let disabled = 0;
          for (const rg of Array.from(rgs)) {
            disabled += rg.querySelectorAll('div[role="radio"]').length;
          }
          const text = (document.body?.innerText ?? "").toLowerCase();
          const signIn = /\bsign in\b|\bmag-sign in\b|\biniciar sesi[oó]n\b|\blog in\b/.test(text);
          return { signIn, disabled };
        });
        throw new Error(
          gate.signIn
            ? "form requires sign-in (all options stay disabled until the responder signs in); worker uses an anonymous browser"
            : `all ${gate.disabled} radio options stayed disabled — the form may be closed or gated`,
        );
      }
    }

    const maxPages = 10;
    for (let _p = 0; _p < maxPages; _p++) {
      const step = await smartFill(
        page,
        assignedName,
        submission.name !== null,
        pick,
        unitCounter,
      );
      if (step.nameWritten) submission.name = assignedName;
      if (step.email) submission.email = step.email;
      submission.answers.push(...step.answers);

      const btns = await page.locator('div[role="button"]').all();
      let nextBtn: NonNullable<(typeof btns)[number]> | undefined;
      let submitBtn: NonNullable<(typeof btns)[number]> | undefined;

      for (const btn of btns) {
        const text = (await btn.innerText()).toLowerCase();
        if (text.includes("next") || text.includes("susunod")) nextBtn = btn;
        if (text.includes("submit") || text.includes("isumite")) submitBtn = btn;
      }

      if (submitBtn) {
        await submitBtn.click();
        await page.waitForTimeout(2000);
        break;
      } else if (nextBtn) {
        await nextBtn.click();
        await page.waitForTimeout(1000);
      } else {
        break;
      }
    }

    if (submission.name === null) {
      submission.reason = "no text field found on form";
    }

    const content = await page.content();
    const ok = content.toLowerCase().includes("recorded") || content.toLowerCase().includes("tugon");
    return { ok, data: submission };
  } catch (exc) {
    onFail(
      `[${i}/${count}] FAIL ${assignedName ?? "?"} -> ${
        exc instanceof Error ? exc.message : String(exc)
      }`,
    );
    return { ok: false, data: submission };
  } finally {
    await page.close();
  }
}