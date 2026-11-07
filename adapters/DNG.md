# Optional Adobe DNG SDK stage-3 tool

This repository does not include `dng_validate`, the DNG SDK source, or a prebuilt binary.

## Verified public download

Checked 2026-11-07 against Adobe's Digital Negative page:

- Page: <https://helpx.adobe.com/camera-raw/digital-negative.html>
- Go link: <https://www.adobe.com/go/dng_sdk>
- That go link redirected to `https://download.adobe.com/pub/adobe/dng/dng_sdk_1_7_1_2768_20261013.zip`
- Archive size reported by the server: 80,509,918 bytes
- Label on the page and inside `DNG_ReadMe.txt`: **DNG SDK 1.7.1 Build 2768, October 13, 2026**

Download that archive yourself. Read `LICENSE.txt` inside it before you build or share anything you compile. A later Adobe upload can change the file name; start from the go link and confirm the version in the readme.

## License of that SDK archive

`dng_sdk_1_7_1/LICENSE.txt` in Build 2768 is the "DNG SDK License Agreement" (Adobe Inc.). In short, it grants a non-exclusive, worldwide, royalty-free license to use, reproduce, prepare derivative works from, publicly display, publicly perform, distribute, and sublicense the SDK software for any purpose, if you keep the copyright notices. Documentation may be copied for development and distributed, and may not be modified. The software is "AS IS". If you distribute the software in a commercial product, the agreement requires you to defend and indemnify Adobe. Adobe trademarks and the DNG logo are not licensed by that agreement.

That is the SDK software license. It is separate from the DNG Specification patent license published on the same Adobe page. This repository is not granting you Adobe's license; the grant is between you and Adobe when you download the SDK.

`dng_validate` is a sample command-line tool in the SDK. The Build 2768 source (`dng_sdk/source/dng_validate.cpp`) documents:

```text
-3 <file>    Write stage 3 image to "<file>.tif"
-tif <file>  final rendered TIFF
```

Stage 3 is the linear image after demosaic. `-tif` is a different, already-rendered output. `adapters/dng_linear.py` calls `-3`. `adapters/indigo_dng.py` calls `-tif`.

## Build

The SDK readme gives project files, not a universal one-command Linux build:

- macOS: open `dng_sdk/projects/mac/dng_validate.xcodeproj` (Xcode 12.4 through Xcode 26 in the Build 2768 notes)
- Windows: open `dng_sdk/projects/win/dng_validate.sln` (Visual Studio 2022 + clang in those notes)

Point the CLI at your binary:

```bash
export DNG_VALIDATE=/path/to/dng_validate
python adapters/dng_linear.py input.dng stage3.tif
```

`dng_linear.py` reads `AnalogBalance`, `ColorMatrix2`, and `Orientation` from `dng_validate -v`, then converts stage-3 pixels with that matrix into ProPhoto RGB and writes a uint16 TIFF whose ImageDescription is `ProPhoto RGB`. It does not apply ForwardMatrix, RGBTables, ProfileGainTableMap, or opcode lists. Many phone and camera DNGs need those. When they do, this adapter is the wrong tool.

`indigo_dng.py` asks the SDK for its own final render (`-tif`), including the camera profile the SDK understands. That file is display-rendered data, then stored with a ProPhoto transfer curve. It is not the stage-3 path.

LibRaw / rawpy inside `film.py` is a third path: demosaic to linear ProPhoto RGB. It is usable for many classic RAW files and is not a DNG stage-3 decode.
