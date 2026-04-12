from backend.report_parser import extract_parameters as ep

def run_test(name, text):
    results = ep(text)
    print(f"--- {name} ---")
    if results:
        for k, v in results.items():
            print(f"  {k}: value={v['value']}, range={v['ref_range']}, status={v['status']}")
    else:
        print("  NO RESULTS")

# Test 1: Vertical bars (common in tables)
run_test("Vertical Bars", "Calcium Serum | 8.9 | mg/dL | 8.4 - 10.2")

# Test 2: Spaces around dots (common in OCR)
run_test("Spaces around dots", "Calcium Serum  8 . 9  mg/dL  8 . 4 - 10 . 2")

# Test 3: Comma as decimal
run_test("Comma Decimal", "Calcium Serum  8,9  mg/dL  8,4 - 10,2")

# Test 4: Messy units
run_test("Messy Units", "Calcium Serum   8.9  mg / dL   8.4-10.2")

# Test 5: No dash in range (common OCR failure)
run_test("No Dash In Range", "Calcium Serum  8.9  mg/dL  8.4 10.2")
