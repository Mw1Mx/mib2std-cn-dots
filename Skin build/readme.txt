SKIN BUILD

Recommended: back up your original skins on the unit using
GEM > Toolbox > dump > Skins. Keep that dump unchanged and save a copy
on your PC. Use working copies when preparing input.

Windows: Python 3.9 or later is required. Run build.cmd to start.

1. Input - Working skins to convert

Place complete, supported original skin folders here:

input/
`-- skinN/

The folder name selects the destination slot. For example, rename a
working copy to skin3 to build for slot 3, if the project supports it.
Do not use an already converted CN Dots output as input.

You may customize language resource files, artwork inside images.mcf,
and only the skin.displayname value in info.txt. Keep the MCF image IDs
and order, the transparent pixel and any protected SD notice unchanged.
The output name receives the [CN_Dots]- prefix once.

Do not modify images.res, viewhandler.zip or view/skinanim.res.
Do not change any other info.txt property, formatting or line endings,
including its language and locale settings. Editing language resources
does not permit changing those info.txt properties.

Do not alter the original dump, Skin exception references, or the
supplied Projects and data resources.

2. Skin exception - Alternative original reference

If you do not have a Toolbox dump, place a complete, unmodified original
skin folder here. Use this option only if you are sure it belongs to
your unit.

Recommended structure:
Skin exception/
`-- skinN/

Keep the original folder name and files unchanged. Rename only the
working copy placed in input.

Run build.cmd. It launches build.py, which checks the original reference
and the input skin resources to automatically identify the matching
project, firmware and cpu/cpuplus variant.

Firmware and variant folders are not required. Only supported projects
are accepted. If the match is unknown or ambiguous, the build stops.
Skin exception is an alternative reference, not a compatibility bypass.

3. Build

a. Prepare the working copies in input and retain the original references
   in the Toolbox dump or Skin exception.
b. Run build.cmd and check the detected firmware, variant and source skin.
c. Wait for BUILD OK. If the build fails, correct the reported problem;
   do not install an older output by mistake.
d. Follow the root readme.txt to install through GreenMenu.

Use one firmware/variant per output and installation SD. Use a separate
package folder or card for a different firmware. The first build expands
the shared resource pack automatically. Later unchanged builds are skipped.

MST2_EU_VW_PQ_P0480T / cpuplus - Multicolor and Golden

Both appearances use the same supported original multilingual skin1.
The input folder name selects the destination and its appearance.

Example: build both appearances from two copies of the original skin1

a. Keep the original skin1 unchanged in your Toolbox dump or here:

   Skin exception/
   `-- skin1/   Original reference; keep its original folder name

b. Make two working copies of that original skin1 inside input.
   Keep one named skin1 and rename the other to skin4:

   input/
   |-- skin1/   First copy of the original skin1
   `-- skin4/   Second copy of the original skin1, renamed to skin4

c. Run build.cmd. It automatically identifies MST2_EU_VW_PQ_P0480T
   from the supported skin resources. The destination folder selects:

   output/
   |-- skin1/   CN Dots, original VW icons and multicolor
   `-- skin4/   Golden: CN icons, gold particles and gold menu accents

Renaming the original skin1 working copy to input/skin4 is enough to
select Golden. Keep its original reference named skin1 in dump or
Skin exception. Do not use an already converted output as the source.

If input contains only skin1, the builder creates only the multicolor
skin1. If input contains only the renamed skin4 copy, it creates only
Golden skin4. The builder does not automatically create both from one
input folder. dump and Skin exception are references, not build inputs.
Any older folders already present in output are preserved and remain
selected for installation or restoration.

The native Arabic skin4 is not the source for this conversion. Its actual
original contents are backed up on the unit before the replacement.
Optionally set skin.displayname=VW PQ CN Gold in the skin4 working copy
to give the skin a descriptive label. Other custom labels are kept.
For this project, target skin4 selects Golden; other supported target
slots use the original VW icons and multicolor appearance.

4. Output - Compiled skins

The builder creates the compiled skin folders here before installation.
All folders present are selected by the installer and uninstaller.
Do not edit or rename generated folders. Edit input and rebuild instead.

To exclude a skin temporarily, move its output folder outside output.
Removing it only changes the selection; it does not delete backups or
permanently prevent restoration. Put the same generated folder back
under the same name when you want to restore that slot.

Back up the complete SD, including backup/, output/ and toolbox/custom/.
Keeping output alone is not a complete restoration backup.

Both readme.txt files are editable documentation. Their contents are not
used by build.cmd or build.py and are excluded from build validation.
