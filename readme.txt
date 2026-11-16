CN VARIANT DOTS by Mw1Mx salu2 :)

CN Dots animations and transitions from Chinese-market MIB2 Technisat
units, adapted to supported PQ and ZR units running European firmware.

Use original skins from your own unit to reduce compatibility risks.
Use this project at your own risk. I am not responsible for any damage
to your unit, including permanent damage.

1. Prepare your SD card

Toolbox must already be installed and working on your unit.
Extract this ZIP and copy its contents to the root of your SD card:

SD root/
|-- readme.txt
|-- custom/
|   `-- greenmenu/
|       |-- cn-variant-dots.esd
|       `-- scripts/
|           |-- cn_variant_dots.sh
|           |-- cn_variant_dots_clean.sh
|           |-- cn_variant_dots_restore.sh
|           `-- cn_variant_dots_status.sh
|-- toolbox/
|   `-- custom/
|       `-- skins/
|           `-- cn_variant_dots/
`-- Skin build/

Do not create an extra folder named "SD root" or "sd".
Keep the existing Toolbox files and all backups on your card. Start with
a fresh Skin build folder; keep any previous package separately.

2. Back up your original skins

Recommended: on the unit, use GEM > Toolbox > dump > Skins.
Keep the resulting dump unchanged and save another copy on your PC.

3. Build your skins on the PC

Follow Skin build/readme.txt to prepare input and the original references.
Run Skin build/build.cmd and wait for BUILD OK. Python 3.9 or later is
required. The first run automatically expands the compressed resources
and needs additional time and free space. Keep resources.pack.xz.

The smaller ZIP does not reduce installed skin size or unit memory use.
All folders present in Skin build/output are selected for installation.

4. Install on the unit

If a private toolbox.sh trial is still installed, first restore it using
its matching restore script, original SD package and backups. For the
PQ skin1 + skin4 visual trial, use RESTORE_CN_VISUAL_PQ.sh.
For the earlier PQ skin1-only trial, use RESTORE_CN_DOTS_PQ.sh.
For the VW ZR private trial, use RESTORE_CN_DOTS_VW.sh.
Restart the unit after restoration, then continue with this package.

a. Safely eject the prepared SD from the PC and insert it into the unit.
b. Open GEM > Toolbox > Customization.
c. If CN Variant dots is missing, open GreenMenu and select:
   "Copy custom Green Engineering Menu screens and scripts to unit".
   Wait until it finishes, restart the unit and open GEM again.
d. Open GEM > Toolbox > Customization > CN Variant dots.
e. Select "Install CN Variant dots skins".
f. Wait for success. Do not remove the SD or interrupt the operation.
g. Restart the unit manually. If needed, select the destination skin
   using your unit's normal skin selection controls.
h. Use "Check CN Variant dots status" to check the installation.

5. Restore your original skins

Use the same SD with its backups and generated support files intact.
Keep the folders you want to restore in Skin build/output. Move other
output folders elsewhere temporarily if you want to exclude them.

Open GEM > Toolbox > Customization > CN Variant dots and select
"Uninstall CN Variant dots skins". Wait for success, then restart the
unit manually. Each selected slot returns to its original contents.
When the last managed skin is restored, the original shared configuration
is restored too.

After all skins are restored, you may use "Clean CN Variant dots trace".
This is optional and is not a substitute for uninstalling the skins.

Back up the complete SD, especially backup/, Skin build/output/ and
toolbox/custom/. Removing a folder from output only changes the selection;
it does not delete the unit's skin or its backup. Keep the generated
folder so you can put it back under the same name when restoring it.

Both readme.txt files are documentation only. You may edit them without
affecting build.cmd, build.py or resource validation.
