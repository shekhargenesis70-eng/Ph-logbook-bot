#!/usr/bin/env python3
"""
BLDE PG Logbook Automation Bot
MD Radio-Diagnosis – Day-to-Day Activities
Dec 5 2025 → Feb 27 2026  |  85 entries total
"""

import os, sys, time, random
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── Config ────────────────────────────────────────────────────────────────────
USER    = os.environ.get("LB_USER", "S240128")
PASS    = os.environ.get("LB_PASS", "")
BASE    = "https://myapp.in/pglogbook"
DRY_RUN = os.environ.get("DRY_RUN", "preview") == "preview"

# Faculty code → name map
FACULTY = [
    "E250131",   # DR Vishal N S
    "E250248",   # DR Tejas Halkude
    "E250176",   # DR SIDDAROODHA SAJJAN
    "E250231",   # DR PAVAN R KOLEKAR
]

# ── Entry Generator ───────────────────────────────────────────────────────────
def spread(lo, hi, n):
    """Evenly spread integers from lo to hi over n steps."""
    return [round(lo + (hi - lo) * i / max(n - 1, 1)) for i in range(n)]

def gen_entries():
    rows = []
    fi   = 0  # faculty index

    def next_fac():
        nonlocal fi
        f = FACULTY[fi % len(FACULTY)]
        fi += 1
        return f

    def class_type(i):
        # Every 7th entry → Seminars (simulates weekly seminar)
        return "Seminars" if (i + 1) % 7 == 0 else "Other"

    # ── December 2025: Dec 5–31 → 27 days, USG 40→55 ────────────────────────
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2025, 12, 5) + timedelta(i)
        p = f"{n}usgs performed"
        rows.append(dict(
            date    = d.strftime("%d/%m/%Y"),
            proc    = p,
            desc    = p,
            caption = p,
            fac     = next_fac(),
            ctype   = class_type(i),
        ))

    # ── January 2026: Jan 1–31 → 31 days, CT + MRI ──────────────────────────
    for i in range(31):
        d   = date(2026, 1, 1) + timedelta(i)
        ct  = random.randint(10, 15)
        mri = random.randint(2, 5)
        p   = f"Ct cases drafted {ct} and {mri} MRI"
        rows.append(dict(
            date    = d.strftime("%d/%m/%Y"),
            proc    = p,
            desc    = p,
            caption = p,
            fac     = next_fac(),
            ctype   = class_type(i),
        ))

    # ── February 2026: Feb 1–27 → 27 days, USG 40→55 ───────────────────────
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2026, 2, 1) + timedelta(i)
        p = f"{n}usgs performed"
        rows.append(dict(
            date    = d.strftime("%d/%m/%Y"),
            proc    = p,
            desc    = p,
            caption = p,
            fac     = next_fac(),
            ctype   = class_type(i),
        ))

    return rows

# ── Browser setup ─────────────────────────────────────────────────────────────
def make_driver():
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--window-size=1366,768")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=o
    )

# ── Helpers ───────────────────────────────────────────────────────────────────
def shot(d, name):
    d.save_screenshot(f"screenshot_{name}.png")
    print(f"  📸 {name}.png")

def try_fill(driver, xpaths, value):
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            el.clear()
            el.send_keys(value)
            return True
        except:
            continue
    return False

def try_select(driver, xpaths, text):
    for xp in xpaths:
        try:
            el  = driver.find_element(By.XPATH, xp)
            sel = Select(el)
            for opt in sel.options:
                if text.lower() in opt.text.lower():
                    sel.select_by_visible_text(opt.text)
                    return True
        except:
            continue
    return False

def try_click(driver, xpaths):
    for xp in xpaths:
        try:
            driver.find_element(By.XPATH, xp).click()
            return True
        except:
            continue
    return False

# ── Login ─────────────────────────────────────────────────────────────────────
def login(driver):
    print("→ Opening login page...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(3)
    shot(driver, "00_login_page")

    # Username
    try_fill(driver, [
        "//input[@id[contains(.,'User') or contains(.,'user') or contains(.,'Login')]]",
        "//input[@name[contains(.,'user') or contains(.,'User')]]",
        "//input[@type='text'][1]",
    ], USER)

    # Password
    try_fill(driver, [
        "//input[@type='password']",
        "//input[@id[contains(.,'Pass') or contains(.,'pass')]]",
    ], PASS)

    # Login button
    try_click(driver, [
        "//input[@type='submit']",
        "//button[@type='submit']",
        "//input[@value[contains(.,'Login') or contains(.,'login') or contains(.,'Sign')]]",
        "//button[contains(.,'Login') or contains(.,'Sign')]",
        "//input[@id[contains(.,'Login') or contains(.,'Btn')]]",
    ])

    time.sleep(4)
    shot(driver, "01_after_login")
    print(f"  URL: {driver.current_url}")

# ── Submit one entry ──────────────────────────────────────────────────────────
def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['fac']} | {e['ctype']} | {e['proc']}")

    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(2)

    # ── Click + Add ───────────────────────────────────────────────────────────
    try_click(driver, [
        "//a[contains(.,'Add') or contains(.,'add')]",
        "//button[contains(.,'Add')]",
        "//*[contains(@class,'btn')][contains(.,'Add')]",
        "//input[@value[contains(.,'Add')]]",
        "//*[@id[contains(.,'Add')]]",
    ])
    time.sleep(2)
    shot(driver, f"{idx+1:03d}_a_form")

    # ── Session Year dropdown: pick option with "2023" ────────────────────────
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s    = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("2023" in o for o in opts):
                for o in opts:
                    if "2023" in o:
                        s.select_by_visible_text(o)
                        break
                break
        except:
            continue

    # ── Name of Procedure ─────────────────────────────────────────────────────
    try_fill(driver, [
        "//*[contains(text(),'Name of the Procedure')]/following::input[1]",
        "//*[contains(text(),'Name of the Procedure')]/following::textarea[1]",
        "//input[@id[contains(.,'ProcedureName') or contains(.,'Proc') or contains(.,'txtProc')]]",
        "//input[@id[contains(.,'Activity') or contains(.,'activity')]]",
    ], e["proc"])

    # ── Date ─────────────────────────────────────────────────────────────────
    try_fill(driver, [
        "//*[contains(text(),'Date')]/following::input[1]",
        "//input[@id[contains(.,'Date') or contains(.,'date')]]",
        "//input[@type='date']",
    ], e["date"])

    # ── Faculty ───────────────────────────────────────────────────────────────
    fac_filled = False
    for xp in [
        "//*[contains(text(),'Faculty')]/following::input[1]",
        "//input[@id[contains(.,'Faculty') or contains(.,'faculty')]]",
    ]:
        try:
            el = driver.find_element(By.XPATH, xp)
            el.clear()
            el.send_keys(e["fac"])
            time.sleep(2.5)
            # Try to click autocomplete suggestion
            for sxp in [
                f"//*[contains(text(),'{e['fac']}') and not(self::input)]",
                "//*[contains(@class,'autocomplete') or contains(@class,'suggest')]//li[1]",
                "//*[contains(@class,'ui-menu-item')][1]",
            ]:
                try:
                    driver.find_element(By.XPATH, sxp).click()
                    fac_filled = True
                    break
                except:
                    continue
            if not fac_filled:
                el.send_keys(Keys.RETURN)
            time.sleep(1)
            break
        except:
            continue

    # ── Procedures dropdown → "Washed up and observed" ───────────────────────
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s    = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Washed" in o or "washed" in o for o in opts):
                for o in opts:
                    if "Washed" in o or "washed" in o:
                        s.select_by_visible_text(o)
                        break
                break
        except:
            continue

    # ── Work Type → "Lab Work" ────────────────────────────────────────────────
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s    = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Lab" in o for o in opts):
                for o in opts:
                    if "Lab" in o:
                        s.select_by_visible_text(o)
                        break
                break
        except:
            continue

    # ── Description ───────────────────────────────────────────────────────────
    try_fill(driver, [
        "//*[contains(text(),'Description')]/following::input[1]",
        "//*[contains(text(),'Description')]/following::textarea[1]",
        "//input[@id[contains(.,'Desc') or contains(.,'desc')]]",
        "//textarea[@id[contains(.,'Desc') or contains(.,'desc')]]",
    ], e["desc"])

    # ── Classes → "Attended" ─────────────────────────────────────────────────
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s    = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Attended" in o for o in opts):
                for o in opts:
                    if "Attended" in o:
                        s.select_by_visible_text(o)
                        break
                break
        except:
            continue

    # ── Class Type → "Other" or "Seminars" ───────────────────────────────────
    target_ctype = e["ctype"]  # "Other" or "Seminars"
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s    = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Other" in o for o in opts) and any("Sem" in o for o in opts):
                for o in opts:
                    if target_ctype.lower() in o.lower():
                        s.select_by_visible_text(o)
                        break
                break
        except:
            continue

    # ── File Caption (no file upload) ─────────────────────────────────────────
    try_fill(driver, [
        "//*[contains(text(),'File Caption')]/following::input[1]",
        "//input[@id[contains(.,'Caption') or contains(.,'caption')]]",
        "//input[@id[contains(.,'FileCaption')]]",
    ], e["caption"])

    # ── Save ─────────────────────────────────────────────────────────────────
    saved = try_click(driver, [
        "//input[@value='Save']",
        "//button[normalize-space()='Save']",
        "//input[@id[contains(.,'Save') or contains(.,'Btn')]][@type='button' or @type='submit']",
    ])
    if not saved:
        shot(driver, f"{idx+1:03d}_SAVE_FAILED")
        print("  ❌ Save button not found!")
        return False

    time.sleep(2.5)
    shot(driver, f"{idx+1:03d}_b_after_save")

    # ── I want to Submit + Submit ─────────────────────────────────────────────
    try:
        cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if not cb.is_selected():
            cb.click()
        time.sleep(0.5)
    except:
        print("  ⚠️  Checkbox not found – continuing to Submit")

    submitted = try_click(driver, [
        "//input[@value='Submit']",
        "//button[normalize-space()='Submit']",
        "//input[@id[contains(.,'Submit')]]",
    ])

    time.sleep(2.5)

    if submitted:
        print("  ✅ Entry submitted!")
        return True
    else:
        shot(driver, f"{idx+1:03d}_SUBMIT_FAILED")
        print("  ❌ Submit failed!")
        return False

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    entries = gen_entries()

    # ── Dry run / preview ─────────────────────────────────────────────────────
    if DRY_RUN or not PASS:
        print(f"\n{'='*70}")
        print(f"DRY RUN – {len(entries)} entries planned:")
        print(f"{'='*70}")
        print(f"{'#':<4} {'Date':<12} {'Fac':<10} {'CType':<10} Procedure")
        print("-" * 70)
        for i, e in enumerate(entries):
            print(f"{i+1:<4} {e['date']:<12} {e['fac']:<10} {e['ctype']:<10} {e['proc']}")
        print(f"\nTotal: {len(entries)} entries")
        print("\nSet DRY_RUN=false and provide LB_PASS to run for real.")
        return

    # ── Live run ──────────────────────────────────────────────────────────────
    driver = make_driver()
    ok, fail = 0, 0

    try:
        login(driver)

        for i, e in enumerate(entries):
            try:
                if do_entry(driver, e, i):
                    ok += 1
                else:
                    fail += 1
            except Exception as ex:
                print(f"  💥 Crashed: {ex}")
                shot(driver, f"{i+1:03d}_CRASH")
                fail += 1
            # polite delay between entries
            time.sleep(random.uniform(2.5, 5.0))

    finally:
        driver.quit()

    print(f"\n{'='*50}")
    print(f"FINISHED  ✅ {ok} submitted  |  ❌ {fail} failed")
    if fail > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
