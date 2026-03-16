#!/usr/bin/env python3
import os, sys, time, random
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

USER    = os.environ.get("LB_USER", "S240128")
PASS    = os.environ.get("LB_PASS", "")
BASE    = "https://myapp.in/pglogbook"
DRY_RUN = os.environ.get("DRY_RUN", "preview") == "preview"

FACULTY = ["E250131","E250248","E250176","E250231"]

def spread(lo, hi, n):
    return [round(lo + (hi - lo) * i / max(n - 1, 1)) for i in range(n)]

def gen_entries():
    rows = []; fi = 0
    def next_fac():
        nonlocal fi
        f = FACULTY[fi % len(FACULTY)]; fi += 1; return f
    def class_type(i):
        return "Seminars" if (i + 1) % 7 == 0 else "Other"

    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2025, 12, 5) + timedelta(i)
        p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i)))

    random.seed(42)
    for i in range(31):
        d = date(2026, 1, 1) + timedelta(i)
        p = f"Ct cases drafted {random.randint(10,15)} and {random.randint(2,5)} MRI"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i)))

    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2026, 2, 1) + timedelta(i)
        p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i)))

    return rows

def make_driver():
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--window-size=1366,768")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)

def shot(d, name):
    d.save_screenshot(f"screenshot_{name}.png")
    print(f"  screenshot: {name}.png")

def try_fill(driver, xpaths, value):
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            el.clear(); el.send_keys(value); return True
        except: continue
    return False

def try_click(driver, xpaths):
    for xp in xpaths:
        try:
            driver.find_element(By.XPATH, xp).click(); return True
        except: continue
    return False

def login(driver):
    print("Opening login page...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(3)
    shot(driver, "00_login")
    try_fill(driver, ["//input[@type='text'][1]", "//input[@id[contains(.,'User')]]"], USER)
    try_fill(driver, ["//input[@type='password']"], PASS)
    try_click(driver, ["//input[@type='submit']", "//button[@type='submit']", "//input[@value[contains(.,'Login')]]"])
    time.sleep(4)
    shot(driver, "01_after_login")
    print(f"  URL: {driver.current_url}")

def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['fac']} | {e['ctype']} | {e['proc']}")
    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(2)

    try_click(driver, [
        "//a[contains(.,'Add')]", "//button[contains(.,'Add')]",
        "//*[contains(@class,'btn')][contains(.,'Add')]",
        "//input[@value[contains(.,'Add')]]",
    ])
    time.sleep(2)
    shot(driver, f"{idx+1:03d}_a_form")

    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            if any("2023" in o.text for o in s.options):
                for o in s.options:
                    if "2023" in o.text: s.select_by_visible_text(o.text); break
                break
        except: continue

    try_fill(driver, [
        "//*[contains(text(),'Name of the Procedure')]/following::input[1]",
        "//input[@id[contains(.,'Proc')]]",
    ], e["proc"])

    try_fill(driver, [
        "//*[contains(text(),'Date')]/following::input[1]",
        "//input[@id[contains(.,'Date')]]",
        "//input[@type='date']",
    ], e["date"])

    for xp in ["//*[contains(text(),'Faculty')]/following::input[1]", "//input[@id[contains(.,'Faculty')]]"]:
        try:
            el = driver.find_element(By.XPATH, xp)
            el.clear(); el.send_keys(e["fac"]); time.sleep(2.5)
            for sxp in [f"//*[contains(text(),'{e['fac']}') and not(self::input)]", "//*[contains(@class,'ui-menu-item')][1]"]:
                try: driver.find_element(By.XPATH, sxp).click(); break
                except: continue
            time.sleep(1); break
        except: continue

    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            if any("Washed" in o.text for o in s.options):
                for o in s.options:
                    if "Washed" in o.text: s.select_by_visible_text(o.text); break
                break
        except: continue

    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            if any("Lab" in o.text for o in s.options):
                for o in s.options:
                    if "Lab" in o.text: s.select_by_visible_text(o.text); break
                break
        except: continue

    try_fill(driver, [
        "//*[contains(text(),'Description')]/following::input[1]",
        "//*[contains(text(),'Description')]/following::textarea[1]",
        "//input[@id[contains(.,'Desc')]]",
    ], e["desc"])

    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            if any("Attended" in o.text for o in s.options):
                for o in s.options:
                    if "Attended" in o.text: s.select_by_visible_text(o.text); break
                break
        except: continue

    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            if any("Other" in o.text for o in s.options) and any("Sem" in o.text for o in s.options):
                for o in s.options:
                    if e["ctype"].lower() in o.text.lower(): s.select_by_visible_text(o.text); break
                break
        except: continue

    try_fill(driver, [
        "//*[contains(text(),'File Caption')]/following::input[1]",
        "//input[@id[contains(.,'Caption')]]",
    ], e["caption"])

    saved = try_click(driver, [
        "//input[@value='Save']", "//button[normalize-space()='Save']",
    ])
    if not saved:
        shot(driver, f"{idx+1:03d}_SAVE_FAILED")
        print("  SAVE FAILED"); return False

    time.sleep(2.5)
    shot(driver, f"{idx+1:03d}_b_saved")

    try:
        cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if not cb.is_selected(): cb.click()
        time.sleep(0.5)
    except: pass

    submitted = try_click(driver, [
        "//input[@value='Submit']", "//button[normalize-space()='Submit']",
    ])
    time.sleep(2.5)

    if submitted:
        print("  OK submitted"); return True
    else:
        shot(driver, f"{idx+1:03d}_SUBMIT_FAILED")
        print("  SUBMIT FAILED"); return False

def main():
    entries = gen_entries()
    if DRY_RUN:
        print(f"\n{'='*70}")
        print(f"DRY RUN - {len(entries)} entries planned:")
        print(f"{'='*70}")
        print(f"{'#':<4} {'Date':<13} {'Fac':<10} {'CType':<10} Procedure")
        print("-" * 70)
        for i, e in enumerate(entries):
            print(f"{i+1:<4} {e['date']:<13} {e['fac']:<10} {e['ctype']:<10} {e['proc']}")
        print(f"\nTotal: {len(entries)} entries")
        return

    driver = make_driver()
    ok, fail = 0, 0
    try:
        login(driver)
        for i, e in enumerate(entries):
            try:
                if do_entry(driver, e, i): ok += 1
                else: fail += 1
            except Exception as ex:
                print(f"  CRASH: {ex}")
                shot(driver, f"{i+1:03d}_CRASH")
                fail += 1
            time.sleep(random.uniform(2.5, 5.0))
    finally:
        driver.quit()

    print(f"\nFINISHED: {ok} submitted | {fail} failed")
    if fail > 0: sys.exit(1)

if __name__ == "__main__":
    main()
