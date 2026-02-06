phantom-api() {
  local d=${UNVEIL_DELAY:-0.04}
  command phantom-api "$@" | while IFS= read -r l; do
    printf '%s\n' "$l"
    sleep "$d"
  done
  read -n 1 -s -r
}