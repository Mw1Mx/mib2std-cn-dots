#!/bin/ksh
# GreenMenu maintenance. Keep the ESD and all four button scripts installed.
fail() { echo "ERROR CN DOTS: $*"; exit 1; }
# CN_PROGRESS_BEGIN
progress() {
    case "${CN_COMPACT_SEEN-}" in *"|$*|"*) return 0;; esac
    CN_COMPACT_SEEN="${CN_COMPACT_SEEN-}|$*|"
    echo "$*" || :
}
# CN_PROGRESS_END
# Read the same firmware and DevInfo fields without starting awk.
# No diagnostic filtering: real read/parse errors remain visible.
metadata_train() {
    sed -n '
/46924065 401 25/h
${
g
s/^[ 	]*//
s/^[^ 	]*[ 	]*//
s/^[^ 	]*[ 	]*//
s/^[^ 	]*[ 	]*//
s/[ 	].*//
s/[^[:print:]]//g
p
}' "$1"
}
metadata_serial() {
    sed -n '
/\.devinfo/h
${
g
s/^.*DevInfo:[ 	]*//
s/[ 	][ 	]*/ /g
s/^ //
s/ $//
/^[^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =]/!s/.*//
s/^[^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =][^ =]*[ =]\([^ =]*\).*$/\1/
p
}'
}

present() { [ -e "$1" ] || [ -L "$1" ]; }
readline() { VALUE=""; IFS= read -r VALUE < "$1"; }
numbered() {
    case "$1" in "$2"[1-9]*) digits=${1#"$2"}; case "$digits" in *[!0-9]*) return 1;; *) return 0;; esac;; *) return 1;; esac
}
slot_ok() { [ "$1" = skin0 ] || numbered "$1" skin; }
regular() { [ -f "$1" ] && [ ! -L "$1" ] && [ -r "$1" ]; }
same() { regular "$1" && regular "$2" && cmp "$1" "$2" >/dev/null 2>&1; }
safe_tree() (
    [ -d "$1" ] && [ ! -L "$1" ] || exit 1
    bad=$(find "$1" ! -type f ! -type d) || exit 1
    [ -z "$bad" ]
)
treecheck() (
    safe_tree "$1" && safe_tree "$2" || exit 1
    for direction in forward reverse; do
        if [ "$direction" = forward ]; then left="$1"; right="$2"; else left="$2"; right="$1"; fi
        (cd "$left" && find . -type f) | while IFS= read -r rel; do same "$left/$rel" "$right/$rel" || exit 1; done || exit 1
        (cd "$left" && find . -type d) | while IFS= read -r rel; do [ -d "$right/$rel" ] || exit 1; done || exit 1
    done
)
subsetcheck() (
    safe_tree "$1" && safe_tree "$2" || exit 1
    (cd "$1" && find . -type f) | while IFS= read -r rel; do same "$1/$rel" "$2/$rel" || exit 1; done || exit 1
    (cd "$1" && find . -type d) | while IFS= read -r rel; do [ -d "$2/$rel" ] || exit 1; done
)
meta() {
    echo "$2" > "$1" || fail "Cannot save metadata: $1"
    readline "$1"; [ "$VALUE" = "$2" ] || fail "Metadata verification failed: $1"
}
case "$ACTION" in status|clean) ;; *) fail "Unknown maintenance action";; esac
for cmd in sed cat cmp find grep; do command -v "$cmd" >/dev/null 2>&1 || fail "Required command missing: $cmd"; done
SD=""
for drive in /media/mp00*; do
    if [ -f "$drive/toolbox/custom/skins/cn_variant_dots/maintenance.sh" ]; then
        [ -z "$SD" ] || fail "Multiple CN Variant dots cards"
        SD="$drive"
    fi
done
[ -n "$SD" ] && [ ! -L "$SD" ] || fail "CN Variant dots SD package missing or linked"
BASE="$SD/toolbox/custom/skins/cn_variant_dots"
REF="$BASE/status_refs"
RES=/tsd/hmi/Resources
ESD=/tsd/etc/persistence/esd
CONFIG=/tsd/hmi/HMI/res/configurationmanager.res
VAULT=/tsd/var/persistence/.persistence.vault
REG="$RES/.cn_dots_multi_v1"
STAGE="$CONFIG.cn-trace-new"
for path in "$BASE" "$REF" "$RES" "$ESD" "$ESD/scripts" "$CONFIG"; do
    [ ! -L "$path" ] || fail "Unexpected link: $path"
done
same /tsd/hmi/tsd.mibstd2.hmi.ifs "$BASE/runtime.ifs" || fail "Runtime does not match the selected project variant"
TRAIN=$(metadata_train "$VAULT") || fail "Cannot read firmware information"
[ "$TRAIN" = "$PROJECT_FIRMWARE" ] || fail "Unsupported firmware"
# Status does not need a serial or a backup SD, and never calls util_info.sh.
regular "$REF/placeholder" || fail "Missing status reference"
for family in cn cn_skin4 stock1 stock2 stock3 stock4 stock5; do
    for rel in images.res viewhandler.zip view/skinanim.res; do
        regular "$REF/$family/$rel" || fail "Incomplete status references: $family/$rel"
    done
done
regular "$REF/common/imageidmap.res" || fail "Missing shared skin reference"
for rel in allowed/stock.res allowed/enabled.res allowed/dynamic_pre_settings.res allowed/dynamic_pre_ecotrainer.res allowed/dynamic_pre_submenus.res configuration.res; do
    regular "$BASE/$rel" || fail "Missing configuration reference: $rel"
done

# SETTINGS_DEFAULT_V1: classify and restore only exact known dynamic revisions.
known_dynamic_config() {
    same "$1" "$BASE/configuration.res" || same "$1" "$BASE/allowed/dynamic_pre_settings.res" || same "$1" "$BASE/allowed/dynamic_pre_ecotrainer.res" || same "$1" "$BASE/allowed/dynamic_pre_submenus.res"
}

# Detect the live animation controllers, independently of results selection,
# cosmetic MCF edits, folder number, and missing/obsolete internal metadata.
classify() {
    CLASS=unknown
    safe_tree "$1" || return
    if unused_slot "$1"; then CLASS=original; return; fi
    for cn_family in cn cn_skin4; do
        for rel in images.res viewhandler.zip view/skinanim.res; do
            if same "$1/$rel" "$REF/$cn_family/$rel"; then CLASS=cn; return; fi
        done
    done
    for family in stock1 stock2 stock3 stock4 stock5; do
        if same "$1/images.res" "$REF/$family/images.res" &&
           same "$1/viewhandler.zip" "$REF/$family/viewhandler.zip" &&
           same "$1/view/skinanim.res" "$REF/$family/view/skinanim.res"; then CLASS=original; return; fi
    done
    # skin0 is the shared resource container, not a selectable visual skin.
    if [ "${1##*/}" = skin0 ] && same "$1/imageidmap.res" "$REF/common/imageidmap.res" &&
       ! present "$1/images.res" && ! present "$1/viewhandler.zip" && ! present "$1/view/skinanim.res"; then
        CLASS=original; return
    fi
    if same "$1/Place images.mcf and or ambienceColorMap.res here" "$REF/placeholder"; then
        entries=$(find "$1" ! -type d) || return
        [ "$entries" = "$1/Place images.mcf and or ambienceColorMap.res here" ] && CLASS=original
    fi
}

echo "Skin folder prepared with cn variant dots..."
FOUND=0; UNKNOWN=0; SCANNED=0
for folder in "$RES"/skin*; do
    present "$folder" || continue
    slot=${folder##*/}
    if ! slot_ok "$slot"; then echo "Unknown skin folder: $slot"; UNKNOWN=1; continue; fi
    SCANNED=$((SCANNED+1))
    classify "$folder"
    case "$CLASS" in
        cn) echo "CN Dots installed in Skin${slot#skin}"; FOUND=$((FOUND+1));;
        original) :;;
        *) echo "Unknown CN Dots status in Skin${slot#skin}: resources need review"; UNKNOWN=1;;
    esac
done
[ "$SCANNED" -gt 0 ] || { echo "No readable skin folders; status unknown"; UNKNOWN=1; }
if [ "$FOUND" -eq 0 ] && [ "$UNKNOWN" -eq 0 ]; then echo "No CN Dots skin folder found"; fi
echo "configurationmanager.res status..."
if known_dynamic_config "$CONFIG"; then
    CONFIG_STATE=dynamic; echo "Dynamic dots installed"
elif same "$CONFIG" "$BASE/allowed/stock.res"; then
    CONFIG_STATE=stock; echo "No Dynamic dots installed"
elif same "$CONFIG" "$BASE/allowed/enabled.res"; then
    CONFIG_STATE=enabled; echo "CN Dots enabled configuration found; not the dynamic configuration"
else
    CONFIG_STATE=unknown; echo "Unknown configurationmanager.res; manual review required"
fi
if [ "$ACTION" = status ]; then
    if present "$REG/active"; then
        for pointer in "$REG/active"/*; do
            present "$pointer" || continue
            echo "Managed installation record: ${pointer##*/} (uninstall before cleaning)"
        done
    fi
    echo "CN DOTS STATUS: inspection complete; nothing changed."
    [ "$UNKNOWN" -eq 0 ] && [ "$CONFIG_STATE" != unknown ]
    exit $?
fi

progress "Checking cleanup requirements..."
[ "$FOUND" -eq 0 ] || fail "Uninstall CN Variant dots skins first; CN skins are still installed"
[ "$UNKNOWN" -eq 0 ] || fail "Unknown skin resources; cleanup blocked"
[ "$CONFIG_STATE" = stock ] || [ "$CONFIG_STATE" = dynamic ] || fail "Unknown or unsupported configuration; cleanup blocked"
for cmd in cp mkdir mount mv rm sync sloginfo; do command -v "$cmd" >/dev/null 2>&1 || fail "Required command missing: $cmd"; done
SERIAL=$(sloginfo | metadata_serial) || fail "Cannot read unit serial"
case "$SERIAL" in ''|----------|*[!A-Za-z0-9_-]*) fail "Invalid unit serial";; esac
UNIT="$SD/backup/$TRAIN/$SERIAL"
BACK="$UNIT/cn_variant_dots_multi_v1"
CLEAN="$UNIT/cn_variant_dots_trace_v1"
for path in "$SD/backup" "$SD/backup/$TRAIN" "$UNIT" "$BACK" "$CLEAN"; do [ ! -L "$path" ] || fail "Linked backup path"; done
safe_tree "$BACK" || fail "Insert the SD containing this unit's Install CN Variant dots backups"

# A COMPLETED cycle proves the normal Uninstall path finished. The latest
# cycle (including an incomplete one) must be considered, not an older success.
LATEST=0; CYCLE=""; SLOTS=""
for cycle in "$BACK"/cycle_*; do
    present "$cycle" || continue
    name=${cycle##*/}; numbered "$name" cycle_ || fail "Invalid backup cycle"
    n=${name#cycle_}
    if [ "$n" -gt "$LATEST" ]; then LATEST="$n"; CYCLE="$name"; fi
    for folder in "$cycle/slots"/*; do
        present "$folder" || continue
        slot=${folder##*/}; slot_ok "$slot" || fail "Invalid saved skin number"
        case " $SLOTS " in *" $slot "*) ;; *) SLOTS="$SLOTS $slot";; esac
    done
done
[ -n "$CYCLE" ] && [ -n "$SLOTS" ] || fail "No installation backups for this unit"
CBACK="$BACK/$CYCLE"
readline "$CBACK/COMPLETED"
[ "$VALUE" = "All managed slots restored" ] || fail "Run Uninstall CN Variant dots skins for all managed skins before cleaning"
same "$CBACK/configuration.before" "$BASE/allowed/stock.res" ||
    known_dynamic_config "$CBACK/configuration.before" || fail "Invalid saved configuration"

if present "$REG"; then
    safe_tree "$REG" || fail "Invalid internal registry"
    CHECKREG="$REG"
    # A stopped recursive removal may have removed only some registry files.
    # Accept that subset only with the verified pre-cleanup registry on this SD.
    if regular "$CLEAN/current_run"; then
        readline "$CLEAN/current_run"; saved_run="$VALUE"
        numbered "$saved_run" run_ || fail "Invalid cleanup pointer"
        saved="$CLEAN/$saved_run"
        if [ -d "$saved/before/registry" ]; then
            readline "$saved/before/cycle"
            if [ "$VALUE" = "$CYCLE" ]; then
                readline "$saved/PREPARED"; [ "$VALUE" = CN_DOTS_TRACE_V1 ] || fail "Cleanup archive not prepared"
                treecheck "$saved/before" "$saved/verify" || fail "Cleanup backup copies differ"
                subsetcheck "$REG" "$saved/before/registry" || fail "Registry changed after cleanup backup"
                CHECKREG="$saved/before/registry"
            fi
        fi
    fi
    [ -d "$CHECKREG/active" ] && [ -d "$CHECKREG/completed" ] || fail "Incomplete internal registry; finish Uninstall"
    for pointer in "$CHECKREG/active"/*; do present "$pointer" && fail "Managed skin still active; finish Uninstall first"; done
    readline "$CHECKREG/cycle"; [ "$VALUE" = "$CYCLE" ] || fail "Registry belongs to another cycle or SD"
    same "$CHECKREG/configuration.before" "$CBACK/configuration.before" || fail "Wrong SD or changed configuration backup"
fi
present "$RES/.cn_dots_multi_v1_init" && fail "Incomplete initialization; finish the previous operation"
for pointer in "$UNIT"/cn_variant_dots*/active "$UNIT"/cn_personal_skin3*/active; do
    present "$pointer" && fail "Legacy active installation needs restoration first"
done

latest_snapshot() {
    SNAP=""; best_cycle=0; best_run=0
    for cycle in "$BACK"/cycle_*; do
        [ -d "$cycle/slots/$1" ] || continue
        name=${cycle##*/}; cn=${name#cycle_}
        for run in "$cycle/slots/$1"/run_*; do
            present "$run" || continue
            name=${run##*/}; numbered "$name" run_ || fail "Invalid slot run"
            rn=${name#run_}
            if [ "$cn" -gt "$best_cycle" ] || { [ "$cn" -eq "$best_cycle" ] && [ "$rn" -gt "$best_run" ]; }; then
                best_cycle="$cn"; best_run="$rn"; SNAP="$run"
            fi
        done
    done
    [ -n "$SNAP" ] || fail "Missing backup for $1"
    readline "$SNAP/COMPLETE"
    [ "$VALUE" = "verified $1 run_$best_run" ] || fail "Incomplete saved skin: $1"
    classify "$SNAP/installed"; [ "$CLASS" = cn ] || fail "Saved installation does not match CN dots: $1"
    classify "$SNAP/original"; [ "$CLASS" = original ] || fail "Saved original still has CN dots or is unknown: $1"
}
for slot in $SLOTS; do
    progress "Comparing files..."
    latest_snapshot "$slot"
    treecheck "$RES/$slot" "$SNAP/original" || fail "$slot was not fully restored or changed since Uninstall"
done

# Only these resource paths may ever be archived/removed. No ESD path is a
# cleanup target; the menu is removed only by the user's Toolbox Restore action.
target_for() {
    case "$1" in
        registry) TARGET="$REG";;
        personal_previous) TARGET="$RES/.cn_personal_skin3_previous";;
        factory_previous) TARGET="$RES/.restore_factory_skin3_previous";;
        multi_skin*)
            part=${1#multi_}; slot=${part%_*}; kind=${part##*_}
            slot_ok "$slot" || fail "Invalid trace slot"
            case " $SLOTS " in *" $slot "*) ;; *) fail "Trace has no original backup: $slot";; esac
            case "$kind" in previous|stage|displaced) ;; *) fail "Invalid trace kind";; esac
            TARGET="$RES/.cn_multi_${slot}_$kind";;
        *) fail "Unknown cleanup target";;
    esac
}
KEYS="registry personal_previous factory_previous"
for slot in $SLOTS; do
    for kind in previous stage displaced; do KEYS="$KEYS multi_${slot}_$kind"; done
done
for path in "$RES"/.cn* "$RES"/.restore_factory_skin3*; do
    present "$path" || continue
    known=0
    for key in $KEYS; do target_for "$key"; [ "$TARGET" = "$path" ] && known=1; done
    [ "$known" -eq 1 ] || fail "Unreviewed CN resource trace: $path"
done
for path in "$CONFIG".cn*; do
    present "$path" || continue
    [ "$path" = "$STAGE" ] || fail "Unfinished configuration operation: $path"
done

# Resume the same incomplete cleanup, or create a new run for a later completed
# installation cycle. Existing installation and cleanup archives never change.
ARCHIVE=""
if present "$CLEAN/current_run"; then
    regular "$CLEAN/current_run" || fail "Invalid cleanup pointer"
    readline "$CLEAN/current_run"; run="$VALUE"; numbered "$run" run_ || fail "Invalid cleanup run"
    previous="$CLEAN/$run"
    safe_tree "$previous" || fail "Invalid cleanup archive"
    readline "$previous/PREPARED"; [ "$VALUE" = "CN_DOTS_TRACE_V1" ] || fail "Incomplete cleanup archive"
    treecheck "$previous/before" "$previous/verify" || fail "Cleanup backup copies differ"
    readline "$previous/before/cycle"; saved_cycle="$VALUE"
    if [ "$saved_cycle" = "$CYCLE" ]; then ARCHIVE="$previous"
    elif [ ! -f "$previous/COMPLETED" ]; then fail "An earlier cleanup is incomplete; keep its original SD"; fi
fi
if [ -z "$ARCHIVE" ]; then
    present "$STAGE" && fail "Untracked cleanup staging file"
    # Validate snapshots of managed recovery dirs before saving any new state.
    for key in $KEYS; do
        target_for "$key"; present "$TARGET" || continue
        safe_tree "$TARGET" || fail "Trace contains links or special files"
        case "$key" in multi_*)
            part=${key#multi_}; slot=${part%_*}; kind=${part##*_}; latest_snapshot "$slot"
            case "$kind" in
                previous) treecheck "$TARGET" "$SNAP/original" || fail "Retained original differs";;
                displaced) treecheck "$TARGET" "$SNAP/installed" || fail "Retained installation differs";;
                stage) treecheck "$TARGET" "$SNAP/original" || treecheck "$TARGET" "$SNAP/installed" || fail "Unknown staging contents";;
            esac;;
        esac
    done
    progress "Saving backups..."
    mkdir -p "$CLEAN" || fail "Cannot create cleanup backup directory"
    n=1; while present "$CLEAN/run_$n"; do n=$((n+1)); done
    ARCHIVE="$CLEAN/run_$n"
    mkdir "$ARCHIVE" "$ARCHIVE/before" || fail "Cannot create cleanup archive"
    cp "$CONFIG" "$ARCHIVE/before/configurationmanager.res" || fail "Cannot save configuration"
    same "$CONFIG" "$ARCHIVE/before/configurationmanager.res" || fail "Configuration backup differs"
    meta "$ARCHIVE/before/cycle" "$CYCLE"
    : > "$ARCHIVE/before/targets" || fail "Cannot create target inventory"
    for key in $KEYS; do
        target_for "$key"; present "$TARGET" || continue
        cp -R "$TARGET" "$ARCHIVE/before/$key" || fail "Cannot save residual: $key"
        treecheck "$TARGET" "$ARCHIVE/before/$key" || fail "Residual backup differs"
        echo "$key" >> "$ARCHIVE/before/targets" || fail "Cannot save target inventory"
    done
    cp -R "$ARCHIVE/before" "$ARCHIVE/verify" || fail "Cannot create backup mirror"
    treecheck "$ARCHIVE/before" "$ARCHIVE/verify" || fail "Backup mirror differs"
    meta "$ARCHIVE/PREPARED" CN_DOTS_TRACE_V1
    meta "$CLEAN/current_run" "run_$n"
    sync
fi
known_dynamic_config "$ARCHIVE/before/configurationmanager.res" ||
    same "$ARCHIVE/before/configurationmanager.res" "$BASE/allowed/stock.res" || fail "Unknown archived configuration"
for key in $KEYS; do
    target_for "$key"; present "$TARGET" || continue
    subsetcheck "$TARGET" "$ARCHIVE/before/$key" || fail "Residual changed since backup"
    grep -x "$key" "$ARCHIVE/before/targets" >/dev/null || fail "Residual missing from inventory"
done
# Check all saved keys through the fixed path resolver before entering rw mode.
while IFS= read -r key; do target_for "$key"; done < "$ARCHIVE/before/targets"
if [ -f "$ARCHIVE/COMPLETED" ]; then
    [ "$CONFIG_STATE" = stock ] || fail "Configuration changed after cleanup"
    for key in $KEYS; do target_for "$key"; present "$TARGET" && fail "New trace after completed cleanup"; done
    present "$STAGE" && fail "Unexpected staging after cleanup"
    echo "CN DOTS CLEAN OK: already clean. Menu retained. Nothing changed."
    exit 0
fi

RW=0
finish() { if [ "$RW" = 1 ]; then sync; mount -t qnx6 -o remount,ro /dev/hd0t177 / || echo "ERROR: Could not remount read-only"; fi; }
trap finish EXIT
progress "Restoring stock configuration..."
mount -t qnx6 -o remount,rw /dev/hd0t177 / || fail "Cannot remount read/write"
RW=1
[ ! -L "$STAGE" ] || fail "Linked configuration staging"
cp -p "$CONFIG" "$STAGE" || fail "Cannot create configuration staging"
cat "$BASE/allowed/stock.res" > "$STAGE" || fail "Cannot write configuration staging"
same "$STAGE" "$BASE/allowed/stock.res" || fail "Staging verification failed"
sync
mv -f "$STAGE" "$CONFIG" || fail "Cannot activate stock configuration; retry Clean before reboot"
same "$CONFIG" "$BASE/allowed/stock.res" || fail "Stock configuration verification failed"
while IFS= read -r key; do
    target_for "$key"; present "$TARGET" || continue
    subsetcheck "$TARGET" "$ARCHIVE/before/$key" || fail "Residual changed before removal"
    progress "Removing traces..."
    rm -rf "$TARGET" || fail "Residual removal incomplete; retry Clean"
    present "$TARGET" && fail "Residual remains; retry Clean"
done < "$ARCHIVE/before/targets"
treecheck "$ARCHIVE/before" "$ARCHIVE/verify" || fail "Cleanup backup changed"
sync
meta "$ARCHIVE/COMPLETED" "Stock configuration restored; resource traces removed; GreenMenu retained"
echo "CN DOTS CLEAN OK: stock configuration restored. Menu and backup SD retained. Restart unit manually."
echo "Cleanup backup saved on SD."
exit 0
