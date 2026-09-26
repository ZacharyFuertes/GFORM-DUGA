import asyncio
import random
import argparse
import logging
from datetime import datetime
from playwright.async_api import async_playwright

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

async def smart_fill(page, assigned_name, name_written):
    """Dynamically find and fill all visible fields on the current page."""
    data_used = {"name_written": name_written, "email": None, "answers": []}
    
    # Find all radio groups (Linear Scale / Multiple Choice / Grid)
    radiogroups = await page.locator('div[role="radiogroup"]').all()
    
    for gi, rg in enumerate(radiogroups, 1):
        radios = await rg.locator('div[role="radio"]').all()
        if not radios: continue
        
        if len(radios) == 5: # Rating 1-5
            idx = random.choice([0, 1, 2]) # 5, 4, 3
        elif len(radios) == 2: # Potential Gender or Binary
            idx = random.randint(0, 1)
        else:
            idx = random.randrange(len(radios))

        question = (await rg.get_attribute("aria-label") or "").strip() or f"question {gi}"
        option = (await radios[idx].get_attribute("aria-label") or "").strip()
        choice = option or f"option {idx + 1} of {len(radios)}"
        data_used["answers"].append((question, choice))
        logging.info("  Q%-3d %s -> %s", gi, question, choice)

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
                    email = generate_email(fake_name)
                    data_used["email"] = email
                    await ti.fill(email)
                    logging.info(f"  Filled email: {email}")
            # Name detection or generic
            elif not data_used["name_written"]:
                await ti.fill(assigned_name)
                data_used["name_written"] = True
                logging.info(f"  Filled name field with: {assigned_name}")
            else:
                await ti.fill(f"Test Response {random.randint(100, 999)}")
            await page.wait_for_timeout(random.randint(100, 300))
    return data_used

async def submit_form(context, i, count, name_pool, url):
    page = await context.new_page()
    submission_data = {"name": None, "email": None, "reason": None, "answers": []}
    assigned_name, _ = name_pool.pop() if name_pool else (None, None)
    try:
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        max_pages = 10 
        for _ in range(max_pages):
            step_data = await smart_fill(page, assigned_name, submission_data["name"] is not None)
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
        if "recorded" in content.lower() or "tugon" in content.lower():
            logging.info(f"[{i}/{count}] OK")
            return True, submission_data
        return False, submission_data
            
    except Exception as e:
        logging.error(f"[{i}/{count}] Error: {e}")
        return False, submission_data
    finally:
        await page.close()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--url", type=str, required=True)
    args = parser.parse_args()
    
    logging.info(f"Starting {args.count} iterations on {args.url}...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        name_pool = build_name_pool()
        success = 0
        for i in range(1, args.count + 1):
            if not name_pool:
                name_pool = build_name_pool()
            res = await submit_form(context, i, args.count, name_pool, args.url)
            if res:
                success += 1
            await asyncio.sleep(random.uniform(1.0, 3.0))

        logging.info(f"Complete. Success: {success}/{args.count}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
