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
        nonlocal fi; f = FACULTY[fi % len(FACULTY)]; fi += 1; return f
    def class_type(i):
        return "Seminars" if (i + 1) % 7 == 0 else "Other"
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2025, 12, 5) + timedelta(i); p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i), session="2025"))
    random.seed(42)
    for i in range(31):
        d = date(2026, 1, 1) + timedelta(i)
        p = f"Ct cases drafted {random.randint(10,15)} and {random.randint(2,5)} MRI"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i), session="2026"))
    for i, n in enumerate(spread(40, 55, 27)):
        d = date(2026, 2, 1) + timedelta(i); p = f"{n}usgs performed"
        rows.append(dict(date=d.strftime("%d/%m/%Y"), proc=p, desc=p, caption=p, fac=next_fac(), ctype=class_type(i), session="2026"))
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

def is_logged_out(driver):
    """Returns True if we've been redirected to login page"""
    url = driver.current_url.lower()
    if "login" in url or "default.aspx" in url:
        return True
    # Check if login form inputs exist
    try:
        driver.find_element(By.ID, "txtUserID")
        return True
    except:
        return False

def do_login(driver):
    print("  Logging in...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(3)
    try:
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        js_click(driver, radios[0])
    except: pass
    time.sleep(1)
    try:
        el = driver.find_element(By.ID, "txtUserID")
        js_fill(driver, el, USER)
    except:
        try:
            el = driver.find_element(By.XPATH, "//input[@type='text'][1]")
            js_fill(driver, el, USER)
        except: pass
    try:
        el = driver.find_element(By.ID, "txtPassword")
        js_fill(driver, el, PASS)
    except:
        try:
            el = driver.find_element(By.XPATH, "//input[@type='password']")
            js_fill(driver, el, PASS)
        except: pass
    try:
        btn = driver.find_element(By.ID, "myBtn")
        js_click(driver, btn)
    except:
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(.,'LOGIN')] | //input[@type='submit']")
            js_click(driver, btn)
        except: pass
    time.sleep(5)
    if is_logged_out(driver):
        print("  ERROR: Login failed!")
        shot(driver, "LOGIN_FAILED")
        return False
    print(f"  Logged in! URL: {driver.current_url}")
    return True

def ensure_logged_in(driver):
    """Re-login if session expired"""
    if is_logged_out(driver):
        print("  Session expired! Re-logging in...")
        return do_login(driver)
    return True

def select_session(driver, session_year):
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            if any(session_year in o for o in opts):
                for o in opts:
                    if session_year in o and "Select" not in o:
                        s.select_by_visible_text(o)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                        print(f"  Session: {o}")
                        return True
        except: continue
    print(f"  WARNING: session {session_year} not found")
    return False

def click_save(driver):
    for selector in [
        "//input[@value='Save']",
        "//button[normalize-space()='Save']",
        "//button[contains(.,'Save')]",
        "//input[contains(@value,'Save')]",
        "//a[contains(.,'Save')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el)
            print("  Clicked Save")
            return True
        except: continue
    try:
        for el in driver.find_elements(By.TAG_NAME, "button"):
            if "save" in el.text.lower(): js_click(driver, el); return True
        for el in driver.find_elements(By.TAG_NAME, "input"):
            v = el.get_attribute("value") or ""
            if "save" in v.lower(): js_click(driver, el); return True
    except: pass
    return False

def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['session']} | {e['fac']} | {e['ctype']} | {e['proc']}")

    # Navigate to logbook page
    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(3)

    # CHECK: did we get redirected to login?
    if is_logged_out(driver):
        print("  Session expired - re-logging in...")
        if not do_login(driver):
            print("  Re-login failed! Skipping entry.")
            return False
        # Navigate back to logbook
        driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
        time.sleep(3)

    # Click Add button
    add_clicked = False
    for selector in [
        "//a[contains(.,'Add')]", "//button[contains(.,'Add')]",
        "//*[contains(@class,'btn')][contains(.,'Add')]",
        "//input[@value[contains(.,'Add')]]",
        "//*[contains(text(),'+ Add')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); add_clicked = True; time.sleep(2); break
        except: continue

    if not add_clicked:
        shot(driver, f"{idx+1:03d}_ADD_FAILED")
        print("  Add button not found!"); return False

    shot(driver, f"{idx+1:03d}_a_form")

    # CHECK again after clicking Add
    if is_logged_out(driver):
        print("  Logged out after Add click - re-logging in...")
        if not do_login(driver): return False
        driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
        time.sleep(2)
        for selector in ["//a[contains(.,'Add')]", "//button[contains(.,'Add')]"]:
            try:
                el = driver.find_element(By.XPATH, selector)
                js_click(driver, el); time.sleep(2); break
            except: continue

    # Select session year FIRST
    select_session(driver, e["session"])
    time.sleep(3)
    shot(driver, f"{idx+1:03d}_a2_session")

    # Print inputs for debugging first 3 entries
    if idx < 3:
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"  DEBUG inputs ({len(inputs)}):")
        for inp in inputs:
            itype = inp.get_attribute("type") or "text"
            if itype != "hidden":
                print(f"    id={inp.get_attribute('id')} ph={inp.get_attribute('placeholder')} type={itype}")
        selects = driver.find_elements(By.TAG_NAME, "select")
        for s in selects:
            try:
                sel = Select(s)
                print(f"    SELECT id={s.get_attribute('id')}: {[o.text for o in sel.options[:4]]}")
            except: pass

    # Fill Name of Procedure
    filled_proc = False
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid   = (inp.get_attribute("id") or "").lower()
        iname = (inp.get_attribute("name") or "").lower()
        iph   = (inp.get_attribute("placeholder") or "").lower()
        itype = (inp.get_attribute("type") or "text").lower()
        if itype in ["hidden","file","checkbox","radio","submit","button","password"]: continue
        if any(k in iid+iname+iph for k in ["proc","activity","actname","txtact","txtproc","name","title"]):
            if "user" not in iid+iname and "pass" not in iid+iname:
                js_fill(driver, inp, e["proc"])
                print(f"  Procedure → {inp.get_attribute('id')}")
                filled_proc = True; break
    if not filled_proc:
        visibles = [i for i in driver.find_elements(By.TAG_NAME, "input")
                    if (i.get_attribute("type") or "text") not in ["hidden","file","checkbox","radio","submit","button","password"]
                    and i.is_displayed()
                    and "user" not in (i.get_attribute("id") or "").lower()
                    and "pass" not in (i.get_attribute("id") or "").lower()]
        if visibles:
            js_fill(driver, visibles[0], e["proc"])
            print(f"  Procedure → first visible: {visibles[0].get_attribute('id')}")

    # Fill Date
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid   = (inp.get_attribute("id") or "").lower()
        iname = (inp.get_attribute("name") or "").lower()
        itype = (inp.get_attribute("type") or "text").lower()
        if "date" in iid+iname or itype == "date":
            js_fill(driver, inp, e["date"])
            print(f"  Date → {inp.get_attribute('id')}: {e['date']}")
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
            print(f"  Faculty → {inp.get_attribute('id')}: {e['fac']}")
            break

    # Dropdowns
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Washed" in o for o in opts):
                for o in opts:
                    if "Washed" in o: s.select_by_visible_text(o); print(f"  Procedure type → {o}"); break
            elif any("Lab" in o for o in opts):
                for o in opts:
                    if "Lab" in o: s.select_by_visible_text(o); print(f"  Work type → {o}"); break
            elif any("Attended" in o for o in opts):
                for o in opts:
                    if "Attended" in o: s.select_by_visible_text(o); print(f"  Classes → {o}"); break
            elif any("Other" in o for o in opts) and any("Sem" in o for o in opts):
                for o in opts:
                    if e["ctype"].lower() in o.lower():
                        s.select_by_visible_text(o); print(f"  Class type → {o}"); break
        except: continue

    # Description
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid = (inp.get_attribute("id") or "").lower()
        if "desc" in iid:
            js_fill(driver, inp, e["desc"]); print(f"  Desc → {inp.get_attribute('id')}"); break
    for ta in driver.find_elements(By.TAG_NAME, "textarea"):
        iid = (ta.get_attribute("id") or "").lower()
        if "desc" in iid:
            js_fill(driver, ta, e["desc"]); print(f"  Desc(ta) → {ta.get_attribute('id')}"); break

    # File Caption
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        iid = (inp.get_attribute("id") or "").lower()
        iph = (inp.get_attribute("placeholder") or "").lower()
        if "caption" in iid+iph or ("desc" in iph and "caption" not in iid):
            js_fill(driver, inp, e["caption"]); print(f"  Caption → {inp.get_attribute('id')}"); break

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
        print(f"\n{'='*70}\nDRY RUN - {len(entries)} entries\n{'='*70}")
        print(f"{'#':<4} {'Date':<13} {'Ses':<6} {'Fac':<10} {'CType':<10} Procedure")
        print("-"*70)
        for i, e in enumerate(entries):
            print(f"{i+1:<4} {e['date']:<13} {e['session']:<6} {e['fac']:<10} {e['ctype']:<10} {e['proc']}")
        print(f"\nTotal: {len(entries)} entries")
        return

    driver = make_driver()
    ok, fail = 0, 0
    try:
        if not do_login(driver):
            print("Initial login failed!"); sys.exit(1)
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
