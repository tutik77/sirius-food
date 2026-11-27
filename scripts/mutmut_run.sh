set -e
pip install -q -r requirements-dev.txt mutmut 2>&1 | grep -v notice || true
rm -rf mutants
mutmut run > /dev/null 2>&1 || true
mutmut results --all true | awk '{print $NF}' | sort | uniq -c
mutmut results
