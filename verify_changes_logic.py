
def verify_logic():
    # 1. Verify Route Replacement
    route_input = "Luzern, Hubelmatt » Luzern, Bahnhof"
    clean_r = route_input.replace('»', '%')
    print(f"Original: {route_input}")
    print(f"Cleaned : {clean_r}")
    assert clean_r == "Luzern, Hubelmatt % Luzern, Bahnhof"
    
    # 2. Verify Label Formatting
    ptime = "06:30"
    cnt = 42
    label = f"{ptime} (n={cnt})"
    print(f"Label   : {label}")
    assert label == "06:30 (n=42)"

    print("Verification Successful!")

if __name__ == "__main__":
    verify_logic()
