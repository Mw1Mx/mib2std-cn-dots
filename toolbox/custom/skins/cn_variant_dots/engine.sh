#!/bin/ksh
# CN_PROGRESS_BEGIN
progress() {
    case "${CN_COMPACT_SEEN-}" in *"|$*|"*) return 0;; esac
    CN_COMPACT_SEEN="${CN_COMPACT_SEEN-}|$*|"
    echo "$*" || :
}
# CN_PROGRESS_END
# CN_PROGRESS_BEGIN
progress "Checking package..."
# CN_PROGRESS_END
fail() { echo "ERROR: $*"; exit 1; }
valid_slot() {
    case "$1" in
        skin0) return 0;;
        skin[1-9]*)
            digits=${1#skin}
            case "$digits" in *[!0-9]*) return 1;; *) return 0;; esac
            ;;
        *) return 1;;
    esac
}
BASE=""
for drive in /media/mp00*; do
    if [ -f "$drive/toolbox/custom/skins/cn_variant_dots/engine.sh" ]; then
        [ -z "$BASE" ] || fail "Multiple CN Variant dots drives"
        SD="$drive"; BASE="$drive/toolbox/custom/skins/cn_variant_dots"
    fi
done
[ -n "$BASE" ] || fail "CN Variant dots package missing on SD"
ESD=/tsd/etc/persistence/esd
RES=/tsd/hmi/Resources
CONFIG=/tsd/hmi/HMI/res/configurationmanager.res
# SETTINGS_DEFAULT_V1: exact previous dynamic configuration remains upgradeable.
# The original cycle backup is never rewritten when changing this revision.
known_dynamic_config() {
    [ -f "$1" ] && [ ! -L "$1" ] || return 1
    cmp "$1" "$BASE/configuration.res" >/dev/null 2>&1 ||
        cmp "$1" "$BASE/allowed/dynamic_pre_settings.res" >/dev/null 2>&1 ||
        cmp "$1" "$BASE/allowed/dynamic_pre_ecotrainer.res" >/dev/null 2>&1 ||
        cmp "$1" "$BASE/allowed/dynamic_pre_submenus.res" >/dev/null 2>&1
}
for config_ref in configuration.res allowed/dynamic_pre_settings.res allowed/dynamic_pre_ecotrainer.res allowed/dynamic_pre_submenus.res allowed/stock.res; do
    [ -f "$BASE/$config_ref" ] && [ ! -L "$BASE/$config_ref" ] || fail "Missing configuration reference: $config_ref"
done
# Compare complete trees in both directions; reject links and special files.
treecheck() {
    [ -d "$1" ] && [ -d "$2" ] || return 1
# CN_PROGRESS_BEGIN
    progress "Comparing files..."
# CN_PROGRESS_END
    (cd "$1" && find . -type f) | while IFS= read -r rel; do
        cmp "$1/$rel" "$2/$rel" >/dev/null 2>&1 || exit 1
    done || return 1
    (cd "$2" && find . -type f) | while IFS= read -r rel; do
        [ -f "$1/$rel" ] || exit 1
    done || return 1
    (cd "$1" && find . -type d) | while IFS= read -r rel; do
        [ -d "$2/$rel" ] || exit 1
    done || return 1
    (cd "$2" && find . -type d) | while IFS= read -r rel; do
        [ -d "$1/$rel" ] || exit 1
    done || return 1
    [ -z "$(find "$1" "$2" ! -type f ! -type d)" ] || return 1
}
# An unused slot is an empty directory or the exact empty Toolbox placeholder.
# This does not accept a partially missing skin, extra files, links or subfolders.
unused_slot() (
    [ -d "$1" ] && [ ! -L "$1" ] || return 1
    entries=$(find "$1") || return 1
    [ "$entries" = "$1" ] && return 0
    marker="$1/Place images.mcf and or ambienceColorMap.res here"
    [ -f "$marker" ] && [ ! -L "$marker" ] && [ ! -s "$marker" ] || return 1
    [ "$entries" = "$1
$marker" ]
)


rw() {
# CN_PROGRESS_BEGIN
    progress "Preparing changes..."
# CN_PROGRESS_END
    mount -t qnx6 -o remount,rw /dev/hd0t177 / || fail "Cannot mount read/write"
    trap 'sync; mount -t qnx6 -o remount,ro /dev/hd0t177 /' EXIT
}
# Runtime references were selected from a registered Projects profile by build.py.
project_line() {
    PROJECT_VALUE=""
    [ -f "$1" ] && [ ! -L "$1" ] || fail "Missing project metadata; run build.cmd"
    IFS= read -r PROJECT_VALUE < "$1"
}
project_line "$BASE/project_firmware.txt"; PROJECT_FIRMWARE="$PROJECT_VALUE"
case "$PROJECT_FIRMWARE" in MST2_*) ;; *) fail "Invalid project firmware";; esac
case "$PROJECT_FIRMWARE" in *[!A-Za-z0-9_]*) fail "Invalid project firmware";; esac
project_line "$BASE/project_variant.txt"; PROJECT_VARIANT="$PROJECT_VALUE"
case "$PROJECT_VARIANT" in cpu|cpuplus) ;; *) fail "Invalid project variant";; esac

# Maintenance does not use output or the install/restore metadata path.
case "$ACTION" in
    clean|status) . "$BASE/maintenance.sh"; exit $?;;
esac
case "$ACTION" in
install|restore) ;;
*) fail "Unknown action";;
esac
# The menu integration and common validation helpers precede this section.
# CN_PROGRESS_BEGIN
progress "Checking requirements..."
# CN_PROGRESS_END
cmp /tsd/hmi/tsd.mibstd2.hmi.ifs "$BASE/runtime.ifs" >/dev/null 2>&1 || fail "Runtime does not match the selected project variant"
. "$ESD/scripts/util_info.sh"
[ "$TRAIN" = "$PROJECT_FIRMWARE" ] || fail "Unsupported firmware"
case "$SERIAL" in ''|----------|*[!A-Za-z0-9_-]*) fail "Invalid unit serial";; esac
readline() { VALUE=""; IFS= read -r VALUE < "$1"; }
valid_numbered() {
    case "$1" in "$2"_[1-9]*) digits=${1#*_}; case "$digits" in *[!0-9]*) return 1;; *) return 0;; esac;; *) return 1;; esac
}
write_meta() {
    echo "$2" > "$1.new" || fail "Cannot write metadata"
    readline "$1.new"; [ "$VALUE" = "$2" ] || fail "Metadata verification failed"
    mv -f "$1.new" "$1" || fail "Cannot activate metadata"
}
# CN_PROGRESS_BEGIN
progress "Checking requirements..."
# CN_PROGRESS_END
SELECTED=""
RESULTS="$SD/Skin build/output"
[ -d "$RESULTS" ] && [ ! -L "$RESULTS" ] || fail "Missing Skin build/output; run build.cmd"
for candidate in "$RESULTS"/*; do
    [ -e "$candidate" ] || continue
    [ -d "$candidate" ] || continue
    SLOT=${candidate##*/}
    valid_slot "$SLOT" || fail "Invalid selected folder: $SLOT"
    [ ! -L "$candidate" ] || fail "Selected folder is a link"
    META="$BASE/generated/$SLOT"
    [ -f "$META/target_slot.txt" ] || fail "Missing generated slot metadata: $SLOT"
    readline "$META/target_slot.txt"
    [ "$VALUE" = "$SLOT" ] || fail "Folder renamed after generation: $SLOT"
    if [ "$ACTION" = install ]; then
        project_line "$META/profile_firmware.txt"
        [ "$PROJECT_VALUE" = "$PROJECT_FIRMWARE" ] || fail "Selected skin belongs to another firmware: $SLOT"
        project_line "$META/profile_variant.txt"
        [ "$PROJECT_VALUE" = "$PROJECT_VARIANT" ] || fail "Selected skin belongs to another variant: $SLOT"
        project_line "$META/profile_source_skin.txt"; PROFILE_SKIN="$PROJECT_VALUE"
        valid_slot "$PROFILE_SKIN" || fail "Invalid source skin profile"
        echo "$PROFILE_SKIN match with $PROJECT_FIRMWARE >$PROJECT_VARIANT<"
# CN_PROGRESS_BEGIN
progress "Checking requirements..."
# CN_PROGRESS_END
        treecheck "$candidate" "$META/reference" || fail "Generated skin incomplete or changed: $SLOT"
        [ -f "$META/build_id.txt" ] && [ ! -L "$META/build_id.txt" ] || fail "Missing build identifier: run build.cmd"
        readline "$META/build_id.txt"
        [ "${#VALUE}" -eq 64 ] || fail "Invalid build identifier"
        case "$VALUE" in *[!0-9a-f]*) fail "Invalid build identifier";; esac
    fi
    SELECTED="$SELECTED $SLOT"
done
[ -n "$SELECTED" ] || fail "No selected skins in output. Nothing changed."
echo "CN DOTS MULTI: $ACTION selected:$SELECTED"
BACK="$SD/backup/$TRAIN/$SERIAL/cn_variant_dots_multi_v1"
REG="$RES/.cn_dots_multi_v1"
REGSTAGE="$RES/.cn_dots_multi_v1_init"
[ ! -L "$REG" ] && [ ! -L "$REGSTAGE" ] || fail "Invalid internal registry link"
[ ! -f "$SD/backup/$TRAIN/$SERIAL/cn_variant_dots_b1_slots/active" ] || fail "Legacy single-slot install active; migration required"

# CN_PROGRESS_BEGIN
progress "Checking requirements..."
# CN_PROGRESS_END
if [ -d "$REG" ]; then
    readline "$REG/cycle"; CYCLE="$VALUE"
    valid_numbered "$CYCLE" cycle || fail "Invalid internal cycle"
    CBACK="$BACK/$CYCLE"
    [ -d "$REG/active" ] && [ -d "$REG/completed" ] || fail "Incomplete internal registry"
    cmp "$REG/configuration.before" "$CBACK/configuration.before" >/dev/null 2>&1 || fail "Missing SD for this unit or damaged shared backup"
    known_dynamic_config "$CONFIG" || cmp "$CONFIG" "$REG/configuration.before" >/dev/null 2>&1 || fail "Global configuration changed; nothing overwritten"
else
    if [ "$ACTION" = restore ]; then
        echo "CN DOTS MULTI: No managed installation active. Nothing changed."
        exit 0
    fi
    cmp "$CONFIG" "$BASE/allowed/stock.res" >/dev/null 2>&1 || known_dynamic_config "$CONFIG" || fail "Unknown global configuration"
    CYCLE=""; CBACK=""
fi

slot_paths() {
    SLOT="$1"
    TARGET="$RES/$SLOT"
    OLD="$RES/.cn_multi_${SLOT}_previous"
    STAGE="$RES/.cn_multi_${SLOT}_stage"
    HOLD="$RES/.cn_multi_${SLOT}_displaced"
    for path in "$TARGET" "$OLD" "$STAGE" "$HOLD"; do
        [ ! -L "$path" ] || fail "Unexpected link: $SLOT"
    done
}
load_active() {
    readline "$REG/active/$SLOT"; RUN="$VALUE"
    valid_numbered "$RUN" run || fail "Invalid slot backup pointer: $SLOT"
    SNAP="$CBACK/slots/$SLOT/$RUN"
    [ -f "$SNAP/COMPLETE" ] || fail "Slot backup incomplete: $SLOT"
    readline "$SNAP/COMPLETE"
    [ "$VALUE" = "verified $SLOT $RUN" ] || fail "Slot backup marker invalid: $SLOT"
    [ -d "$SNAP/original" ] && [ ! -L "$SNAP/original" ] &&
        [ -d "$SNAP/installed" ] && [ ! -L "$SNAP/installed" ] || fail "Slot backup folders missing: $SLOT"
    [ -f "$SNAP/installed/info.txt" ] && [ ! -L "$SNAP/installed/info.txt" ] || fail "Installed backup info.txt missing: $SLOT"
    if [ ! -f "$SNAP/original/info.txt" ]; then
        unused_slot "$SNAP/original" || fail "Original backup info.txt missing from a non-empty skin: $SLOT"
        # Older installers saved unused folders without an info.txt. Accept only
        # when the independent retained original, or the restored live slot,
        # confirms exactly the same unused state. Never invent a backup file.
        if unused_slot "$OLD" && treecheck "$OLD" "$SNAP/original"; then :
        elif unused_slot "$TARGET" && treecheck "$TARGET" "$SNAP/original"; then :
        else fail "Unused-slot backup cannot be verified against the unit: $SLOT"
        fi
    fi
    if [ -e "$SNAP/previous_run.txt" ]; then
        readline "$SNAP/previous_run.txt"; PREVIOUS_RUN="$VALUE"
        valid_numbered "$PREVIOUS_RUN" run || fail "Invalid previous version pointer: $SLOT"
        [ "$PREVIOUS_RUN" != "$RUN" ] || fail "Invalid self-referencing update"
        PREVIOUS_SNAP="$CBACK/slots/$SLOT/$PREVIOUS_RUN"
        readline "$PREVIOUS_SNAP/COMPLETE"
        [ "$VALUE" = "verified $SLOT $PREVIOUS_RUN" ] || fail "Previous backup incomplete: $SLOT"
        treecheck "$SNAP/original" "$PREVIOUS_SNAP/original" || fail "Original backup chain changed: $SLOT"
        treecheck "$SNAP/previous" "$PREVIOUS_SNAP/installed" || fail "Previous version backup changed: $SLOT"
    elif [ -e "$SNAP/previous" ]; then fail "Previous version pointer missing: $SLOT"
    fi
}
state_slot() {
    if [ -e "$TARGET" ]; then
        if treecheck "$TARGET" "$SNAP/installed"; then STATE=installed
        elif [ -d "$SNAP/previous" ] && treecheck "$TARGET" "$SNAP/previous"; then STATE=previous
        elif treecheck "$TARGET" "$SNAP/original"; then STATE=original
        else fail "Skin changed outside this installer: $SLOT"
        fi
    else STATE=missing
    fi
    if [ -e "$OLD" ]; then treecheck "$OLD" "$SNAP/original" || fail "Original backup differs: $SLOT"; fi
    if [ -e "$HOLD" ]; then
        treecheck "$HOLD" "$SNAP/installed" || treecheck "$HOLD" "$SNAP/previous" || fail "Installed recovery copy differs: $SLOT"
    fi
    if [ "$STATE" != original ]; then
        treecheck "$OLD" "$SNAP/original" || fail "Retained original missing: $SLOT"
    fi
}

# Each update creates a new immutable run. Its original is always the first
# pre-CN skin, while previous is the installed version immediately before it.
prepare_update() {
    PRIOR_RUN="$RUN"; PRIOR_SNAP="$SNAP"
    n=1; while [ -e "$CBACK/slots/$SLOT/run_$n" ]; do n=$((n+1)); done
    RUN="run_$n"; SNAP="$CBACK/slots/$SLOT/$RUN"
    mkdir -p "$SNAP" || fail "Cannot create update backup: $SLOT"
    progress "Saving backups..."
    cp -R "$PRIOR_SNAP/original" "$SNAP/original" || fail "Cannot preserve original backup: $SLOT"
    treecheck "$SNAP/original" "$PRIOR_SNAP/original" || fail "Original update backup mismatch: $SLOT"
    cp -R "$TARGET" "$SNAP/previous" || fail "Cannot save previous version: $SLOT"
    treecheck "$SNAP/previous" "$PRIOR_SNAP/installed" || fail "Previous version backup mismatch: $SLOT"
    cp -R "$RESULTS/$SLOT" "$SNAP/installed" || fail "Cannot save updated build: $SLOT"
    treecheck "$SNAP/installed" "$RESULTS/$SLOT" || fail "Updated build backup mismatch: $SLOT"
    cp "$BASE/generated/$SLOT/build_id.txt" "$SNAP/build_id.txt" || fail "Cannot save build identifier"
    write_meta "$SNAP/previous_run.txt" "$PRIOR_RUN"
    write_meta "$SNAP/COMPLETE" "verified $SLOT $RUN"
    sync
    write_meta "$REG/active/$SLOT" "$RUN"
    sync
    load_active; state_slot
}

# Validate the whole selection before any changes, including inactive/changed slots.
# CN_PROGRESS_BEGIN
progress "Checking requirements..."
# CN_PROGRESS_END
for slot in $SELECTED; do
    slot_paths "$slot"
# CN_PROGRESS_BEGIN
    case "$ACTION" in install) progress "Installing selected skins...";; restore) progress "Restoring selected skins...";; esac
# CN_PROGRESS_END
    if [ -f "$REG/active/$SLOT" ]; then
        load_active; state_slot
        if [ "$ACTION" = install ]; then
            if ! treecheck "$RESULTS/$SLOT" "$SNAP/installed"; then
                [ "$STATE" = installed ] || fail "Finish the pending install or restore before another update: $SLOT"
            fi
        fi
    elif [ "$ACTION" = install ]; then
        [ -d "$TARGET" ] || fail "Destination slot does not exist: $SLOT"
        if [ ! -f "$TARGET/info.txt" ]; then
            unused_slot "$TARGET" || fail "Destination has no info.txt and is not an unused slot: $SLOT"
        fi
        [ -z "$(find "$TARGET" ! -type f ! -type d)" ] || fail "Unsupported files in target: $SLOT"
        for path in "$OLD" "$STAGE" "$HOLD" "$RES/.cn_b1slots_${SLOT}_previous"; do
            [ ! -e "$path" ] || fail "Untracked previous installation: $SLOT"
        done
        if [ "$SLOT" = skin3 ]; then
            [ ! -f "$SD/backup/$TRAIN/$SERIAL/cn_personal_skin3_updates/active" ] || fail "Legacy personal skin3 update recorded; migration required"
        fi
    elif [ -f "$REG/completed/$SLOT" ]; then
        readline "$REG/completed/$SLOT"; RUN="$VALUE"
        valid_numbered "$RUN" run || fail "Invalid completed pointer"
        treecheck "$TARGET" "$CBACK/slots/$SLOT/$RUN/original" || fail "Previously restored slot changed: $SLOT"
    else
        fail "No managed original backup for selected $SLOT. Remove it from output."
    fi
done

if [ -z "$CYCLE" ]; then
    mkdir -p "$BACK" || fail "Cannot create unit backup directory"
    n=1; while [ -e "$BACK/cycle_$n" ]; do n=$((n+1)); done
    CYCLE="cycle_$n"; CBACK="$BACK/$CYCLE"
    mkdir "$CBACK" || fail "Cannot create shared backup"
# CN_PROGRESS_BEGIN
    progress "Saving backups..."
# CN_PROGRESS_END
    cp "$CONFIG" "$CBACK/configuration.before" || fail "Shared config backup failed"
    cmp "$CONFIG" "$CBACK/configuration.before" >/dev/null || fail "Shared config backup mismatch"
    rw
    # A partial registry initialization never changed a skin or the config.
    [ ! -e "$REGSTAGE" ] || rm -rf "$REGSTAGE" || fail "Cannot clear registry staging"
    mkdir -p "$REGSTAGE/active" "$REGSTAGE/completed" || fail "Cannot stage registry"
# CN_PROGRESS_BEGIN
    progress "Saving backups..."
# CN_PROGRESS_END
    cp "$CONFIG" "$REGSTAGE/configuration.before" || fail "Internal config backup failed"
    cmp "$CONFIG" "$REGSTAGE/configuration.before" >/dev/null || fail "Internal config mismatch"
    write_meta "$REGSTAGE/cycle" "$CYCLE"
    mv "$REGSTAGE" "$REG" || fail "Cannot activate registry"
fi

set_config() {
    if cmp "$1" "$CONFIG" >/dev/null 2>&1; then return 0; fi
# CN_PROGRESS_BEGIN
    progress "Updating configuration..."
# CN_PROGRESS_END
    cp "$1" "$CONFIG.cn-multi-new" || fail "Config staging failed"
    cmp "$1" "$CONFIG.cn-multi-new" >/dev/null || fail "Config staging mismatch"
    mv -f "$CONFIG.cn-multi-new" "$CONFIG" || fail "Config activation failed; retry action before reboot"
    cmp "$1" "$CONFIG" >/dev/null || fail "Config verification failed"
}
rw
for slot in $SELECTED; do
    slot_paths "$slot"
# CN_PROGRESS_BEGIN
    case "$ACTION" in install) progress "Installing selected skins...";; restore) progress "Restoring selected skins...";; esac
# CN_PROGRESS_END
    if [ "$ACTION" = install ]; then
        if [ -f "$REG/active/$SLOT" ]; then
            load_active; state_slot
            if ! treecheck "$RESULTS/$SLOT" "$SNAP/installed"; then
                progress "Updating selected skins..."
                prepare_update
            elif [ "$STATE" = installed ]; then
                # No skin or backup write for a repeated, byte-identical build.
                [ ! -e "$HOLD" ] || rm -rf "$HOLD" || fail "Cannot finish update recovery"
                [ ! -e "$STAGE" ] || rm -rf "$STAGE" || fail "Cannot finish staging recovery"
                set_config "$BASE/configuration.res"
                echo "CN VARIANT DOTS SKIPPED: $SLOT is unchanged"
                continue
            fi
        else
            n=1; while [ -e "$CBACK/slots/$SLOT/run_$n" ]; do n=$((n+1)); done
            RUN="run_$n"; SNAP="$CBACK/slots/$SLOT/$RUN"
            mkdir -p "$SNAP" || fail "Cannot create $SLOT backup"
# CN_PROGRESS_BEGIN
    progress "Saving backups..."
# CN_PROGRESS_END
            cp -R "$TARGET" "$SNAP/original" || fail "Original backup failed: $SLOT"
            treecheck "$TARGET" "$SNAP/original" || fail "Original backup mismatch: $SLOT"
# CN_PROGRESS_BEGIN
    progress "Saving backups..."
# CN_PROGRESS_END
            cp -R "$RESULTS/$SLOT" "$SNAP/installed" || fail "Installed snapshot failed: $SLOT"
            treecheck "$RESULTS/$SLOT" "$SNAP/installed" || fail "Installed snapshot mismatch: $SLOT"
            cp "$BASE/generated/$SLOT/build_id.txt" "$SNAP/build_id.txt" || fail "Cannot save build identifier"
            write_meta "$SNAP/COMPLETE" "verified $SLOT $RUN"
            write_meta "$REG/active/$SLOT" "$RUN"
            sync
            STATE=original
        fi
        set_config "$BASE/configuration.res"
        if [ "$STATE" != installed ]; then
            [ ! -e "$STAGE" ] || rm -rf "$STAGE" || fail "Cannot clear slot staging"
# CN_PROGRESS_BEGIN
    progress "Installing selected skins..."
# CN_PROGRESS_END
            cp -R "$SNAP/installed" "$STAGE" || fail "Skin staging failed: $SLOT. Retry or restore selected."
            treecheck "$STAGE" "$SNAP/installed" || fail "Skin staging mismatch: $SLOT"
            sync
# CN_PROGRESS_BEGIN
    progress "Installing selected skins..."
# CN_PROGRESS_END
            if [ "$STATE" = original ]; then
                [ ! -e "$OLD" ] || fail "Ambiguous original recovery state: $SLOT"
                mv "$TARGET" "$OLD" || fail "Cannot retain original: $SLOT"
            elif [ "$STATE" = previous ]; then
                [ ! -e "$HOLD" ] || rm -rf "$HOLD" || fail "Cannot clear verified recovery copy"
                mv "$TARGET" "$HOLD" || fail "Cannot retain previous version: $SLOT"
            fi
            if ! mv "$STAGE" "$TARGET"; then
                if [ -d "$HOLD" ]; then
                    mv "$HOLD" "$TARGET" || fail "Activation failed; restore selected before reboot: $SLOT"
                else
                    mv "$OLD" "$TARGET" || fail "Activation failed; restore selected before reboot: $SLOT"
                fi
                fail "Activation failed; previous skin recovered: $SLOT"
            fi
        fi
# CN_PROGRESS_BEGIN
    progress "Verifying changes..."
# CN_PROGRESS_END
        treecheck "$TARGET" "$SNAP/installed" || fail "Final verification failed: $SLOT"
        treecheck "$OLD" "$SNAP/original" || fail "Retained original verification failed: $SLOT"
        [ ! -e "$HOLD" ] || rm -rf "$HOLD" || fail "Cannot finish update recovery"
        echo "CN VARIANT DOTS OK: install $SLOT"
    else
        if [ ! -f "$REG/active/$SLOT" ]; then
            echo "CN VARIANT DOTS OK: already restored $SLOT"
            continue
        fi
        load_active; state_slot
        if [ "$STATE" != original ]; then
            [ ! -e "$STAGE" ] || rm -rf "$STAGE" || fail "Cannot clear restore staging"
# CN_PROGRESS_BEGIN
    progress "Restoring selected skins..."
# CN_PROGRESS_END
            cp -R "$SNAP/original" "$STAGE" || fail "Restore staging failed: $SLOT"
            treecheck "$STAGE" "$SNAP/original" || fail "Restore staging mismatch: $SLOT"
            sync
# CN_PROGRESS_BEGIN
    progress "Restoring selected skins..."
# CN_PROGRESS_END
            if [ "$STATE" = installed ] || [ "$STATE" = previous ]; then
                [ ! -e "$HOLD" ] || rm -rf "$HOLD" || fail "Cannot clear own holding copy"
                mv "$TARGET" "$HOLD" || fail "Cannot retain installed skin: $SLOT"
            fi
            if ! mv "$STAGE" "$TARGET"; then
                if [ -d "$HOLD" ]; then mv "$HOLD" "$TARGET"; fi
                fail "Restore activation failed: $SLOT. Retry before reboot."
            fi
        fi
# CN_PROGRESS_BEGIN
    progress "Verifying changes..."
# CN_PROGRESS_END
        treecheck "$TARGET" "$SNAP/original" || fail "Restored skin mismatch: $SLOT"
        # Keep the active pointer until cleanup is complete. Repetition is safe.
# CN_PROGRESS_BEGIN
    progress "Finishing restoration..."
# CN_PROGRESS_END
        for path in "$STAGE" "$HOLD" "$OLD"; do
            [ ! -e "$path" ] || rm -rf "$path" || fail "Cannot finish recovery cleanup: $SLOT"
        done
        mv -f "$REG/active/$SLOT" "$REG/completed/$SLOT" || fail "Cannot complete slot restoration"
        echo "CN VARIANT DOTS OK: restore $SLOT"
    fi
    sync
done

# CN_PROGRESS_BEGIN
    progress "Verifying changes..."
# CN_PROGRESS_END
REMAINING=""
for path in "$REG/active"/*; do
    [ -f "$path" ] || continue
    slot=${path##*/}; valid_slot "$slot" || fail "Unexpected registry entry"
    REMAINING="$REMAINING $slot"
done
if [ -n "$REMAINING" ]; then
    set_config "$BASE/configuration.res"
    echo "CN DOTS MULTI: Shared animation configuration retained. Active:$REMAINING"
else
# CN_PROGRESS_BEGIN
    progress "Restoring previous configuration..."
# CN_PROGRESS_END
    set_config "$REG/configuration.before"
    cmp "$CONFIG" "$CBACK/configuration.before" >/dev/null || fail "Original shared config verification failed"
    echo "All managed slots restored" > "$CBACK/COMPLETED" || fail "Cannot mark completed cycle"
    rm -rf "$REG" || fail "Cannot close completed registry"
    echo "CN DOTS MULTI: Last skin removed; previous global configuration restored."
fi
sync
echo "CN DOTS MULTI OK: $ACTION selected skins. Restart unit manually."
exit 0
