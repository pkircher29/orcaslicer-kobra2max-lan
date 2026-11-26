# Kobra 2 Max LAN for OrcaSlicer

Upload OrcaSlicer G-code to a compatible modded Anycubic Kobra 2 Max over SSH, then start it using the printer's touchscreen inside Orca. No Anycubic Cloud, USB drive, or network listener on your PC. This is a separate tab, not Orca's built-in Print Plate button.

## Compatibility and firmware

Windows 11, OrcaSlicer 2.5.2, Ubuntu-24.04 WSL, Windows Python 3.9+, and a Kobra 2 Max with a matching 32-bit Tina/KobraOS build, ED25519-capable Dropbear SSH, and the 480 × 272 framebuffer and `sunxi-ts` input. The original local version was tested on one unlocked 3.1.2 Kobra 2 Max. Stock firmware, other Kobra models, and different touchscreen layouts are not supported. This repo contains no printer firmware, keys, or passwords.

Start with the [historical Anycubic Kobra 2 Series Tools mirror and its flashing instructions](https://github.com/1coderookie/Anycubic-Kobra-2-Series-Tools/blob/8398936ead052906aa084f9796f6c224f9a6b77f/README.md#usage), its [build options](https://github.com/1coderookie/Anycubic-Kobra-2-Series-Tools/blob/main/docs/OPTIONS.md), and [eMMC backup guide](https://github.com/1coderookie/Anycubic-Kobra-2-Series-Tools/blob/main/docs/EMMC_BACKUP.md). [ACK2-Webserver](https://github.com/AGG2017/ACK2-Webserver) documents the optional local web interface; this plugin does not depend on it. Match the exact printer and motherboard revision before flashing and make a recovery backup. Do not flash a generic image just to install the plugin.

## Setup

1. Install [Ubuntu 24.04 for WSL](https://learn.microsoft.com/windows/wsl/install) and launch it once. Inside Ubuntu, run `sudo apt install openssh-client python3` if those commands are missing.
2. Download and extract the [latest release ZIP](https://github.com/pkircher29/orcaslicer-kobra2max-lan/releases). In a Windows terminal, switch into the extracted directory and run `py install.py`. This copies the local Orca plugin and its support files; it does not modify the printer.
3. From the same Windows terminal run `wsl -d Ubuntu-24.04 python3 ./setup-wsl.py`. Enter your printer's private IPv4 address and **independently verified SSH ED25519 fingerprint**. For example, from the printer's trusted serial console run `dropbearkey -y -f /opt/etc/dropbear/dropbear_ed25519_host_key` and use the fingerprint it reports, locating the actual key first if the path differs. Do not trust a fingerprint obtained only from the network being verified. The setup then prompts for root password via OpenSSH to enroll a dedicated public key. The password is not stored. Treat the private key in the WSL Linux home as root-equivalent; protect your Windows account. To revoke it, remove its matching public key from the printer's `authorized_keys`.
4. Save open work, then in Orca use **File → Plugins → Refresh** and activate **Kobra 2 Max LAN**. Approve only the listed local files, threading, and fixed WSL command; do not grant Full Access. If the tab does not appear, restart Orca after saving your work.

## Print

1. Slice with the **Anycubic Kobra 2 Max** profile. Export to the folder shown in the Kobra tab, using a unique `.gcode` name (ASCII letters, digits, underscores, hyphens and dots). Click **Browse exports…**, select the filename, and click **Upload**. It refuses overwrites, checks SHA-256, and never starts a print.
2. Check the bed and filament in person, then use **Refresh screen**. Enable one tap at a time on the live screen: **Print → Local → exact filename → Print**. Confirm the preview filename before the final tap. Watch for heating and advancing progress; don't repeat a start whose result is uncertain. The original firmware sometimes displays a generic preview for Orca files even when it can print them.
3. Check the first layer in person. Do not expose SSH to the internet, start unattended, or bypass any printer safety interlock.

## OrcaCloud catalog

GitHub hosting does not automatically list a plugin in Orca. Users discover catalog entries by signing into OrcaCloud, opening **File → Plugins → Browse plugins**, subscribing, then activating in Orca. [Official instructions](https://www.orcaslicer.com/wiki/plugins/plugins_cloud) · [OrcaCloud Plugin Hub](https://cloud.orcaslicer.com/app/plugins/plugin-hub). This release is a manual GitHub install; it is not listed in OrcaCloud. The catalog publisher flow is behind OrcaCloud sign-in and may require access from Orca's maintainers. The WSL helper setup remains a prerequisite even if the Python page is catalog-listed.

## Build and checks

Helper source is `kobra-touch.c`. Build on a host with Clang and LLD:

```sh
clang --target=armv7a-linux-musleabi -fuse-ld=lld -nostdlib -static -fno-pic -marm -O2 kobra-touch.c -o kobra_touch2.elf
python test_plugin.py
```
