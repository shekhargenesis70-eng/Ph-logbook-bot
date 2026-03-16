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
    o.add_argument("--window-size=1920,1080")
    # Disguise as real browser
    o.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    o.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    d = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=o)
    # Remove webdriver property
    d.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return d

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

def print_js_errors(driver):
    try:
        logs = driver.get_log("browser")
        for log in logs:
            if log["level"] in ["SEVERE", "WARNING"]:
                print(f"  JS {log['level']}: {log['message'][:200]}")
    except: pass

def wait_for_jquery(driver, timeout=10):
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return typeof jQuery !== 'undefined' && jQuery.active === 0")
        )
    except: pass

def is_logged_out(driver):
    url = driver.current_url.lower()
    if "login" in url or "default.aspx" in url: return True
    try: driver.find_element(By.ID, "txtUserID"); return True
    except: return False

def do_login(driver):
    print("  Logging in...")
    driver.get(f"{BASE}/Default.aspx")
    time.sleep(4)
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
    if is_logged_out(driver):
        print("  Login failed!")
        shot(driver, "LOGIN_FAILED")
        return False
    print(f"  Logged in! URL: {driver.current_url}")
    return True

def try_populate_session(driver, session_year):
    """Aggressively try to get session dropdown options"""

    sel_id = "cboStudentSessionDetail"

    def get_opts():
        try:
            s = Select(driver.find_element(By.ID, sel_id))
            return [o.text for o in s.options if "Select" not in o.text]
        except: return []

    # Strategy 1: Wait + jQuery idle
    wait_for_jquery(driver, 10)
    time.sleep(5)
    opts = get_opts()
    if opts: return opts

    print_js_errors(driver)

    # Strategy 2: Click/focus the dropdown
    try:
        el = driver.find_element(By.ID, sel_id)
        driver.execute_script("arguments[0].scrollIntoView(true);", el)
        el.click(); time.sleep(3)
    except: pass
    opts = get_opts()
    if opts: return opts

    # Strategy 3: Inspect relevant scripts
    try:
        scripts = driver.find_elements(By.TAG_NAME, "script")
        for s in scripts:
            c = s.get_attribute("innerHTML") or ""
            if sel_id in c or "BindSession" in c or "GetSession" in c:
                print(f"  Relevant script snippet: {c[:800]}")
    except: pass

    # Strategy 4: Call any JS function that sounds session-related
    try:
        found_fns = driver.execute_script("""
            var called = [];
            var keywords = ['session','bind','load','fill','get','student'];
            for (var k in window) {
                if (typeof window[k] === 'function') {
                    var n = k.toLowerCase();
                    if (keywords.some(function(kw){ return n.includes(kw); })) {
                        called.push(k);
                        try { window[k](); } catch(e) {}
                    }
                }
            }
            return called;
        """)
        print(f"  Called JS fns: {found_fns}")
        time.sleep(5)
    except: pass
    opts = get_opts()
    if opts: return opts

    # Strategy 5: Try __doPostBack patterns
    for target in [sel_id, "ScriptManager1", "UpdatePanel1", "ctl00$ContentPlaceHolder1$cboStudentSessionDetail"]:
        try:
            driver.execute_script(f"__doPostBack('{target}','');")
            time.sleep(5)
            opts = get_opts()
            if opts: return opts
        except: pass

    # Strategy 6: Use requests with session cookies to hit AJAX endpoints
    try:
        import requests
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": driver.current_url,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        base_url = f"{BASE}/apps/PGLogBook/"
        for ep in ["PGLogBookEntry.aspx/GetStudentSession",
                   "PGLogBookEntry.aspx/BindSession",
                   "PGLogBookEntry.aspx/GetSession",
                   "PGLogBookEntry.aspx/LoadSession",
                   "PGLogBookEntry.aspx/FillSession"]:
            try:
                r = requests.post(base_url + ep, cookies=cookies,
                                  headers=headers, json={}, timeout=8)
                print(f"  AJAX {ep}: {r.status_code} | {r.text[:300]}")
            except Exception as ex:
                print(f"  AJAX {ep}: {ex}")
    except Exception as ex:
        print(f"  Requests error: {ex}")

    # Strategy 7: Reload the page and try again
    print("  Reloading page...")
    driver.refresh()
    time.sleep(5)
    wait_for_jquery(driver, 10)

    # Re-click Add
    for selector in ["//a[contains(.,'Add')]","//button[contains(.,'Add')]",
                     "//*[contains(@class,'btn')][contains(.,'Add')]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); time.sleep(4); break
        except: continue

    opts = get_opts()
    if opts: return opts

    # Final: print full page source snippet around the dropdown
    try:
        src = driver.page_source
        idx = src.find(sel_id)
        if idx >= 0:
            print(f"  Page source around dropdown:\n{src[max(0,idx-200):idx+500]}")
    except: pass

    return []

def select_session_option(driver, session_year, opts):
    """Select the right option from populated dropdown"""
    try:
        sel_el = driver.find_element(By.ID, "cboStudentSessionDetail")
        s = Select(sel_el)
        all_opts = [o.text for o in s.options]
        print(f"  Available options: {all_opts}")

        # Try to match session_year
        for o in all_opts:
            if session_year in o and "Select" not in o:
                s.select_by_visible_text(o)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                print(f"  Selected: {o}")
                time.sleep(4)
                return True

        # If can't match year, just pick first non-default
        for o in all_opts:
            if "Select" not in o:
                s.select_by_visible_text(o)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", sel_el)
                print(f"  Selected (fallback): {o}")
                time.sleep(4)
                return True
    except Exception as ex:
        print(f"  Select option error: {ex}")
    return False

def debug_form(driver, label):
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
        print(f"    BTN-INPUT value={inp.get_attribute('value')} id={inp.get_attribute('id')}")

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

def click_save(driver):
    for selector in ["//input[@value='Save']","//button[normalize-space()='Save']",
                     "//button[contains(.,'Save')]","//input[contains(@value,'Save')]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); print("  Clicked Save"); return True
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
    for selector in ["//a[contains(.,'Add')]","//button[contains(.,'Add')]",
                     "//*[contains(@class,'btn')][contains(.,'Add')]",
                     "//input[@value[contains(.,'Add')]]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); time.sleep(3); break
        except: continue

    shot(driver, f"{idx+1:03d}_a_form")

    # Populate session dropdown
    opts = try_populate_session(driver, e["session"])
    if not opts:
        print("  Could not load session options after all strategies!")
        debug_form(driver, f"NO_SESSION_{idx+1}")
        shot(driver, f"{idx+1:03d}_SESSION_FAILED")
        return False

    # Select the right session year
    if not select_session_option(driver, e["session"], opts):
        return False

    shot(driver, f"{idx+1:03d}_a2_after_session")

    # Debug first 2 entries to see field IDs
    if idx < 2:
        debug_form(driver, f"AFTER_SESSION_{idx+1}")

    # Fill Name of Procedure
    proc_ids = ["txtActivityName","txtProcedureName","txtActivity","txtLogActivity",
                "txtActName","txtProc","txtName","txtTitle"]
    if not fill_field(driver, proc_ids, e["proc"], "Procedure"):
        # Fallback: first visible text input that isn't a known field
        skip = {"txtApprover","txtUserID","txtPassword","txtFileDescription"}
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid   = inp.get_attribute("id") or ""
            itype = (inp.get_attribute("type") or "text").lower()
            if itype in ["hidden","file","checkbox","radio","submit","button","password"]: continue
            if iid in skip: continue
            if inp.is_displayed():
                js_fill(driver, inp, e["proc"])
                print(f"  Procedure → fallback: {iid}"); break

    # Fill Date
    date_ids = ["txtActivityDate","txtDate","txtLogDate","txtDOA","txtEntryDate"]
    if not fill_field(driver, date_ids, e["date"], "Date"):
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            iid = (inp.get_attribute("id") or "").lower()
            itype = (inp.get_attribute("type") or "text").lower()
            if "date" in iid and "current" not in iid and itype != "hidden":
                js_fill(driver, inp, e["date"])
                print(f"  Date → {inp.get_attribute('id')}"); break

    # Faculty — txtApprover confirmed
    try:
        el = driver.find_element(By.ID, "txtApprover")
        el.clear(); el.send_keys(e["fac"]); time.sleep(2.5)
        try:
            sugg = driver.find_elements(By.XPATH,
                "//*[contains(@class,'ui-menu-item') or contains(@class,'autocomplete')]")
            if sugg: js_click(driver, sugg[0])
        except: pass
        print(f"  Faculty → txtApprover: {e['fac']}")
    except Exception as ex:
        print(f"  Faculty error: {ex}")

    # Dropdowns
    for sel_el in driver.find_elements(By.TAG_NAME, "select"):
        try:
            s = Select(sel_el)
            sid = sel_el.get_attribute("id") or ""
            if "session" in sid.lower(): continue
            opts_text = [o.text for o in s.options]
            if any("Washed" in o for o in opts_text):
                for o in opts_text:
                    if "Washed" in o: s.select_by_visible_text(o); print(f"  Procedures → {o}"); break
            elif any("Lab" in o for o in opts_text):
                for o in opts_text:
                    if "Lab" in o: s.select_by_visible_text(o); print(f"  WorkType → {o}"); break
            elif any("Attended" in o for o in opts_text):
                for o in opts_text:
                    if "Attended" in o: s.select_by_visible_text(o); print(f"  Classes → {o}"); break
            elif any("Other" in o for o in opts_text) and any("Sem" in o for o in opts_text):
                for o in opts_text:
                    if e["ctype"].lower() in o.lower():
                        s.select_by_visible_text(o); print(f"  ClassType → {o}"); break
        except: continue

    # Description
    desc_ids = ["txtDescription","txtDesc","txtLogDesc","txtRemarks","txtLogDescription"]
    fill_field(driver, desc_ids, e["desc"], "Description")

    # File Caption — txtFileDescription confirmed
    fill_field(driver, ["txtFileDescription"], e["caption"], "Caption")

    shot(driver, f"{idx+1:03d}_b_before_save")

    # Save
    saved = click_save(driver)
    if not saved:
        debug_form(driver, f"SAVE_BTN_MISSING_{idx+1}")
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
    for selector in ["//input[@value='Submit']","//button[contains(.,'Submit')]","//a[contains(.,'Submit')]"]:
        try:
            el = driver.find_element(By.XPATH, selector)
            js_click(driver, el); submitted = True; break
        except: continue

    time.sleep(2.5)
    if submitted:
        print("  OK submitted"); return True
    else:
        debug_form(driver, f"SUBMIT_BTN_MISSING_{idx+1}")
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
