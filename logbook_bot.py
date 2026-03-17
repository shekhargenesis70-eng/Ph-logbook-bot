#!/usr/bin/env python3
import os, sys, time, random, requests
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
    o.add_argument("--window-size=1920,1080")
    o.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
    d.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return d

def dismiss_alert(driver):
    try:
        WebDriverWait(driver, 2).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"  Alert: {alert.text}")
        alert.accept()
        time.sleep(1)
    except: pass

def shot(driver, name):
    dismiss_alert(driver)
    try:
        driver.save_screenshot(f"screenshot_{name}.png")
        print(f"  screenshot: {name}.png")
    except Exception as ex:
        print(f"  screenshot failed: {name} ({ex})")

def js_click(driver, el):
    driver.execute_script("arguments[0].click();", el)

def js_fill(driver, el, value):
    driver.execute_script("arguments[0].value = '';", el)
    driver.execute_script("arguments[0].value = arguments[1];", el, value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input', {bubbles:true}));", el)

def is_logged_out(driver):
    dismiss_alert(driver)
    url = driver.current_url.lower()
    if "login" in url or "default.aspx" in url: return True
    try: driver.find_element(By.ID, "txtUserID"); return True
    except: return False

def do_login(driver):
    print("  Logging in...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(4)
    dismiss_alert(driver)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
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
    dismiss_alert(driver)
    if is_logged_out(driver):
        print("  Login failed!")
        shot(driver, "LOGIN_FAILED")
        return False
    print(f"  Logged in! URL: {driver.current_url}")
    return True

def debug_form(driver, label):
    dismiss_alert(driver)
    print(f"  --- DEBUG {label} ---")
    for inp in driver.find_elements(By.TAG_NAME, "input"):
        itype = (inp.get_attribute("type") or "text").lower()
        if itype != "hidden":
            print(f"    INPUT id={inp.get_attribute('id')} ph={inp.get_attribute('placeholder')} type={itype} vis={inp.is_displayed()}")
    for sel in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel)
            print(f"    SELECT id={sel.get_attribute('id')}: {[o.text for o in s.options[:6]]}")
        except: pass
    for ta in driver.find_elements(By.TAG_NAME, "textarea"):
        print(f"    TEXTAREA id={ta.get_attribute('id')}")
    for btn in driver.find_elements(By.TAG_NAME, "button"):
        if btn.text.strip():
            print(f"    BUTTON: '{btn.text.strip()}' id={btn.get_attribute('id')}")
    for inp in driver.find_elements(By.XPATH, "//input[@type='submit' or @type='button']"):
        v = inp.get_attribute("value") or ""
        if v.strip():
            print(f"    BTN-INPUT value={v} id={inp.get_attribute('id')}")

def fill_field(driver, field_ids, value, label):
    for fid in field_ids:
        try:
            el = driver.find_element(By.ID, fid)
            if el.is_displayed():
                js_fill(driver, el, value)
                print(f"  {label} → {fid}")
                return True
        except: continue
    return False

def select_dropdown(driver, keyword, label, skip_ids=None):
    skip_ids = skip_ids or []
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        sid = (sel_el.get_attribute("id") or "").lower()
        if any(s in sid for s in skip_ids): continue
        try:
            s = Select(sel_el)
            opts = [o.text for o in s.options]
            for o in opts:
                if keyword.lower() in o.lower():
                    s.select_by_visible_text(o)
                    print(f"  {label} → {o}")
                    return True
        except: continue
    return False

def click_save(driver):
    dismiss_alert(driver)
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

def open_add_form(driver):
    """Navigate to add form using subAdd JS call — the correct way"""
    driver.get(f"{BASE}/apps/PGLogBook/PGLogBookEntry.aspx")
    time.sleep(3)
    dismiss_alert(driver)

    if is_logged_out(driver):
        return False

    # Call subAdd('A') directly — this is what the Add button does
    try:
        driver.execute_script("subAdd('A');")
        print("  Called subAdd('A')")
        time.sleep(4)
        dismiss_alert(driver)
        return True
    except Exception as ex:
        print(f"  subAdd failed: {ex}")

    # Fallback: try clicking the + Add button
    for selector in [
        "//a[contains(@onclick,'subAdd') or contains(@onclick,'Add')]",
        "//*[contains(@onclick,'subAdd')]",
        "//a[contains(.,'Add') and not(contains(.,'More'))]",
        "//button[contains(.,'Add') and not(contains(.,'More'))]",
        "//*[contains(@class,'btn')][contains(.,'Add') and not(contains(.,'More'))]",
    ]:
        try:
            el = driver.find_element(By.XPATH, selector)
            print(f"  Clicking Add: {el.get_attribute('onclick') or el.text}")
            js_click(driver, el)
            time.sleep(4)
            dismiss_alert(driver)
            return True
        except: continue

    return False

def get_session_opts(driver):
    try:
        s = Select(driver.find_element(By.ID, "cboStudentSessionDetail"))
        return [o.text for o in s.options if "Select" not in o.text and o.text.strip()]
    except: return []

def select_session(driver, session_year):
    opts = get_session_opts(driver)
    print(f"  Session options: {opts}")
    if not opts:
        print("  Session dropdown empty!")
        return False
    try:
        sel_el = driver.find_element(By.ID, "cboStudentSessionDetail")
        s = Select(sel_el)
        for o in [o.text for o in s.options]:
            if session_year in o and "Select" not in o:
                s.select_by_visible_text(o)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                print(f"  Session → {o}")
                time.sleep(3)
                dismiss_alert(driver)
                return True
        # Fallback first available
        for o in [o.text for o in s.options]:
            if "Select" not in o and o.strip():
                s.select_by_visible_text(o)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                print(f"  Session fallback → {o}")
                time.sleep(3)
                dismiss_alert(driver)
                return True
    except Exception as ex:
        print(f"  Session select error: {ex}")
    return False

def do_entry(driver, e, idx):
    print(f"\n[{idx+1:02d}/85] {e['date']} | {e['session']} | {e['fac']} | {e['ctype']} | {e['proc']}")

    # Open the Add form via subAdd('A')
    ok = open_add_form(driver)
    if not ok:
        if is_logged_out(driver):
            print("  Logged out — re-logging in...")
            if not do_login(driver): return False
            ok = open_add_form(driver)
        if not ok:
            shot(driver, f"{idx+1:03d}_ADD_FAILED")
            print("  Could not open Add form"); return False

    shot(driver, f"{idx+1:03d}_a_form")

    # Debug form on first 3 entries
    if idx < 3:
        debug_form(driver, f"ADD_FORM_{idx+1}")

    # Select session year
    session_ok = select_session(driver, e["session"])
    if not session_ok:
        shot(driver, f"{idx+1:03d}_SESSION_FAILED")
        print("  Session selection failed"); return False

    shot(driver, f"{idx+1:03d}_a2_after_session")

    # Debug after session for first 3
    if idx < 3:
        debug_form(driver, f"AFTER_SESSION_{idx+1}")

    # Name of Procedure
    proc_ids = ["txtActivityName","txtProcedureName","txtActivity","txtLogActivity",
                "txtActName","txtProc","txtName","txtTitle","txtLogName","txtActvName"]
    if not fill_field(driver, proc_ids, e["proc"], "Procedure"):
        skip = {"txtApprover","txtUserID","txtPassword","txtFileDescription"}
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid   = inp.get_attribute("id") or ""
            itype = (inp.get_attribute("type") or "text").lower()
            if itype in ["hidden","file","checkbox","radio","submit","button","password"]: continue
            if iid in skip: continue
            if inp.is_displayed():
                js_fill(driver, inp, e["proc"])
                print(f"  Procedure → fallback: {iid}"); break

    # Date
    date_ids = ["txtActivityDate","txtDate","txtLogDate","txtDOA","txtEntryDate","txtActDate","txtDt"]
    if not fill_field(driver, date_ids, e["date"], "Date"):
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid   = (inp.get_attribute("id") or "").lower()
            itype = (inp.get_attribute("type") or "text").lower()
            if "date" in iid and "current" not in iid and itype != "hidden":
                js_fill(driver, inp, e["date"])
                print(f"  Date → {inp.get_attribute('id')}"); break

    # Faculty — txtApprover confirmed
    try:
        el = driver.find_element(By.ID, "txtApprover")
        el.clear(); el.send_keys(e["fac"]); time.sleep(2.5)
        dismiss_alert(driver)
        try:
            sugg = driver.find_elements(By.XPATH,
                "//*[contains(@class,'ui-menu-item') or contains(@class,'autocomplete')]")
            if sugg: js_click(driver, sugg[0])
        except: pass
        print(f"  Faculty → txtApprover: {e['fac']}")
    except Exception as ex:
        print(f"  Faculty error: {ex}")

    # Dropdowns: Procedures, Work Type, Classes, Class Type
    select_dropdown(driver, "Washed", "Procedures", skip_ids=["session"])
    select_dropdown(driver, "Lab",    "WorkType",   skip_ids=["session"])
    select_dropdown(driver, "Attended","Classes",   skip_ids=["session"])
    # Class Type needs special handling for Other vs Seminars
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        sid = (sel_el.get_attribute("id") or "").lower()
        if "session" in sid: continue
        try:
            s = Select(sel_el)
            opts_text = [o.text for o in s.options]
            if any("Other" in o for o in opts_text) and any("Sem" in o for o in opts_text):
                for o in opts_text:
                    if e["ctype"].lower() in o.lower():
                        s.select_by_visible_text(o)
                        print(f"  ClassType → {o}"); break
                break
        except: continue

    # Description
    fill_field(driver,
               ["txtDescription","txtDesc","txtLogDesc","txtRemarks","txtLogDescription"],
               e["desc"], "Description")

    # File Caption — confirmed txtFileDescription
    fill_field(driver, ["txtFileDescription"], e["caption"], "Caption")

    shot(driver, f"{idx+1:03d}_b_before_save")

    # Save
    saved = click_save(driver)
    if not saved:
        debug_form(driver, f"SAVE_MISSING_{idx+1}")
        shot(driver, f"{idx+1:03d}_SAVE_FAILED")
        print("  SAVE FAILED"); return False

    time.sleep(3)
    dismiss_alert(driver)
    shot(driver, f"{idx+1:03d}_c_saved")

    # Checkbox + Submit
    try:
        cb = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
        if not cb.is_selected(): js_click(driver, cb)
        time.sleep(0.5)
    except: pass

    submitted = False
    for selector in ["//input[@value='Submit']","//button[contains(.,'Submit')]","//a[contains(.,'Submit')]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); submitted = True; break
        except: continue

    time.sleep(2.5)
    dismiss_alert(driver)

    if submitted:
        print("  OK submitted"); return True
    else:
        debug_form(driver, f"SUBMIT_MISSING_{idx+1}")
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
                try: shot(driver, f"{i+1:03d}_CRASH")
                except: pass
                fail += 1
            time.sleep(random.uniform(2.5, 4.0))
    finally:
        try: driver.quit()
        except: pass

    print(f"\nFINISHED: {ok} submitted | {fail} failed")
    if fail > 0: sys.exit(1)

if __name__ == "__main__":
    main()
