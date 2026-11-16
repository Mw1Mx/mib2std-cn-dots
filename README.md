# mib2std-cn-dots

Bring Chinese-market dots animations and transitions to European **MIB2 Standard Technisat/Preh PQ & ZR**

Build compatible skins from your unit's original resources, install them through Toolbox, and restore the original files when needed.


### Volkswagen PQ - Golden dots 🟡
<img width="1426" height="1600" alt="IMG-20261112-WA0008(1)" src="https://github.com/user-attachments/assets/48f5d95c-4fb4-4144-b6c8-289f4d4d81be" />


### Seat ZR - Ambient light dots 🚗
<img width="1285" height="938" alt="20261110_165356_1" src="https://github.com/user-attachments/assets/7e0defed-50ba-4919-bfc9-db898b9f0bd2" />



> [!WARNING]
> **Use this project at your own risk.** Modifying incompatible resources or interrupting installation can damage your unit. I am not responsible for partial or permanent damage. Keep your original files and backups.

> **I'm not a programmer.** All the code was written by an AI agent, and reaching a stable, working version for the tested configurations required extensive testing, trial, and error.

> I created this project for personal use and to share it with fellow enthusiasts. Feedback and bug reports are welcome through **Issues**. If you have programming experience, you can also contribute improvements through **Pull Requests**.

Support for additional units is planned. 🔜

## Features

- Particle backgrounds, animations, and transitions adapted from Chinese-market resources.
- Skin building based on supported original resources from your own unit.
- Automatic project, firmware, and hardware variant identification.
- Destination skin selection through the folder names in `input`.
- Support for permitted language, artwork, and display-name customization.
- Backup and selective restoration of installed skins.
- Installation status checks and cleanup tools.
- Multicolor and Golden appearances for Volkswagen PQ.

## Supported firmware 🌐

| Firmware | Hardware variant | Supported original source skins |
| --- | --- | --- |
| `MST2_EU_SE_ZR_P0516T` | `cpu` | `skin2`, `skin4` |
| `MST2_EU_VW_ZR_P0478T` | `cpuplus` | `skin1`, `skin5` |
| `MST2_EU_VW_PQ_P0480T` | `cpuplus` | `skin1` |

For these profiles, `cpu` corresponds to the navigation variant and `cpuplus` to the non-navigation variant.


**A matching firmware name alone does not establish compatibility.**  🔴
The builder checks the original skin resources, and the installer verifies the supported unit resources before making changes.

Each build output and installation SD must use **one firmware and hardware variant**. Use a separate package folder or SD card for another project.

Build, installation, and restoration workflows were checked locally, including simulations; those checks do not establish compatibility with every unit carrying the same firmware name.

## Requirements

- A unit matching one of the supported profiles above.
- [MIB STD2 PQ/ZR Toolbox](https://github.com/olli991/mib-std2-pq-zr-toolbox) installed.
- Access to the Green Engineering Menu, referred to as **GEM** below.
- **Python 3.9 or later**.
- An SD card with enough free space for the package, expanded resources, generated skins, and backups.
- Complete original skin files from your own unit.

## Download ⬇️

Download **`CN Variant dots.zip`** from this repository's **Releases** section.

Choose the prepared ZIP under **Assets**. GitHub's automatic **Source code** archives are not the prepared SD package.

## 1. Back up your original skins

Open in service mode:

```text
GEM > Toolbox > dump > Skins
```

Keep the resulting dump unchanged and save another copy on your PC.

Use working copies of your original skins when preparing a build. Do not edit the original dump.

## 2. Prepare your SD card

Extract the ZIP and copy its contents directly to the root of your SD card.

The main structure should look like this:

```text
SD root/
├── readme.txt
├── custom/
│   └── greenmenu/
│       ├── cn-variant-dots.esd
│       └── scripts/
│           ├── cn_variant_dots.sh
│           ├── cn_variant_dots_clean.sh
│           ├── cn_variant_dots_restore.sh
│           └── cn_variant_dots_status.sh
├── toolbox/
│   └── custom/
│       └── skins/
│           └── cn_variant_dots/
└── Skin build/
    ├── build.cmd
    ├── build.py
    ├── readme.txt
    ├── input/
    ├── Skin exception/
    ├── output/
    └── Projects/
```

This is an overview of the main folders. Keep all other files included in the ZIP.

Do not create an additional folder named `SD root` or `sd`.

Preserve the existing Toolbox files and all backups on your card. Start with a fresh `Skin build` folder and keep any previous package separately.

## 3. Prepare the source skins

### input — Working copies

Place here from dump or supported skin folders:

```text
Skin build/
└── input/
    └── skinN/
```

The working folder name selects the destination slot, where supported by the matching project.

Rename only the working copy in `input`. Keep the original reference under its original name.

I recommend renaming it to a folder number different from the original.

Do not use an already converted CN Dots output as input.

### Permitted customization

You may customize:

- Language resource files.
- PNG Files inside `images.mcf`, while preserving image IDs and order, the transparent pixel, and any protected SD notice.
- Only `skin.displayname` value inside `info.txt`.

The generated display name receives `[CN_Dots]-` prefix once.

Do not modify:

- `images.res`
- `viewhandler.zip`
- `view/skinanim.res`
- Other properties, formatting, or line endings in `info.txt`, including language and locale settings.
- Original files in the Toolbox dump or `Skin exception`.
- Supplied `Projects` resources, manifests, or builder data.

Editing language resources does not permit changing the language or locale properties in `info.txt`.

### Skin exception — Alternative original reference

Using your own Toolbox dump is recommended but if you want to skip this step:

Place a skinN folder in `Skin exception` only if you are certain the files belong to your unit.

```text
Skin build/
└── Skin exception/
    └── skinN/
```

Keep the reference folder's original name and contents unchanged.

Firmware and `cpu`/`cpuplus` subfolders are not required. The builder checks the reference and input resources to identify the matching project automatically.

If the match is unknown or ambiguous, the build stops.

**`Skin exception` is an alternative reference, not a compatibility bypass.**

## 4. Volkswagen PQ: build Multicolor and Golden 🟡

For **`MST2_EU_VW_PQ_P0480T / cpuplus`**, both appearances use the same supported original multilingual **`skin1`**.

| Working folder | Generated appearance |
| --- | --- |
| `input/skin1` | CN Dots with original VW icons and multicolor accents |
| `input/skin4` | Golden: CN icons, gold particles, and gold menu accents |

### Example: create both from two copies of the original skin1

1. Keep the original `skin1` unchanged in your Toolbox dump or in:

   ```text
   Skin exception/
   └── skin1/
   ```

2. Make two working copies of that original `skin1` inside `input`.

3. Keep one named `skin1` and rename the other to `skin4`:

   ```text
   input/
   ├── skin1/    First copy of the original skin1
   └── skin4/    Second copy of the original skin1, renamed
   ```

4. Run `build.cmd`.

5. The builder produces:

   ```text
   output/
   ├── skin1/    Original VW icons and multicolor
   └── skin4/    CN icons and Golden appearance
   ```

Renaming the original `skin1` working copy to **`input/skin4`** is enough to select Golden. The original reference must remain named **`skin1`** in the dump or `Skin exception`.

The native Arabic `skin4` is not the source for this conversion. Its actual original contents are backed up on the unit before replacement.

If `input` contains only `skin1`, only the multicolor `skin1` is generated. If it contains only the renamed `skin4` copy, only Golden `skin4` is generated.

The builder does not automatically create both appearances from one input folder. The dump and `Skin exception` provide references; they are not build inputs.

Existing folders in `output` are preserved and remain selected for installation or restoration.

## 5. Build your skins

On your PC:

1. Check that `input` contains the intended working copies.
2. Keep the original references available in the Toolbox dump or `Skin exception`.
3. Run:

   ```text
   Skin build/build.cmd
   ```

4. Check the detected firmware, hardware variant, and original source skin.
5. Wait for:

   ```text
   BUILD OK
   ```

The first build automatically expands compressed resources and may take longer. Keep `resources.pack.xz` and allow enough free space for expansion.

Later builds skip unchanged results.

If the build fails, resolve the reported problem before installation. Check that you are not about to install an older output left from a previous build.

The smaller download size does not reduce the installed skin size or the unit's memory usage.

### output — Generated skins and slot selection

The builder creates skins in `Skin build/output` before installation.

**Every skin folder present in `output` is selected by the installer and uninstaller.**

Do not edit or rename generated folders. Make changes in `input` and rebuild.

To exclude a slot temporarily, move its generated folder outside `output`. Keep it so you can return the same folder under the same name when restoring that slot.


### Install through GEM

1. Safely eject the prepared SD card from PC and insert it into the unit.
2. Open:

   ```text
   GEM > Toolbox > Customization
   ```

3. If **CN Variant dots** is missing, open **GreenMenu** and select:

   ```text
   Copy custom Green Engineering Menu screens and scripts to unit
   ```

4. Wait until the operation finishes, restart GEM.
5. Open:

   ```text
   GEM > Toolbox > Customization > CN Variant dots
   ```

6. Select:

   ```text
   Install CN Variant dots skins
   ```

7. Wait for a successful result. Keep the SD card inserted and do not interrupt the operation.
8. Restart the unit manually.
After restarting the unit, open **Service menu > Testmode > HMI Skin Change** and select installed CN Dots skin.
10. Use **Check CN Variant dots status** to check the installation.

## 7. Restore the original skins

Use the same SD card with its backups and generated support files intact.

1. Keep the folders for the slots you want to restore in `Skin build/output`.
2. Temporarily move any other output folders elsewhere.
3. Open:

   ```text
   GEM > Toolbox > Customization > CN Variant dots
   ```

4. Select:

   ```text
   Uninstall CN Variant dots skins
   ```

5. Wait for a successful result.
6. Restart the unit manually.

Each selected slot returns to its original contents. When the last managed skin is restored, the original shared configuration is restored too.

Removing a folder from `output` only changes the selection. It does not uninstall the skin or delete its backup.

### Optional cleanup

After all managed skins have been restored, select:

```text
Clean CN Variant dots trace
```

Wait for success and restart the unit manually.

Cleanup is not a substitute for uninstalling the skins. It preserves the SD backups and the GreenMenu screens.

### Keep a complete backup

Back up the complete SD card, especially:

```text
backup/
Skin build/output/
toolbox/custom/
```

Keeping `output` alone is not a complete restoration backup.

## GreenMenu actions

| Action | Purpose |
| --- | --- |
| **Install CN Variant dots skins** | Install the skins selected by the folders in `output` |
| **Uninstall CN Variant dots skins** | Restore the selected slots from their original backups |
| **Check CN Variant dots status** | Check the installation state |
| **Clean CN Variant dots trace** | Clean remaining managed traces after full restoration |


## Additional information.

### Can I use skins from another unit?

Use original skins from your own unit whenever possible. Resources from another unit may be incompatible even when the firmware names look similar.

### Can I build both Volkswagen PQ appearances from one original skin?

Yes. Make two working copies of the supported original `skin1`, name them `input/skin1` and `input/skin4`, then build.

### Does renaming a folder make an unsupported skin compatible?

No. The input folder name selects the destination slot and, where applicable, its appearance. Compatibility is checked from the resources.

### Can I rename a generated output folder?

No. Rename the working copy in `input` and rebuild for the intended destination.

### Will CN Dots be visible on every screen?

Some screens retain opaque backgrounds by design. Do not expect particles to be visible on every screen or list.

## Feedback and contributions

Please use **Issues** for questions, feedback, and bug reports, and **Pull Requests** for proposed improvements.

When reporting a problem, include:

- The exact firmware name.
- Hardware variant from > mib-info.
- The relevant build or installation log.
- A description of the expected and actual behavior.
- Pictures of the visual issue.

Please distinguish between results observed on the unit and checks performed only on a PC.

## Credits

- [MIB STD2 PQ/ZR Toolbox](https://github.com/olli991/mib-std2-pq-zr-toolbox) — the Toolbox used by this project's installation workflow.
- The enthusiasts who test supported configurations and share feedback.
