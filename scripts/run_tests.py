import sys
import xml.etree.ElementTree as ET
import subprocess
import os

def run_tests():
    # Run pytest, generating XML reports for results and coverage
    # We use python -m pytest to ensure we use the same environment
    # pyproject.toml handles coverage options (--cov=src --cov-report=xml)
    cmd = [
        sys.executable, "-m", "pytest",
        "--junitxml=results.xml"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

    # 1. Check Test Failures
    try:
        tree = ET.parse("results.xml")
        root = tree.getroot()
        # root is <testsuites> or <testsuite> depending on pytest version/plugins
        # std pytest junitxml usually outputs a root <testsuites> containing <testsuite>
        # or just <testsuite> if only one.
        
        total_tests = 0
        total_failures = 0
        
        if root.tag == "testsuites":
            for suite in root.findall("testsuite"):
                total_tests += int(suite.get("tests", 0))
                total_failures += int(suite.get("failures", 0))
        elif root.tag == "testsuite":
            total_tests = int(root.get("tests", 0))
            total_failures = int(root.get("failures", 0))
        else:
            print("Unknown XML format for results.xml")
            sys.exit(1)

        if total_tests == 0:
            print("No tests found.")
            # If no tests, maybe we shouldn't fail? Or should we?
            # User said "block if > 20% ... failing". 0/0 is 0%.
            pass 
        else:
            failure_rate = total_failures / total_tests
            print(f"Tests: {total_tests}, Failures: {total_failures}, Rate: {failure_rate:.2%}")
            
            if failure_rate > 0.20:
                print("FAILURE: More than 20% of tests failed.")
                sys.exit(1)
            else:
                print("Test failure rate is within acceptable limits (<= 20%).")

    except FileNotFoundError:
        print("results.xml not found. Did pytest run?")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing results.xml: {e}")
        sys.exit(1)

    # 2. Check Coverage
    try:
        # Simple parsing of coverage.xml from coverage.py
        # <coverage line-rate="0.x" lines-valid="N" ...>
        tree = ET.parse("coverage.xml")
        root = tree.getroot()
        line_rate = float(root.get("line-rate", 0))
        lines_valid = int(root.get("lines-valid", 0))
        
        # Determine Threshold
        if lines_valid < 1000:
            threshold = 0.60
            print(f"Codebase size: {lines_valid} lines (< 1000). Threshold set to 60%.")
        else:
            threshold = 0.80
            print(f"Codebase size: {lines_valid} lines (>= 1000). Threshold set to 80%.")

        print(f"Coverage: {line_rate:.2%}")
        
        if line_rate < threshold:
            print(f"FAILURE: Coverage is less than {threshold:.0%}.")
            sys.exit(1)
        else:
            print(f"Coverage is acceptable (>= {threshold:.0%}).")

    except FileNotFoundError:
        print("coverage.xml not found. Did pytest run?")
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing coverage.xml: {e}")
        sys.exit(1)

    print("SUCCESS: All checks passed.")
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
