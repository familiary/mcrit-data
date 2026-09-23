# MCRIT Reference Data

This repository contains a collection of reference data that can be used with the MinHash-based Code Relationship & Investigation Toolkit (MCRIT).  
The scope is to cover popular, typically statically linked code that is commonly encountered during binary / malware analysis.
This includes both artefacts introduced by compilers themselves as well as (precompiled) third party libraries that provide access to common algorithms and data structures.

The data found in this repository has been processed with the following tool chain:
* Starting with raw data, typically containing `.LIB` (`.A`) or `.OBJ` (`.O`), optionally 7z was used to extract the contents, then [lib2smda](https://github.com/danielplohmann/lib2smda) has been used to instrument IDA Pro to parse these files, extract their code and symbols and finally export them into individual SMDA disassembly files.  
* These files are then merged into a single SMDA report, performing deduplication per PicHash and Function Symbol if appropriate.  
* Alternatively, `.DLL` and `.EXE` files have been directly processed using SMDA or optionally IDA Pro if `*.PDB` files are available.  
* Finally, the SMDA reports have been submitted once into a vanilla installation of [MCRIT](https://github.com/danielplohmann/mcrit) and the MCRIT export functionality has been used to convert to an immediately usable format.

This repository contains both the final SMDA files and the ready-to-import MCRIT files, which can be imported using Data/Import in MCRITweb or [using the CLI](https://github.com/danielplohmann/mcrit/blob/main/docs/mcrit-cli.md).

This repository is intended to grow over time, as we find time to process more of the scattered artefacts from several previous endeavors.

If you feel that something especially relevant is missing, please open an issue and/or provide input data and we will see what we can do.

Compilers
* [Golang](#gloang)
* [Microsoft Visual Studio](#msvc)
* [MinGW](#mingw)
* [Nim](#nim)
* [Rust](#rust)

Libraries
* [aPLib](#aplibrust)
* [libzlib](#libzlib)

## Compilers

Reference code extracted from all files containing precompiled code found in installations for various compiler toolchains.


### Golang<a id='golang'></a>

Many thanks to Daniel Enders for creating these reference binaries during his Master thesis in 2022!  
Also many thanks to Max Ufer for providing more recent builds of Go versions 1.19-1.22!  
The source file used to compile these included as many Golang standard library files as possible to create coverage for common functions.  
When using these with MCRIT, you probably want to have as few as possible / the most fitting version only as you may otherwise run into performance issues. We noticed that the similarity in Golang library functions can lead to huge candidate clusters for which all functions will have to be matched.


| Name      | Date       | Version                           | MCRIT | SMDA |
|-----------|------------|-----------------------------------|-------|------|
| Golang   | 2014-05-05 | 1.2.2  | [x86](data/Golang/x86/smda/golang_1.2.2_x86.7z) / x64                                           | [x86](data/Golang/x86/mcrit/golang_1.2.2_x86.mcrit) / x64                                               |
| Golang   | 2014-06-18 | 1.3    | [x86](data/Golang/x86/smda/golang_1.3_x86.7z) / [x64](data/Golang/x64/smda/golang_1.3_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.3_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.3_x64.mcrit)   |
| Golang   | 2014-12-10 | 1.4    | [x86](data/Golang/x86/smda/golang_1.4_x86.7z) / [x64](data/Golang/x64/smda/golang_1.4_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.4_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.4_x64.mcrit)   |
| Golang   | 2015-08-19 | 1.5    | [x86](data/Golang/x86/smda/golang_1.5_x86.7z) / [x64](data/Golang/x64/smda/golang_1.5_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.5_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.5_x64.mcrit)   |
| Golang   | 2016-02-17 | 1.6    | [x86](data/Golang/x86/smda/golang_1.6_x86.7z) / [x64](data/Golang/x64/smda/golang_1.6_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.6_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.6_x64.mcrit)   |
| Golang   | 2016-08-15 | 1.7    | [x86](data/Golang/x86/smda/golang_1.7_x86.7z) / [x64](data/Golang/x64/smda/golang_1.7_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.7_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.7_x64.mcrit)   |
| Golang   | 2017-02-16 | 1.8    | [x86](data/Golang/x86/smda/golang_1.8_x86.7z) / [x64](data/Golang/x64/smda/golang_1.8_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.8_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.8_x64.mcrit)   |
| Golang   | 2017-08-24 | 1.9    | [x86](data/Golang/x86/smda/golang_1.9_x86.7z) / [x64](data/Golang/x64/smda/golang_1.9_x64.7z)   | [x86](data/Golang/x86/mcrit/golang_1.9_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.9_x64.mcrit)   |
| Golang   | 2018-02-16 | 1.10   | [x86](data/Golang/x86/smda/golang_1.10_x86.7z) / [x64](data/Golang/x64/smda/golang_1.10_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.10_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.10_x64.mcrit) |
| Golang   | 2018-08-24 | 1.11   | [x86](data/Golang/x86/smda/golang_1.11_x86.7z) / [x64](data/Golang/x64/smda/golang_1.11_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.11_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.11_x64.mcrit) |
| Golang   | 2019-02-25 | 1.12   | [x86](data/Golang/x86/smda/golang_1.12_x86.7z) / [x64](data/Golang/x64/smda/golang_1.12_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.12_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.12_x64.mcrit) |
| Golang   | 2019-09-03 | 1.13   | [x86](data/Golang/x86/smda/golang_1.13_x86.7z) / [x64](data/Golang/x64/smda/golang_1.13_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.13_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.13_x64.mcrit) |
| Golang   | 2020-02-25 | 1.14   | [x86](data/Golang/x86/smda/golang_1.14_x86.7z) / [x64](data/Golang/x64/smda/golang_1.14_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.14_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.14_x64.mcrit) |
| Golang   | 2020-08-11 | 1.15   | [x86](data/Golang/x86/smda/golang_1.15_x86.7z) / [x64](data/Golang/x64/smda/golang_1.15_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.15_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.15_x64.mcrit) |
| Golang   | 2021-02-16 | 1.16   | [x86](data/Golang/x86/smda/golang_1.16_x86.7z) / [x64](data/Golang/x64/smda/golang_1.16_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.16_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.16_x64.mcrit) |
| Golang   | 2021-08-16 | 1.17   | [x86](data/Golang/x86/smda/golang_1.17_x86.7z) / [x64](data/Golang/x64/smda/golang_1.17_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.17_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.17_x64.mcrit) |
| Golang   | 2022-03-15 | 1.18   | [x86](data/Golang/x86/smda/golang_1.18_x86.7z) / [x64](data/Golang/x64/smda/golang_1.18_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.18_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.18_x64.mcrit) |
| Golang   | 2022-08-02 | 1.19   | [x86](data/Golang/x86/smda/golang_1.19_x86.7z) / [x64](data/Golang/x64/smda/golang_1.19_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.19_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.19_x64.mcrit) |
| Golang   | 2023-02-01 | 1.20   | [x86](data/Golang/x86/smda/golang_1.20_x86.7z) / [x64](data/Golang/x64/smda/golang_1.20_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.20_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.20_x64.mcrit) |
| Golang   | 2024-04-03 | 1.21.9 | [x86](data/Golang/x86/smda/golang_1.21_x86.7z) / [x64](data/Golang/x64/smda/golang_1.21_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.21_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.21_x64.mcrit) |
| Golang   | 2024-01-24 | 1.22.2 | [x86](data/Golang/x86/smda/golang_1.22_x86.7z) / [x64](data/Golang/x64/smda/golang_1.22_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.22_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.22_x64.mcrit) |


### Microsoft Visual Studio<a id='msvc'></a>

Having used an installer for the respective version of VS, we crawl its directory structure to discover and process all `*.LIB` and `*.OBJ`, sort them by bitness, and merge the code found into a single file.  
Thanks to Check Point Research for processing VS 2015, 2017, 2019, and 2022.

| Name            | Version | MCRIT                                        | SMDA                                     |
|-----------------|---------|----------------------------------------------|------------------------------------------|
| VS 6    Express | 8168    | [x86](data/MSVC/x86/mcrit/VC6_Express_x86.mcrit)      | [x86](data/MSVC/x86/smda/VC6_Express_x86.7z)     |
| VS 2003 Express | 3077    | [x86](data/MSVC/x86/mcrit/2003_Express_x86.mcrit)      | [x86](data/MSVC/x86/smda/2003_Express_x86.7z)     |
| VS 2005 Express | 50727   | [x86](data/MSVC/x86/mcrit/2005_Express_x86.mcrit)      | [x86](data/MSVC/x86/smda/2005_Express_x86.7z)     |
| VS 2008 Express | -----   | [x86](data/MSVC/x86/mcrit/2005_Express_x86.mcrit)      | [x86](data/MSVC/x86/smda/2005_Express_x86.7z)     |
| VS 2010 Express | 30319   | [x86](data/MSVC/x86/mcrit/2010_Express_x86.mcrit)      | [x86](data/MSVC/x86/smda/2010_Express_x86.7z)     |
| VS 2012 Express | -----   | [x86](data/MSVC/x86/mcrit/2012_Express_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2012_Express_x64.mcrit)     | [x86](data/MSVC/x86/smda/2012_Express_x86.7z) / [x64](data/MSVC/x64/mcrit/2012_Express_x64.mcrit)    |
| VS 2013 Express | -----   | [x86](data/MSVC/x86/mcrit/2013_Express_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2013_Express_x64.mcrit)     | [x86](data/MSVC/x86/smda/2013_Express_x86.7z) / [x64](data/MSVC/x64/mcrit/2013_Express_x64.mcrit)    |
| VS 2015 Pro     | -----   | [x86](data/MSVC/x86/mcrit/2015_Pro_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2015_Pro_x64.mcrit)     | [x86](data/MSVC/x86/smda/2015_Pro_x86.7z) / [x64](data/MSVC/x64/mcrit/2015_Pro_x64.mcrit)    |
| VS 2017 Pro     | -----   | [x86](data/MSVC/x86/mcrit/2017_Pro_x86.mcrit) / [x86-MFC](data/MSVC/x86/mcrit/2017_Pro_mfc_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2017_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2017_Pro_mfc_x64.mcrit)    | [x86](data/MSVC/x86/smda/2017_Pro_x86.7z) / [x86-MFC](data/MSVC/x86/smda/2017_Pro_mfc_x86.7z) / [x64](data/MSVC/x64/mcrit/2017_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2017_Pro_mfc_x64.mcrit)   |
| VS 2019 Pro     | -----   | [x86](data/MSVC/x86/mcrit/2019_Pro_x86.mcrit) / [x86-MFC](data/MSVC/x86/mcrit/2019_Pro_mfc_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2019_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2019_Pro_mfc_x64.mcrit)    | [x86](data/MSVC/x86/smda/2019_Pro_x86.7z) / [x86-MFC](data/MSVC/x86/smda/2019_Pro_mfc_x86.7z) / [x64](data/MSVC/x64/mcrit/2019_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2019_Pro_mfc_x64.mcrit)   |
| VS 2022 Pro     | -----   | x86 / [x86-MFC](data/MSVC/x86/mcrit/2022_Pro_mfc_x86.mcrit) / [x64](data/MSVC/x64/mcrit/2022_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2022_Pro_mfc_x64.mcrit)    | [x86](data/MSVC/x86/smda/2022_Pro_x86.7z) / [x86-MFC](data/MSVC/x86/smda/2022_Pro_mfc_x86.7z) / [x64](data/MSVC/x64/mcrit/2022_Pro_x64.mcrit) / [x64-MFC](data/MSVC/x64/mcrit/2022_Pro_mfc_x64.mcrit)   |

### MinGW<a id='mingw'></a>

Having used an installer for the Windows version of a MinGW release, we crawl its directory structure to discover and process all `*.A` and `*.O`, sort them by bitness, and merge the code found into a single file.


| Name      | Date       | Version                           | MCRIT | SMDA |
|-----------|------------|-----------------------------------|-------|------|
| MinGW r1   | XXXX-XX-XX | - | x86 / x64 | x86 / x64 |
| MinGW r2   | XXXX-XX-XX | - | x86 / x64 | x86 / x64 |
| MinGW r3   | 2012-07-14 | trunk_r5214 gcc4.7.1 binutils cvs-20120714 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.7.1-stable-r3_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.7.1-stable-r3_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.7.1-stable-r3_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.7.1-stable-r3_x64.mcrit) |
| MinGW r4   | 2012-10-27 | v2.0.7      gcc4.7.2 binutils2.23 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.7.2-stable-r4_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.7.2-stable-r4_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.7.2-stable-r4_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.7.2-stable-r4_x64.mcrit) |
| MinGW r5   | 2012-11-04 | v2.0.7      gcc4.7.2 binutils2.23 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.7.2-stable-r5_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.7.2-stable-r5_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.7.2-stable-r5_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.7.2-stable-r5_x64.mcrit) |
| MinGW r6   | 2013-04-13 | v2.0.8      gcc4.7.3 binutils2.23.2 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.7.3-stable-r6_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.7.3-stable-r6_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.7.3-stable-r6_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.7.3-stable-r6_x64.mcrit) |
| MinGW r7   | 2013-04-13 | trunk_r5784 gcc4.8.0 binutils2.23.2 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.8.0-stable-r7_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.8.0-stable-r7_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.8.0-stable-r7_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.8.0-stable-r7_x64.mcrit) |
| MinGW r8   | 2013-06-01 | trunk_r5876 gcc4.8.1 binutils2.23.2 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.8.1-stable-r8_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.8.1-stable-r8_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.8.1-stable-r8_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.8.1-stable-r8_x64.mcrit) |
| MinGW r9   | - | - | x86 / x64 | x86 / x64 |
| MinGW r10  | 2013-11-17 | v3.0.0      gcc4.8.2 binutils2.23.2 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.8.2-stable-r10_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.8.2-stable-r10_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.8.2-stable-r10_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.8.2-stable-r10_x64.mcrit) |
| MinGW r11  | 2014-05-22 | v3.1.0      gcc4.8.3 binutils2.24 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.8.3-stable-r11_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.8.3-stable-r11_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.8.3-stable-r11_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.8.3-stable-r11_x64.mcrit) |
| MinGW r12  | 2014-07-30 | v3.1.0      gcc4.9.1 binutils2.24 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.9.1-stable-r12_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.9.1-stable-r12_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.9.1-stable-r12_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.9.1-stable-r12_x64.mcrit) |
| MinGW r13  | 2014-11-10 | v3.3.0      gcc4.9.2 binutils2.24 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.9.2-stable-r13_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.9.2-stable-r13_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.9.2-stable-r13_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.9.2-stable-r13_x64.mcrit) |
| MinGW r14  | 2015-06-30 | v4.0.2      gcc4.9.3 binutils2.25 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-4.9.3-stable-r14_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-4.9.3-stable-r14_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-4.9.3-stable-r14_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-4.9.3-stable-r14_x64.mcrit) |
| MinGW r15  | 2015-07-10 | v4.0.2      gcc5.1   binutils2.25 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-5.1-stable-r15_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-5.1-stable-r15_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-5.1-stable-r15_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-5.1-stable-r15_x64.mcrit) |
| MinGW r16  | 2015-07-21 | v4.0.2      gcc5.2   binutils2.25 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-5.2-stable-r16_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-5.2-stable-r16_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-5.2-stable-r16_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-5.2-stable-r16_x64.mcrit) |
| MinGW r17  | 2015-12-01 | v4.0.4+     gcc5.2   binutils2.25.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-5.2-stable-r17_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-5.2-stable-r17_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-5.2-stable-r17_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-5.2-stable-r17_x64.mcrit) |
| MinGW r18  | 2015-12-05 | v4.0.4+     gcc5.3   binutils2.25.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-5.3-stable-r18_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-5.3-stable-r18_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-5.3-stable-r18_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-5.3-stable-r18_x64.mcrit) |
| MinGW r19  | 2016-06-14 | v4.0.6      gcc5.4   binutils2.25.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-5.4-stable-r19_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-5.4-stable-r19_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-5.4-stable-r19_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-5.4-stable-r19_x64.mcrit) |
| MinGW r20  | 2016-06-14 | v4.0.6      gcc6.1   binutils2.25.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-6.1-stable-r20_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-6.1-stable-r20_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-6.1-stable-r20_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-6.1-stable-r20_x64.mcrit) |
| MinGW r21  | 2016-09-27 | v4.0.6      gcc6.2   binutils2.27 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-6.2-stable-r21_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-6.2-stable-r21_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-6.2-stable-r21_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-6.2-stable-r21_x64.mcrit) |
| MinGW r22  | 2016-12-29 | v4.0.6      gcc6.3   binutils2.27 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-6.3-stable-r22_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-6.3-stable-r22_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-6.3-stable-r22_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-6.3-stable-r22_x64.mcrit) |
| MinGW r23  | - | - | x86 / x64 | x86 / x64 |
| MinGW r24  | - | - | x86 / x64 | x86 / x64 |
| MinGW r25  | 2017-02-20 | v5.0.1+1    gcc6.3   binutils2.27 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-6.3-stable-r25_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-6.3-stable-r25_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-6.3-stable-r25_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-6.3-stable-r25_x64.mcrit) |
| MinGW r26  | 2017-06-02 | v5.0.2      gcc7.1   binutils2.28 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-7.1-stable-r26_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-7.1-stable-r26_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-7.1-stable-r26_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-7.1-stable-r26_x64.mcrit) |
| MinGW r27  | 2017-08-16 | v5.0.2      gcc7.2   binutils2.29 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-7.2-stable-r27_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-7.2-stable-r27_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-7.2-stable-r27_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-7.2-stable-r27_x64.mcrit) |
| MinGW r28  | 2018-02-07 | v5.0.3      gcc7.3   binutils2.29.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-7.3-stable-r28_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-7.3-stable-r28_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-7.3-stable-r28_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-7.3-stable-r28_x64.mcrit) |
| MinGW r29  | 2018-11-01 | v5.0.4      gcc8.2   binutils2.31.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-8.2-stable-r29_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-8.2-stable-r29_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-8.2-stable-r29_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-8.2-stable-r29_x64.mcrit) |
| MinGW r30  | 2019-02-27 | v6.0.0      gcc8.3   binutils2.31.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-8.3-stable-r30_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-8.3-stable-r30_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-8.3-stable-r30_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-8.3-stable-r30_x64.mcrit) |
| MinGW r31  | 2019-10-14 | v6.0.0      gcc9.2   binutils2.32 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-9.2-stable-r31_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-9.2-stable-r31_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-9.2-stable-r31_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-9.2-stable-r31_x64.mcrit) |
| MinGW r32  | 2020-04-30 | v7.0.0      gcc9.3   binutils2.34 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-9.3-stable-r32_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-9.3-stable-r32_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-9.3-stable-r32_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-9.3-stable-r32_x64.mcrit) |
| MinGW r33  | 2021-02-27 | v8.0.0      gcc10.2  binutils2.36.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-11.2-stable-r33_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-11.2-stable-r33_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-11.2-stable-r33_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-11.2-stable-r33_x64.mcrit) |
| MinGW r34  | 2021-07-13 | v8.0.2      gcc10.3  binutils2.36.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-11.2-stable-r34_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-11.2-stable-r34_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-11.2-stable-r34_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-11.2-stable-r34_x64.mcrit) |
| MinGW r35  | 2021-08-15 | v9.0.0      gcc11.2  binutils2.36.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-11.2-stable-r35_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-11.2-stable-r35_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-11.2-stable-r35_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-11.2-stable-r35_x64.mcrit) |
| MinGW r36  | - | - | x86 / x64 | x86 / x64 |
| MinGW r37  | 2022-04-26 | v10.0.0     gcc11.3  binutils2.38 | x86 / [x64](data/MinGW/x64/smda/mingw-w64-gcc-11.3-stable-r37_x64.7z) | x86 / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-11.3-stable-r37_x64.mcrit) |
| MinGW r38  | 2022-08-23 | v10.0.0     gcc12.2  binutils2.39 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-12.2-stable-r38_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-12.2-stable-r38_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-12.2-stable-r38_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-12.2-stable-r38_x64.mcrit) |



### Nim<a id='nim'></a>

Thanks to [Nim-IDA-FLIRT-Generator](https://github.com/Cisco-Talos/Nim-IDA-FLIRT-Generator) by @hunterbr72, we were able to produce object files for Nim, which we could then turn into MCRIT symbols.

| Name            | Version | MCRIT                                        | SMDA                                     |
|-----------------|---------|----------------------------------------------|------------------------------------------|
| Nim  | 1.2.10    | [x86](data/nim/x86/mcrit/nim-1.2.10_x86.mcrit) / [x64](data/nim/x64/mcrit/nim-1.2.10_x64.mcrit)     | [x86](data/nim/x86/smda/nim-1.2.10_x86.7z) / [x64](data/nim/x64/smda/nim-1.2.10_x64.7z)    |
| Nim  | 1.4.8    | [x86](data/nim/x86/mcrit/nim-1.4.8_x86_incomplete.mcrit) / [x64](data/nim/x64/mcrit/nim-1.4.8_x64_incomplete.mcrit)     | [x86](data/nim/x86/smda/nim-1.4.8_x86_incomplete.7z) / [x64](data/nim/x64/smda/nim-1.4.8_x64_incomplete.7z)    |
| Nim  | 1.6.14    | [x86](data/nim/x86/mcrit/nim-1.6.14_x86.mcrit) / [x64](data/nim/x64/mcrit/nim-1.6.14_x64.mcrit)     | [x86](data/nim/x86/smda/nim-1.6.14_x86.7z) / [x64](data/nim/x64/smda/nim-1.6.14_x64.7z)    |

### Rust<a id='rust'></a>

Ben Herzog wrote a great [reverser's guide to Rust](https://research.checkpoint.com/2023/rust-binary-analysis-feature-by-feature/) and provided some [example binaries](https://github.com/BenH11235/rust-re-tour/tree/main) with full symbols (PDB) and covering different standard library functions.  

| Name      | Date       | Version                           | MCRIT | SMDA |
|-----------|------------|-----------------------------------|-------|------|
| Rust RE-Tour | 2023-06-01 | Rosetta  | x86 / [x64](data/Rust/x64/smda/rust_re_tour_rosetta.7z)                                           |x86 / [x64](data/Rust/x64/mcrit/rust_re_tour_rosetta.mcrit)                                               |


#### Rust crates (matchplate)<a id='rustcrates'></a>

Reference code for the Rust standard library and commonly used crates.io crates, built with matchplate at the exact rustc version, target and release profile of real samples. Each crate is built through its **own test suite**, which instantiates its generics over concrete types — an `.rlib` retains only non-generic code. Every function is deduplicated on `(pic_hash, name)` and ingested per binary, so each crate keeps its own `lib.rust.<crate>` family and `lib.rust.std` is split out via a std donor.

Names: `family=lib.rust.<crate>`, `version=<semver>`, `component=<rustc>-<triple>-<profile>`.

**Pick the point that matches your sample** — rustc version first, then the `lto` axis. Exact-version reference data identified 43.9% more library code than one version off, while further distance costs under a point per version; the `lto` setting separates cleanly while `opt-level` barely does. As with Golang, loading many points at once inflates candidate clusters. A Rust binary usually names its compiler: panic paths embed `/rustc/<commit-hash>/library/...`, and the hash maps to a release in Rust's own channel manifests.

Built with no Microsoft-licensed material (rust-lld, mingw-w64 import libraries, own CRT stubs).

| Name | Date | Version | Compiler | MCRIT | SMDA |
|------|------|---------|----------|-------|------|
| Rust crates | 2023-04-20 | rustc 1.69.0 | x86_64-pc-windows-msvc, opt3-ltofat | [35 MB](data/Rust/x64/mcrit/rust-crates_1.69.0_x86_64-pc-windows-msvc_opt3-ltofat.mcrit) | [13 MB](data/Rust/x64/smda/rust-crates_1.69.0_x86_64-pc-windows-msvc_opt3-ltofat.7z) |
| Rust crates | 2023-11-16 | rustc 1.74.0 | x86_64-unknown-linux-gnu, optz-ltofat | [16 MB](data/Rust/x64/mcrit/rust-crates_1.74.0_x86_64-unknown-linux-gnu_optz-ltofat.mcrit) | [7 MB](data/Rust/x64/smda/rust-crates_1.74.0_x86_64-unknown-linux-gnu_optz-ltofat.7z) |
| Rust crates | 2024-06-13 | rustc 1.79.0 | x86_64-pc-windows-gnu, opt3-ltooff | [22 MB](data/Rust/x64/mcrit/rust-crates_1.79.0_x86_64-pc-windows-gnu_opt3-ltooff.mcrit) | [10 MB](data/Rust/x64/smda/rust-crates_1.79.0_x86_64-pc-windows-gnu_opt3-ltooff.7z) |
| Rust crates | 2024-11-28 | rustc 1.83.0 | x86_64-pc-windows-msvc, opt3-ltooff | [30 MB](data/Rust/x64/mcrit/rust-crates_1.83.0_x86_64-pc-windows-msvc_opt3-ltooff.mcrit) | [11 MB](data/Rust/x64/smda/rust-crates_1.83.0_x86_64-pc-windows-msvc_opt3-ltooff.7z) |
| Rust crates | 2025-05-15 | rustc 1.87.0 | x86_64-pc-windows-msvc, opts-ltooff | [24 MB](data/Rust/x64/mcrit/rust-crates_1.87.0_x86_64-pc-windows-msvc_opts-ltooff.mcrit) | [9 MB](data/Rust/x64/smda/rust-crates_1.87.0_x86_64-pc-windows-msvc_opts-ltooff.7z) |
| Rust crates | 2026-03-05 | rustc 1.94.0 | i686-pc-windows-msvc, optz-ltofat | [33 MB](data/Rust/x86/mcrit/rust-crates_1.94.0_i686-pc-windows-msvc_optz-ltofat.mcrit) | [11 MB](data/Rust/x86/smda/rust-crates_1.94.0_i686-pc-windows-msvc_optz-ltofat.7z) |
| Rust crates | 2026-04-16 | rustc 1.95.0 | x86_64-pc-windows-msvc, optz-ltooff | [37 MB](data/Rust/x64/mcrit/rust-crates_1.95.0_x86_64-pc-windows-msvc_optz-ltooff.mcrit) | [14 MB](data/Rust/x64/smda/rust-crates_1.95.0_x86_64-pc-windows-msvc_optz-ltooff.7z) |




## Libraries

Depending on how the library code is distributed, we extract and convert code similar to the above outlined methodology.
In some cases, we also processed code found "as-is".

### aPLib

aPLib is a popular compression library implementing LZ.  
Dates are estimates based on file timestamps found in distributed files.

| Name   | Date       | Version | Compiler       | MCRIT                                                                                                                                                                                                                                                             | SMDA                                                                                                                                                                                                                                              |
|--------|------------|---------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| aPLib  | 1998-05-03 | 0.12b   | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.12b_coff_aplib.lib.mcrit)                                                                                                                                                                                                   | [x86 PE](data/aPLib/x86/smda/aPLib-0.12b_coff_aplib.lib.7z)                                                                                                                                                                                       |
| aPLib  | 1998-09-23 | 0.17b   | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.17b_coff_aplib.lib.mcrit)                                                                                                                                                                                                   | [x86 PE](data/aPLib/x86/smda/aPLib-0.17b_coff_aplib.lib.7z)                                                                                                                                                                                       |
| aPLib  | 1998-10-03 | 0.18b   | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.18b_coff_aplib.lib.mcrit)                                                                                                                                                                                                   | [x86 PE](data/aPLib/x86/smda/aPLib-0.18b_coff_aplib.lib.7z)                                                                                                                                                                                       |
| aPLib  | 1998-11-05 | 0.19b   | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.19b_coff_aplib.lib.mcrit)                                                                                                                                                                                                   | [x86 PE](data/aPLib/x86/smda/aPLib-0.19b_coff_aplib.lib.7z)                                                                                                                                                                                       |
| aPLib  | 1999-01-14 | 0.20b   | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.20b_coff_aplib.lib.mcrit)                                                                                                                                                                                                   | [x86 PE](data/aPLib/x86/smda/aPLib-0.20b_coff_aplib.lib.7z)                                                                                                                                                                                       |
| aPLib  | 1999-05-26 | 0.22    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.22_coff_aplib.lib.mcrit)                                                                                                                                                                                                    | [x86 PE](data/aPLib/x86/smda/aPLib-0.22_coff_aplib.lib.7z)                                                                                                                                                                                        |
| aPLib  | 2001-01-24 | 0.26    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.26_coff_aplib.lib.mcrit)                                                                                                                                                                                                    | [x86 PE](data/aPLib/x86/smda/aPLib-0.26_coff_aplib.lib.7z)                                                                                                                                                                                        |
| aPLib  | 2002-04-18 | 0.36    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.36_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-0.36_elf_aplib.a.mcrit)                                                                                                                                     | [x86 PE](data/aPLib/x86/smda/aPLib-0.36_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-0.36_elf_aplib.a.7z)                                                                                                                             |
| aPLib  | 2004-10-16 | 0.42    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.42_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-0.42_elf_aplib.a.mcrit)                                                                                                                                     | [x86 PE](data/aPLib/x86/smda/aPLib-0.42_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-0.42_elf_aplib.a.7z)                                                                                                                             |
| aPLib  | 2005-10-08 | 0.43    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.43_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-0.43_elf_aplib.a.mcrit)                                                                                                                                     | [x86 PE](data/aPLib/x86/smda/aPLib-0.43_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-0.43_elf_aplib.a.7z)                                                                                                                             |
| aPLib  | 2008-06-22 | 0.44    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-0.44_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-0.44_elf_aplib.a.mcrit)                                                                                                                                     | [x86 PE](data/aPLib/x86/smda/aPLib-0.44_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-0.44_elf_aplib.a.7z)                                                                                                                             |
| aPLib  | 2009-07-29 | 1.01    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-1.01_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-1.01_elf_aplib.a.mcrit) / [x64 PE](data/aPLib/x64/mcrit/aPLib-1.01_coff64_aplib.lib.mcrit) / [x64 ELF](data/aPLib/x64/mcrit/aPLib-1.01_elf64_aplib.a.mcrit) | [x86 PE](data/aPLib/x86/smda/aPLib-1.01_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-1.01_elf_aplib.a.7z) / [x64 PE](data/aPLib/x64/smda/aPLib-1.01_coff64_aplib.lib.7z) / [x64 ELF](data/aPLib/x64/smda/aPLib-1.01_elf64_aplib.a.7z) |
| aPLib  | 2014-01-20 | 1.10    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-1.10_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-1.10_elf_aplib.a.mcrit) / [x64 PE](data/aPLib/x64/mcrit/aPLib-1.10_coff64_aplib.lib.mcrit) / [x64 ELF](data/aPLib/x64/mcrit/aPLib-1.10_elf64_aplib.a.mcrit) | [x86 PE](data/aPLib/x86/smda/aPLib-1.10_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-1.10_elf_aplib.a.7z) / [x64 PE](data/aPLib/x64/smda/aPLib-1.10_coff64_aplib.lib.7z) / [x64 ELF](data/aPLib/x64/smda/aPLib-1.10_elf64_aplib.a.7z) |
| aPLib  | 2014-07-21 | 1.11    | as distributed | [x86 PE](data/aPLib/x86/mcrit/aPLib-1.11_coff_aplib.lib.mcrit) / [x86 ELF](data/aPLib/x86/mcrit/aPLib-1.11_elf_aplib.a.mcrit) / [x64 PE](data/aPLib/x64/mcrit/aPLib-1.11_coff64_aplib.lib.mcrit) / [x64 ELF](data/aPLib/x64/mcrit/aPLib-1.11_elf64_aplib.a.mcrit) | [x86 PE](data/aPLib/x86/smda/aPLib-1.11_coff_aplib.lib.7z) / [x86 ELF](data/aPLib/x86/smda/aPLib-1.11_elf_aplib.a.7z) / [x64 PE](data/aPLib/x64/smda/aPLib-1.11_coff64_aplib.lib.7z) / [x64 ELF](data/aPLib/x64/smda/aPLib-1.11_elf64_aplib.a.7z) |


### libzlib

zlib is a popular compression library implementing the Deflate algorithm.  
Dates taken from Changelog file / release notes.  
Source lib files taken from the [Shiftmedia project](https://github.com/ShiftMediaProject/zlib).


| Name     | Date       | Version | Compiler       | MCRIT                                                                                                                                                 | SMDA                                                                                                                                            |
|----------|------------|---------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| libzlib  | 2013-04-28 | 1.2.8   | MSVC12         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.8_msvc12_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.8_msvc12_x64_libzlib.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.8_msvc12_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.8_msvc12_x64_libzlib.7z)       |
| libzlib  | 2013-04-28 | 1.2.8   | MSVC14         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.8_msvc14_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.8_msvc14_x64_libzlib.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.8_msvc14_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.8_msvc14_x64_libzlib.7z)       |
| libzlib  | 2016-12-31 | 1.2.9   | MSVC12         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.9_msvc12_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.9_msvc12_x64_libzlib.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.9_msvc12_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.9_msvc12_x64_libzlib.7z)       |
| libzlib  | 2016-12-31 | 1.2.9   | MSVC14         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.9_msvc14_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.9_msvc14_x64_libzlib.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.9_msvc14_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.9_msvc14_x64_libzlib.7z)       |
| libzlib  | 2017-01-02 | 1.2.10  | MSVC12         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.10_msvc12_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.10_msvc12_x64_libzlib.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.10_msvc12_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.10_msvc12_x64_libzlib.7z)     |
| libzlib  | 2017-01-02 | 1.2.10  | MSVC14         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.10_msvc14_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.10_msvc14_x64_libzlib.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.10_msvc14_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.10_msvc14_x64_libzlib.7z)     |
| libzlib  | 2017-01-15 | 1.2.11  | MSVC12         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.11_msvc12_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.11_msvc12_x64_libzlib.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.11_msvc12_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.11_msvc12_x64_libzlib.7z)     |
| libzlib  | 2017-01-15 | 1.2.11  | MSVC14         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.11_msvc14_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.11_msvc14_x64_libzlib.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.11_msvc14_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.11_msvc14_x64_libzlib.7z)     |
| libzlib  | 2017-01-15 | 1.2.11  | MSVC15         | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.11_msvc15_x86_libzlib.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.11_msvc15_x64_libzlib.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.11_msvc15_x86_libzlib.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.11_msvc15_x64_libzlib.7z)     |
