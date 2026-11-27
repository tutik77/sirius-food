pip install -q mutmut 2>/dev/null
for name in $(mutmut results 2>/dev/null | grep survived | awk -F: '{print $1}'); do
  echo "=== $name"
  mutmut show "$name" 2>/dev/null | grep '^[-+] ' | grep -v '^+++\|^---'
done
