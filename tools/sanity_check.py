import os
import sys

def check_file_content(path, search_string_lower):
    if not os.path.exists(path):
        return False, f"File not found: {path}"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Perform case-insensitive check to cover True/true
            if search_string_lower.lower() in content.lower():
                return True, "Found"
            else:
                return False, f"String '{search_string_lower}' not found in {path}"
    except Exception as e:
        return False, f"Error reading {path}: {str(e)}"

def check_dir_has_files(path):
    if not os.path.exists(path):
        return False, f"Directory not found: {path}"
    if not os.path.isdir(path):
        return False, f"Path is not a directory: {path}"
    # Check for at least one file
    try:
        # Check for at least one file or directory (hive partitioning uses subdirs)
        items = os.listdir(path)
        if len(items) > 0:
            return True, f"Found {len(items)} items"
        else:
            return False, f"Directory is empty: {path}"
    except Exception as e:
        return False, f"Error accessing {path}: {str(e)}"

def main():
    # Assume script is in tools/sanity_check.py, so root is one level up
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Define paths
    db_path = os.path.join(root_dir, "app", "database.py")
    data_opt_path = os.path.join(root_dir, "data", "optimized")
    main_py_path = os.path.join(root_dir, "app", "main.py")
    dashboard_path = os.path.join(root_dir, "app", "templates", "dashboard.html")

    failed = False

    # 1. Performance-Check
    print("1. Performance-Check: ", end="")
    # Check for hive_partitioning=true (case insensitive to catch =True)
    ok, msg = check_file_content(db_path, "hive_partitioning=true")
    if ok:
        print("OK")
    else:
        print(f"FAIL ({msg})")
        failed = True

    # 2. Daten-Check
    print("2. Daten-Check: ", end="")
    ok, msg = check_dir_has_files(data_opt_path)
    if ok:
        print("OK")
    else:
        print(f"FAIL ({msg})")
        failed = True

    # 3. Config-Check
    print("3. Config-Check: ", end="")
    missing = []
    if not os.path.exists(main_py_path):
        missing.append(f"Missing: {os.path.relpath(main_py_path, root_dir)}")
    if not os.path.exists(dashboard_path):
        missing.append(f"Missing: {os.path.relpath(dashboard_path, root_dir)}")
    
    if not missing:
        print("OK")
    else:
        msg = ", ".join(missing)
        print(f"FAIL ({msg})")
        failed = True
        
    if failed:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
