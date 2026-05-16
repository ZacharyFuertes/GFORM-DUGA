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

def build_name_pool():
    """Create a shuffled pool of (name, gender) tuples. No repeats until pool is exhausted."""
    pool = [(n, "Male") for n in MALE_NAMES] + [(n, "Female") for n in FEMALE_NAMES]
    random.shuffle(pool)
    return pool

async def fill_radiogroups(page, gender=None):
    """Fill all radiogroups. If gender is provided, use it for the 2-option (Male/Female) group."""
    radiogroups = await page.locator('div[role="radiogroup"]').all()
    for rg in radiogroups:
        radios = await rg.locator('div[role="radio"]').all()
        if not radios:
            continue

        if len(radios) == 5:
            # Rating scale: columns go 5 -> 1 left to right
            # index 0 = 5, index 1 = 4, index 2 = 3
            idx = random.choice([0, 1, 2])
            await radios[idx].click()
            await page.wait_for_timeout(random.randint(100, 300))
        elif len(radios) == 2 and gender is not None:
            # Gender question: pick based on the name's gender
            # options are Male (index 0) and Female (index 1)
            idx = 0 if gender == "Male" else 1
            await radios[idx].click()
            await page.wait_for_timeout(random.randint(100, 300))
        else:
            choice = random.choice(radios)
            await choice.click()
            await page.wait_for_timeout(random.randint(100, 300))

async def fill_page1(page, name_pool):
    """Fill page 1: optionally type a name and select gender."""
    use_name = random.random() < 0.5  # 50% chance of filling name
    gender = None

    if use_name and name_pool:
        chosen_name, gender = name_pool.pop()
        # Google Forms renders a visible input[type="text"] for short answer fields
        # The hidden input[name="entry.XXX"] just holds the value — we fill the visible one
        name_input = page.locator('input[type="text"]').first
        count = await name_input.count()
        if count > 0:
            await name_input.click()
            await name_input.fill(chosen_name)
            await page.wait_for_timeout(random.randint(100, 200))
            logging.info(f"  Name: {chosen_name} ({gender})")
    
    await fill_radiogroups(page, gender=gender)

async def submit_form(context, i, count, name_pool):
    page = await context.new_page()
    try:
        await page.goto(FORM_URL)
        await page.wait_for_load_state("networkidle")

        # Page 1: Basic Info (name + gender)
        await fill_page1(page, name_pool)

        # Click Next
        btns = await page.locator('div[role="button"]').all()
        for btn in btns:
            text = await btn.inner_text()
            if "Susunod" in text or "Next" in text:
                await btn.click()
                break
                
        await page.wait_for_timeout(1000)
        
        # Page 2: Part 1
        await fill_radiogroups(page)

        # Click Next
        btns = await page.locator('div[role="button"]').all()
        for btn in btns:
            text = await btn.inner_text()
            if "Susunod" in text or "Next" in text:
                await btn.click()
                break

        await page.wait_for_timeout(1000)

        # Page 3: Part 2
        await fill_radiogroups(page)
        
        # Click Submit
        btns = await page.locator('div[role="button"]').all()
        for btn in btns:
            text = await btn.inner_text()
            if "Isumite" in text or "Submit" in text:
                await btn.click()
                break
                
        await page.wait_for_timeout(2000)
        # Check success
        content = await page.content()
        if "tugon" in content.lower() or "recorded" in content.lower():
            logging.info(f"[{i}/{count}] OK")
            return True
        else:
            await page.screenshot(path=f"playwright_fail_{i}.png", full_page=True)
            logging.warning(f"[{i}/{count}] Failed. Screenshot saved.")
            return False
            
    except Exception as e:
        logging.error(f"[{i}/{count}] Error: {e}")
        return False
    finally:
        await page.close()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=18)
    args = parser.parse_args()
    
    logging.info(f"Starting {args.count} Playwright iterations...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        name_pool = build_name_pool()
        success = 0
        for i in range(1, args.count + 1):
            # Replenish pool if exhausted (only happens if count > 50 names)
            if not name_pool:
                name_pool = build_name_pool()
            res = await submit_form(context, i, args.count, name_pool)
            if res:
                success += 1
            await asyncio.sleep(random.uniform(1.0, 3.0))

        logging.info(f"Complete. Success: {success}/{args.count}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
