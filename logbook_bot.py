#!/usr/bin/env python3
import os, sys, time, random
from datetime import date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    url = driver.current_url.lower()
    if "login" in url or "default.aspx" in url: return True
    try:
        driver.find_element(By.ID, "txtUserID"); return True
    except: return False

def do_login(driver):
    print("  Logging in...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(3)
    try:
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        js_click(driver, radios[0])
    except: pass
    time.sleep(1)
    try: js_fill(driver, driver.find_element(By.ID, "txtUserID"), USER)
    except: pass
    try: js_fill(driver, driver.find_element(By.ID, "txtPassword"), PASS)
    except: pass
    try: js_click(driver, driver.find_element(By.ID, "myBtn"))
    except:
        try: js_click(driver, driver.find_element(By.XPATH, "//button[contains(.,'LOGIN')]"))
        except: pass
    time.sleep(5)
    if is_logged_out(driver):
        print("  Login failed!")
        shot(driver, "LOGIN_FAILED")
        return False
    print(f"  Logged in! URL: {driver.current_url}")
    return True

def wait_for_session_options(driver, timeout=15):
    """Wait until cboStudentSessionDetail has more than 1 option"""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(Select(d.find_element(By.ID, "cboStudentSessionDetail")).options) > 1
        )
        return True
    except:
        return False

def select_session(driver, session_year):
    # Wait for options to load
    print(f"  Waiting for session dropdown options...")
    loaded = wait_for_session_options(driver, timeout=15)
    if not loaded:
        print(f"  Dropdown still empty after wait!")
        # Print page source snippet for debug
        try:
            sel = driver.find_element(By.ID, "cboStudentSessionDetail")
            s = Select(sel)
            print(f"  Options: {[o.text for o in s.options]}")
        except: pass
        return False

    try:
        sel = driver.find_element(By.ID, "cboStudentSessionDetail")
        s = Select(sel)
        opts = [o.text for o in s.options]
        print(f"  Session options: {opts}")
        # Pick option containing session_year
        for o in opts:
            if session_year in o and "Select" not in o:
                s.select_by_visible_text(o)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel)
                print(f"  Selected: {o}")
                time.sleep(3)  # Wait for form fields to load after selection
                return True
        print(f"  No option found containing '{session_year}'")
        return False
    except Exception as ex:
        print(f"  Session select error: {ex}")
        return False

def debug_form(driver, label):
    """Print all visible form fields"""
    print(f"  --- DEBUG {label} ---")
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        itype = (inp.get_attribute("type") or "text").lower()
        if itype != "hidden":
            print(f"    INPUT id={inp.get_attribute('id')} name={inp.get_attribute('name')} ph={inp.get_attribute('placeholder')} type={itype} visible={inp.is_displayed()}")
    for sel in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel)
            print(f"    SELECT id={sel.get_attribute('id')}: {[o.text for o in s.options[:5]]}")
        except: pass
    for ta in driver.find_elements(By.TAG_NAME, "textarea"):
        print(f"    TEXTAREA id={ta.get_attribute('id')} name={ta.get_attribute('name')}")
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        print(f"    BUTTON text={btn.text} id={btn.get_attribute('id')}")
    for inp in driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']"):
        print(f"    BTN-INPUT value={inp.get_attribute('value')} id={inp.get_attribute('id')}")

def fill_field_by_id(driver, field_id, value):
    try:
        el = driver.find_element(By.ID, field_id)
        js_fill(driver, el, value)
        print(f"  Filled {field_id} = {value[:30]}")
        return True
    except: return False

def click_save(driver):
    for selector in [
        "//input[@value='Save']",
        "//button[normalize-space()='Save']",
        "//button[contains(.,'Save')]",
        "//input[contains(@value,'Save')]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el)
            print("  Clicked Save")
            return True
        except: continue
    return False

def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['session']} | {e['fac']} | {e['ctype']} | {e['proc']}")

    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(3)

    if is_logged_out(driver):
        print("  Session expired - re-logging in...")
        if not do_login(driver): return False
        driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
        time.sleep(3)

    # Click Add
    add_clicked = False
    for selector in ["//a[contains(.,'Add')]", "//button[contains(.,'Add')]",
                     "//*[contains(@class,'btn')][contains(.,'Add')]",
                     "//input[@value[contains(.,'Add')]]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); add_clicked = True; time.sleep(2); break
        except: continue

    if not add_clicked:
        shot(driver, f"{idx+1:03d}_ADD_FAILED")
        print("  Add button not found!"); return False

    shot(driver, f"{idx+1:03d}_a_form")

    # Select session year — this triggers the rest of the form to load
    session_ok = select_session(driver, e["session"])
    if not session_ok:
        shot(driver, f"{idx+1:03d}_SESSION_FAILED")
        # Try to debug what's on the page
        debug_form(driver, "SESSION_FAILED")
        return False

    # After session selected, wait and debug form fields
    shot(driver, f"{idx+1:03d}_a2_after_session")
    if idx < 2:
        debug_form(driver, f"AFTER_SESSION_{idx+1}")

    # Now fill fields using known IDs from the form
    # Try known IDs first, fall back to searching

    # Name of Procedure — try common IDs
    proc_filled = False
    for fid in ["txtActivityName", "txtProcedureName", "txtActivity",
                "txtName", "txtActName", "txtProc", "txtLogActivity"]:
        if fill_field_by_id(driver, fid, e["proc"]):
            proc_filled = True; break
    if not proc_filled:
        # Search all visible text inputs excluding known fields
        skip_ids = {"txtApprover", "txtUserID", "txtPassword", "txtFileDescription"}
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid   = (inp.get_attribute("id") or "")
            itype = (inp.get_attribute("type") or "text").lower()
            if itype in ["hidden","file","checkbox","radio","submit","button","password"]: continue
            if iid in skip_ids: continue
            if not inp.is_displayed(): continue
            js_fill(driver, inp, e["proc"])
            print(f"  Procedure → fallback: {iid}")
            proc_filled = True; break

    # Date — txtActivityDate or similar
    date_filled = False
    for fid in ["txtActivityDate", "txtDate", "txtLogDate", "txtDOA"]:
        if fill_field_by_id(driver, fid, e["date"]):
            date_filled = True; break
    if not date_filled:
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid = (inp.get_attribute("id") or "").lower()
            if "date" in iid and "current" not in iid and "hidden" not in (inp.get_attribute("type") or ""):
                js_fill(driver, inp, e["date"])
                print(f"  Date → {inp.get_attribute('id')}"); break

    # Faculty — txtApprover (confirmed from debug!)
    try:
        el = driver.find_element(By.ID, "txtApprover")
        el.clear()
        el.send_keys(e["fac"])
        time.sleep(2.5)
        # Click autocomplete suggestion
        try:
            sugg = driver.find_elements(By.XPATH,
                "//*[contains(@class,'ui-menu-item') or contains(@class,'autocomplete') or contains(@class,'suggest')]")
            if sugg:
                js_click(driver, sugg[0])
                print(f"  Faculty autocomplete selected")
            else:
                print(f"  Faculty → txtApprover: {e['fac']} (no autocomplete)")
        except: pass
    except Exception as ex:
        print(f"  Faculty error: {ex}")

    # Dropdowns — Procedures, Work Type, Classes, Class Type
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            if any("Washed" in o for o in opts):
                for o in opts:
                    if "Washed" in o: s.select_by_visible_text(o); print(f"  Procedures → {o}"); break
            elif any("Lab" in o for o in opts):
                for o in opts:
                    if "Lab" in o: s.select_by_visible_text(o); print(f"  Work Type → {o}"); break
            elif any("Attended" in o for o in opts):
                for o in opts:
                    if "Attended" in o: s.select_by_visible_text(o); print(f"  Classes → {o}"); break
            elif any("Other" in o for o in opts) and any("Sem" in o for o in opts):
                for o in opts:
                    if e["ctype"].lower() in o.lower():
                        s.select_by_visible_text(o); print(f"  Class Type → {o}"); break
        except: continue

    # Description — try known IDs
    for fid in ["txtDescription", "txtDesc", "txtLogDesc", "txtRemarks"]:
        if fill_field_by_id(driver, fid, e["desc"]): break

    # File Caption — txtFileDescription (confirmed!)
    fill_field_by_id(driver, "txtFileDescription", e["caption"])

    shot(driver, f"{idx+1:03d}_b_before_save")

    # Save
    saved = click_save(driver)
    if not saved:
        debug_form(driver, f"SAVE_FAILED_{idx+1}")
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
        debug_form(driver, f"SUBMIT_FAILED_{idx+1}")
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
        if not do_login(driver): sys.exit(1)
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
