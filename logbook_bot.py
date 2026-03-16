#!/usr/bin/env python3
import os, sys, time, random
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
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

    # December 2025 → session year 2025
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2025, 12, 5) + timedelta(i); p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p,
                         fac=next_fac(), ctype=class_type(i), session="2025"))

    # January 2026 → session year 2026
    random.seed(42)
    for i in range(31):
        d = date(2026, 1, 1) + timedelta(i)
        p = f"Ct cases drafted {random.randint(10,15)} and {random.randint(2,5)} MRI"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p,
                         fac=next_fac(), ctype=class_type(i), session="2026"))

    # February 2026 → session year 2026
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2026, 2, 1) + timedelta(i); p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p,
                         fac=next_fac(), ctype=class_type(i), session="2026"))
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

def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)

def js_fill(driver, el, value):
    driver.execute_script("arguments[0].value = '';", el)
    driver.execute_script("arguments[0].value = arguments[1];", el, value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", el)

def login(driver):
    print("Opening login page...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(3)
    shot(driver, "00_login")
    try:
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        js_click(driver, radios[0])
        print("  Clicked Student radio")
    except Exception as ex:
        print(f"  Radio error: {ex}")
    time.sleep(1)
    try:
        el = driver.find_element(By.XPATH, "//input[@placeholder[contains(.,'User')] or @type='text'][1]")
        js_fill(driver, el, USER)
        print("  Filled username")
    except Exception as ex:
        print(f"  Username error: {ex}")
    try:
        el = driver.find_element(By.XPATH, "//input[@type='password']")
        js_fill(driver, el, PASS)
        print("  Filled password")
    except Exception as ex:
        print(f"  Password error: {ex}")
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(.,'LOGIN') or contains(.,'Login')] | //input[@type='submit']")
        js_click(driver, btn)
        print("  Clicked LOGIN")
    except Exception as ex:
        print(f"  Login btn error: {ex}")
    time.sleep(5)
    shot(driver, "01_after_login")
    print(f"  URL: {driver.current_url}")

def select_session(driver, session_year):
    """Select session year dropdown - picks option containing session_year (2025 or 2026)"""
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            # Find the session dropdown (has year options)
            if any(session_year in o for o in opts):
                for o in opts:
                    if session_year in o and "Select" not in o:
                        js_click(driver, sel_el)
                        s.select_by_visible_text(o)
                        driver.execute_script(
                            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                        print(f"  Selected session: {o}")
                        return True
        except Exception as ex:
            print(f"  Session select error: {ex}"); continue
    print(f"  WARNING: Could not find session year {session_year}")
    return False

def click_save(driver):
    for selector in [
        "//input[@value='Save']",
        "//button[normalize-space()='Save']",
        "//button[contains(.,'Save')]",
        "//input[contains(@value,'Save')]",
        "//a[contains(.,'Save')]",
        "//*[contains(@id,'Save') or contains(@id,'save')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el)
            print(f"  Clicked Save")
            return True
        except: continue
    try:
        for el in driver.find_elements(By.TAG_NAME, "button"):
            if "save" in el.text.lower():
                js_click(driver, el); return True
        for el in driver.find_elements(By.TAG_NAME, "input"):
            v = el.get_attribute("value") or ""
            if "save" in v.lower():
                js_click(driver, el); return True
    except: pass
    return False

def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['session']} | {e['fac']} | {e['ctype']} | {e['proc']}")
    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(2)

    # Click Add
    for selector in [
        "//a[contains(.,'Add')]", "//button[contains(.,'Add')]",
        "//*[contains(@class,'btn')][contains(.,'Add')]",
        "//input[@value[contains(.,'Add')]]",
        "//*[contains(text(),'+ Add')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); time.sleep(2); break
        except: continue

    shot(driver, f"{idx+1:03d}_a_form")

    # Select session year FIRST, then wait for form to load
    select_session(driver, e["session"])
    time.sleep(3)
    shot(driver, f"{idx+1:03d}_a2_session")

    # Debug: print all inputs
    inputs = driver.find_elements(By.TAG_NAME, "input")
    print(f"  Inputs found: {len(inputs)}")
    for inp in inputs[:15]:
        print(f"    id={inp.get_attribute('id')} name={inp.get_attribute('name')} "
              f"ph={inp.get_attribute('placeholder')} type={inp.get_attribute('type')}")

    # Fill Name of Procedure
    filled = False
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid   = (inp.get_attribute("id") or "").lower()
        iname = (inp.get_attribute("name") or "").lower()
        iph   = (inp.get_attribute("placeholder") or "").lower()
        itype = (inp.get_attribute("type") or "text").lower()
        if itype in ["hidden","file","checkbox","radio","submit","button"]: continue
        if any(k in iid+iname+iph for k in ["proc","activity","code","title","actname"]):
            js_fill(driver, inp, e["proc"])
            print(f"  Filled procedure: {inp.get_attribute('id')}")
            filled = True; break
    if not filled:
        visibles = [i for i in driver.find_elements(By.TAG_NAME, "input")
                    if i.get_attribute("type") not in ["hidden","file","checkbox","radio","submit","button"]
                    and i.is_displayed()]
        if visibles:
            js_fill(driver, visibles[0], e["proc"])
            print(f"  Filled procedure in first visible: {visibles[0].get_attribute('id')}")

    # Fill Date
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid   = (inp.get_attribute("id") or "").lower()
        iname = (inp.get_attribute("name") or "").lower()
        itype = (inp.get_attribute("type") or "text").lower()
        if "date" in iid+iname or itype == "date":
            js_fill(driver, inp, e["date"])
            print(f"  Filled date: {e['date']}")
            break

    # Fill Faculty
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid   = (inp.get_attribute("id") or "").lower()
        iname = (inp.get_attribute("name") or "").lower()
        if "fac" in iid+iname:
            js_fill(driver, inp, e["fac"])
            time.sleep(2)
            try:
                sugg = driver.find_elements(By.XPATH,
                    "//*[contains(@class,'ui-menu-item') or contains(@class,'autocomplete')]")
                if sugg: js_click(driver, sugg[0])
            except: pass
            print(f"  Filled faculty: {e['fac']}")
            break

    # Fill all dropdowns
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Washed" in o for o in opts):
                for o in opts:
                    if "Washed" in o: s.select_by_visible_text(o); print("  Selected Washed up"); break
            elif any("Lab" in o for o in opts):
                for o in opts:
                    if "Lab" in o: s.select_by_visible_text(o); print("  Selected Lab Work"); break
            elif any("Attended" in o for o in opts):
                for o in opts:
                    if "Attended" in o: s.select_by_visible_text(o); print("  Selected Attended"); break
            elif any("Other" in o for o in opts) and any("Sem" in o for o in opts):
                for o in opts:
                    if e["ctype"].lower() in o.lower():
                        s.select_by_visible_text(o); print(f"  Selected {o}"); break
        except: continue

    # Fill Description
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid = (inp.get_attribute("id") or "").lower()
        if "desc" in iid:
            js_fill(driver, inp, e["desc"]); print("  Filled description"); break
    for ta in driver.find_elements(By.TAG_NAME, "textarea"):
        iid = (ta.get_attribute("id") or "").lower()
        if "desc" in iid:
            js_fill(driver, ta, e["desc"]); print("  Filled description textarea"); break

    # Fill File Caption
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid = (inp.get_attribute("id") or "").lower()
        iph = (inp.get_attribute("placeholder") or "").lower()
        if "caption" in iid+iph or "description" in iph:
            js_fill(driver, inp, e["caption"]); print("  Filled caption"); break

    shot(driver, f"{idx+1:03d}_b_before_save")

    # Save
    saved = click_save(driver)
    if not saved:
        shot(driver, f"{idx+1:03d}_SAVE_FAILED")
        print("  SAVE FAILED"); return False

    time.sleep(3)
    shot(driver, f"{idx+1:03d}_c_saved")

    # Checkbox + Submit
    try:
        cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if not cb.is_selected(): js_click(driver, cb)
        time.sleep(0.5)
    except: pass

    submitted = False
    for selector in ["//input[@value='Submit']", "//button[contains(.,'Submit')]", "//a[contains(.,'Submit')]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); submitted = True; break
        except: continue

    time.sleep(2.5)
    if submitted:
        print("  OK submitted"); return True
    else:
        shot(driver, f"{idx+1:03d}_SUBMIT_FAILED")
        print("  SUBMIT FAILED"); return False

def main():
    entries = gen_entries()
    if DRY_RUN:
        print(f"\n{'='*70}\nDRY RUN - {len(entries)} entries planned:\n{'='*70}")
        print(f"{'#':<4} {'Date':<13} {'Session':<8} {'Fac':<10} {'CType':<10} Procedure")
        print("-"*70)
        for i, e in enumerate(entries):
            print(f"{i+1:<4} {e['date']:<13} {e['session']:<8} {e['fac']:<10} {e['ctype']:<10} {e['proc']}")
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
            time.sleep(random.uniform(2.5, 4.0))
    finally:
        driver.quit()
    print(f"\nFINISHED: {ok} submitted | {fail} failed")
    if fail > 0: sys.exit(1)

if __name__ == "__main__":
    main()
