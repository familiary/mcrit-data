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

Entries marked *Generated with `scripts/build_corpus.py`* came a second way, which needs neither IDA Pro nor a prebuilt binary to start from: unmodified upstream source is fetched against a pinned tag or digest, built with mingw-w64 and with MSVC v143 on a Windows runner, and disassembled with SMDA directly. Most families carry both, from the same upstream tag, because a MinGW reference matches a MinGW-built binary well and an MSVC-built one only weakly; three of them are MSVC-only, because ATL, the DIA SDK and MASM have no GCC equivalent. What it produces is byte-compatible with the rest of the corpus — the minhash and shingler configuration hashes are checked against the existing exports on every run — and every artefact records its source URL and digest, compiler, build flags and dependency versions in `data/<family>/provenance.json`. Compiler runtime that every binary links in is measured against a project-free probe and removed, so it stays attributed to the toolchain rather than to the library. See `scripts/corpus/README.md`.

This repository is intended to grow over time, as we find time to process more of the scattered artefacts from several previous endeavors.

If you feel that something especially relevant is missing, please open an issue and/or provide input data and we will see what we can do.

Compilers
* [Golang](#golang)
* [Microsoft Visual Studio](#msvc)
* [MinGW](#mingw)
* [Nim](#nim)
* [Rust](#rust)

Libraries
* [aPLib](#aplib)
* [libzlib](#libzlib)
* [bzip2](#bzip2)
* [cJSON](#cjson)
* [libcurl](#libcurl)
* [libevent](#libevent)
* [liblzma](#liblzma)
* [libsodium](#libsodium)
* [libtomcrypt](#libtomcrypt)
* [libuv](#libuv)
* [libxml2](#libxml2)
* [lz4](#lz4)
* [mbedTLS](#mbedtls)
* [pcre2](#pcre2)
* [sqlite3](#sqlite3)
* [libpng](#libpng)
* [libtiff](#libtiff)
* [wolfSSL](#wolfssl)
* [OpenSSL](#openssl)
* [Crypto++](#cryptopp)
* [7-Zip](#7-zip)
* [PCRE](#pcre)
* [abseil](#abseil)
* [re2](#re2)
* [protobuf](#protobuf)
* [nlohmann/json](#nlohmann_json)
* [jemalloc](#jemalloc)
* [libstdc++](#libstdcxx)

Runtimes
* [Lua](#lua)
* [LuaJIT](#luajit)
* [q3vm](#q3vm)

Loaders and shellcode
* [donut](#donut)
* [MemoryModule](#memorymodule)
* [pe_to_shellcode](#pe_to_shellcode)
* [sRDI](#srdi)

Offensive tooling
* [VX-API](#vx-api)
* [BlackBone](#blackbone)
* [SysWhispers](#syswhispers)

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
| Golang   | 2024-04-03 | 1.21.9 | [x86](data/Golang/x86/smda/golang_1.21_x86.7z) / [x64](data/Golang/x64/smda/golang_1.21_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.21.9_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.21.9_x64.mcrit) |
| Golang   | 2024-01-24 | 1.22.2 | [x86](data/Golang/x86/smda/golang_1.22_x86.7z) / [x64](data/Golang/x64/smda/golang_1.22_x64.7z) | [x86](data/Golang/x86/mcrit/golang_1.22.2_x86.mcrit) / [x64](data/Golang/x64/mcrit/golang_1.22.2_x64.mcrit) |


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
| MinGW r33  | 2021-02-27 | v8.0.0      gcc10.2  binutils2.36.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-10.2-stable-r33_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-10.2-stable-r33_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-10.2-stable-r33_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-10.2-stable-r33_x64.mcrit) |
| MinGW r34  | 2021-07-13 | v8.0.2      gcc10.3  binutils2.36.1 | [x86](data/MinGW/x86/smda/mingw-w64-gcc-10.3-stable-r34_x86.7z) / [x64](data/MinGW/x64/smda/mingw-w64-gcc-10.3-stable-r34_x64.7z) | [x86](data/MinGW/x86/mcrit/mingw-w64-gcc-10.3-stable-r34_x86.mcrit) / [x64](data/MinGW/x64/mcrit/mingw-w64-gcc-10.3-stable-r34_x64.mcrit) |
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
The MinGW-w64 rows were built from unmodified upstream release tarballs with `scripts/build_corpus.py`, using upstream's own `win32/Makefile.gcc`; they cover `zlib1.dll` rather than a static lib, and MinGW C runtime functions were excluded so they stay attributed to MinGW. See `data/libzlib/provenance.json` for source URLs, digests, compiler and flags.


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
| libzlib  | 2013-04-28 | 1.2.8   | MinGW-w64 GCC 13 | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.8_mingw13_x86_zlib1.dll.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.8_mingw13_x64_zlib1.dll.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.8_mingw13_x86_zlib1.dll.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.8_mingw13_x64_zlib1.dll.7z)       |
| libzlib  | 2017-01-15 | 1.2.11  | MinGW-w64 GCC 13 | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.11_mingw13_x86_zlib1.dll.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.11_mingw13_x64_zlib1.dll.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.11_mingw13_x86_zlib1.dll.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.11_mingw13_x64_zlib1.dll.7z)     |
| libzlib  | 2022-10-13 | 1.2.13  | MinGW-w64 GCC 13 | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.2.13_mingw13_x86_zlib1.dll.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.2.13_mingw13_x64_zlib1.dll.mcrit)   | [x86 PE](data/libzlib/x86/smda/libzlib_1.2.13_mingw13_x86_zlib1.dll.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.2.13_mingw13_x64_zlib1.dll.7z)     |
| libzlib  | 2024-01-22 | 1.3.1   | MinGW-w64 GCC 13 | [x86 PE](data/libzlib/x86/mcrit/libzlib_1.3.1_mingw13_x86_zlib1.dll.mcrit) / [x64 PE](data/libzlib/x64/mcrit/libzlib_1.3.1_mingw13_x64_zlib1.dll.mcrit)     | [x86 PE](data/libzlib/x86/smda/libzlib_1.3.1_mingw13_x86_zlib1.dll.7z) / [x64 PE](data/libzlib/x64/smda/libzlib_1.3.1_mingw13_x64_zlib1.dll.7z)       |

### bzip2<a id='bzip2'></a>

bzip2 is a Burrows-Wheeler compressor found in installers and archivers for over two decades.  
Generated with `scripts/build_corpus.py`; see `data/bzip2/provenance.json` for source digests, compiler and flags.

<!-- generated: bzip2 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| bzip2 | 1.0.8 | MinGW-w64 GCC 13 | [x86 PE](data/bzip2/x86/mcrit/bzip2_1.0.8_mingw13_x86_bzip2.exe.mcrit) / [x64 PE](data/bzip2/x64/mcrit/bzip2_1.0.8_mingw13_x64_bzip2.exe.mcrit) | [x86 PE](data/bzip2/x86/smda/bzip2_1.0.8_mingw13_x86_bzip2.exe.7z) / [x64 PE](data/bzip2/x64/smda/bzip2_1.0.8_mingw13_x64_bzip2.exe.7z) |
| bzip2 | 1.0.8 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/bzip2/x86/mcrit/bzip2_1.0.8_msvc143_x86_bzip2.exe.mcrit) / [x64 PE](data/bzip2/x64/mcrit/bzip2_1.0.8_msvc143_x64_bzip2.exe.mcrit) | [x86 PE](data/bzip2/x86/smda/bzip2_1.0.8_msvc143_x86_bzip2.exe.7z) / [x64 PE](data/bzip2/x64/smda/bzip2_1.0.8_msvc143_x64_bzip2.exe.7z) |
<!-- /generated -->

### cJSON<a id='cjson'></a>

cJSON is a minimal JSON parser very widely vendored into C tooling.  
Generated with `scripts/build_corpus.py`; see `data/cJSON/provenance.json` for source digests, compiler and flags.

<!-- generated: cJSON -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| cJSON | 1.6.0 | MinGW-w64 GCC 13 | [x86 PE](data/cJSON/x86/mcrit/cJSON_1.6.0_mingw13_x86_libcjson.dll.mcrit) / [x64 PE](data/cJSON/x64/mcrit/cJSON_1.6.0_mingw13_x64_libcjson.dll.mcrit) | [x86 PE](data/cJSON/x86/smda/cJSON_1.6.0_mingw13_x86_libcjson.dll.7z) / [x64 PE](data/cJSON/x64/smda/cJSON_1.6.0_mingw13_x64_libcjson.dll.7z) |
| cJSON | 1.6.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/cJSON/x86/mcrit/cJSON_1.6.0_msvc143_x86_cjson.dll.mcrit) / [x64 PE](data/cJSON/x64/mcrit/cJSON_1.6.0_msvc143_x64_cjson.dll.mcrit) | [x86 PE](data/cJSON/x86/smda/cJSON_1.6.0_msvc143_x86_cjson.dll.7z) / [x64 PE](data/cJSON/x64/smda/cJSON_1.6.0_msvc143_x64_cjson.dll.7z) |
| cJSON | 1.7.15 | MinGW-w64 GCC 13 | [x86 PE](data/cJSON/x86/mcrit/cJSON_1.7.15_mingw13_x86_libcjson.dll.mcrit) / [x64 PE](data/cJSON/x64/mcrit/cJSON_1.7.15_mingw13_x64_libcjson.dll.mcrit) | [x86 PE](data/cJSON/x86/smda/cJSON_1.7.15_mingw13_x86_libcjson.dll.7z) / [x64 PE](data/cJSON/x64/smda/cJSON_1.7.15_mingw13_x64_libcjson.dll.7z) |
| cJSON | 1.7.19 | MinGW-w64 GCC 13 | [x86 PE](data/cJSON/x86/mcrit/cJSON_1.7.19_mingw13_x86_libcjson.dll.mcrit) / [x64 PE](data/cJSON/x64/mcrit/cJSON_1.7.19_mingw13_x64_libcjson.dll.mcrit) | [x86 PE](data/cJSON/x86/smda/cJSON_1.7.19_mingw13_x86_libcjson.dll.7z) / [x64 PE](data/cJSON/x64/smda/cJSON_1.7.19_mingw13_x64_libcjson.dll.7z) |
| cJSON | 1.7.19 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/cJSON/x86/mcrit/cJSON_1.7.19_msvc143_x86_cjson.dll.mcrit) / [x64 PE](data/cJSON/x64/mcrit/cJSON_1.7.19_msvc143_x64_cjson.dll.mcrit) | [x86 PE](data/cJSON/x86/smda/cJSON_1.7.19_msvc143_x86_cjson.dll.7z) / [x64 PE](data/cJSON/x64/smda/cJSON_1.7.19_msvc143_x64_cjson.dll.7z) |
<!-- /generated -->

### libcurl<a id='libcurl'></a>

libcurl is commonly statically linked into downloaders and droppers. Built against the Schannel TLS backend, which shapes the emitted code more than the version does.  
Generated with `scripts/build_corpus.py`; see `data/libcurl/provenance.json` for source digests, compiler and flags.

<!-- generated: libcurl -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libcurl | 8.4.0 | MinGW-w64 GCC 13 | [x86 PE](data/libcurl/x86/mcrit/libcurl_8.4.0_mingw13_x86_libcurl.dll.mcrit) / [x64 PE](data/libcurl/x64/mcrit/libcurl_8.4.0_mingw13_x64_libcurl.dll.mcrit) | [x86 PE](data/libcurl/x86/smda/libcurl_8.4.0_mingw13_x86_libcurl.dll.7z) / [x64 PE](data/libcurl/x64/smda/libcurl_8.4.0_mingw13_x64_libcurl.dll.7z) |
| libcurl | 8.4.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libcurl/x86/mcrit/libcurl_8.4.0_msvc143_x86_libcurl.dll.mcrit) / [x64 PE](data/libcurl/x64/mcrit/libcurl_8.4.0_msvc143_x64_libcurl.dll.mcrit) | [x86 PE](data/libcurl/x86/smda/libcurl_8.4.0_msvc143_x86_libcurl.dll.7z) / [x64 PE](data/libcurl/x64/smda/libcurl_8.4.0_msvc143_x64_libcurl.dll.7z) |
| libcurl | 8.15.0 | MinGW-w64 GCC 13 | [x86 PE](data/libcurl/x86/mcrit/libcurl_8.15.0_mingw13_x86_libcurl.dll.mcrit) / [x64 PE](data/libcurl/x64/mcrit/libcurl_8.15.0_mingw13_x64_libcurl.dll.mcrit) | [x86 PE](data/libcurl/x86/smda/libcurl_8.15.0_mingw13_x86_libcurl.dll.7z) / [x64 PE](data/libcurl/x64/smda/libcurl_8.15.0_mingw13_x64_libcurl.dll.7z) |
| libcurl | 8.15.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libcurl/x86/mcrit/libcurl_8.15.0_msvc143_x86_libcurl.dll.mcrit) / [x64 PE](data/libcurl/x64/mcrit/libcurl_8.15.0_msvc143_x64_libcurl.dll.mcrit) | [x86 PE](data/libcurl/x86/smda/libcurl_8.15.0_msvc143_x86_libcurl.dll.7z) / [x64 PE](data/libcurl/x64/smda/libcurl_8.15.0_msvc143_x64_libcurl.dll.7z) |
<!-- /generated -->

### libevent<a id='libevent'></a>

libevent is an event notification library linked into a lot of older tooling.  
Generated with `scripts/build_corpus.py`; see `data/libevent/provenance.json` for source digests, compiler and flags.

<!-- generated: libevent -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libevent | 2.1.12 | MinGW-w64 GCC 13 | [x86 PE](data/libevent/x86/mcrit/libevent_2.1.12_mingw13_x86_libevent_core.dll.mcrit) / [x64 PE](data/libevent/x64/mcrit/libevent_2.1.12_mingw13_x64_libevent_core.dll.mcrit) | [x86 PE](data/libevent/x86/smda/libevent_2.1.12_mingw13_x86_libevent_core.dll.7z) / [x64 PE](data/libevent/x64/smda/libevent_2.1.12_mingw13_x64_libevent_core.dll.7z) |
| libevent | 2.1.12 | MinGW-w64 GCC 13 | [x86 PE](data/libevent/x86/mcrit/libevent_2.1.12_mingw13_x86_libevent_extra.dll.mcrit) / [x64 PE](data/libevent/x64/mcrit/libevent_2.1.12_mingw13_x64_libevent_extra.dll.mcrit) | [x86 PE](data/libevent/x86/smda/libevent_2.1.12_mingw13_x86_libevent_extra.dll.7z) / [x64 PE](data/libevent/x64/smda/libevent_2.1.12_mingw13_x64_libevent_extra.dll.7z) |
| libevent | 2.1.12 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libevent/x86/mcrit/libevent_2.1.12_msvc143_x86_event_core.dll.mcrit) / [x64 PE](data/libevent/x64/mcrit/libevent_2.1.12_msvc143_x64_event_core.dll.mcrit) | [x86 PE](data/libevent/x86/smda/libevent_2.1.12_msvc143_x86_event_core.dll.7z) / [x64 PE](data/libevent/x64/smda/libevent_2.1.12_msvc143_x64_event_core.dll.7z) |
| libevent | 2.1.12 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libevent/x86/mcrit/libevent_2.1.12_msvc143_x86_event_extra.dll.mcrit) / [x64 PE](data/libevent/x64/mcrit/libevent_2.1.12_msvc143_x64_event_extra.dll.mcrit) | [x86 PE](data/libevent/x86/smda/libevent_2.1.12_msvc143_x86_event_extra.dll.7z) / [x64 PE](data/libevent/x64/smda/libevent_2.1.12_msvc143_x64_event_extra.dll.7z) |
<!-- /generated -->

### liblzma<a id='liblzma'></a>

liblzma provides LZMA/LZMA2, ubiquitous in installers. Built from signed git tags rather than release tarballs, because the 2024 backdoor (CVE-2024-3094) was present only in the tarballs.  
Generated with `scripts/build_corpus.py`; see `data/liblzma/provenance.json` for source digests, compiler and flags.

<!-- generated: liblzma -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| liblzma | 5.4.7 | MinGW-w64 GCC 13 | [x86 PE](data/liblzma/x86/mcrit/liblzma_5.4.7_mingw13_x86_liblzma.dll.mcrit) / [x64 PE](data/liblzma/x64/mcrit/liblzma_5.4.7_mingw13_x64_liblzma.dll.mcrit) | [x86 PE](data/liblzma/x86/smda/liblzma_5.4.7_mingw13_x86_liblzma.dll.7z) / [x64 PE](data/liblzma/x64/smda/liblzma_5.4.7_mingw13_x64_liblzma.dll.7z) |
| liblzma | 5.4.7 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/liblzma/x86/mcrit/liblzma_5.4.7_msvc143_x86_liblzma.dll.mcrit) / [x64 PE](data/liblzma/x64/mcrit/liblzma_5.4.7_msvc143_x64_liblzma.dll.mcrit) | [x86 PE](data/liblzma/x86/smda/liblzma_5.4.7_msvc143_x86_liblzma.dll.7z) / [x64 PE](data/liblzma/x64/smda/liblzma_5.4.7_msvc143_x64_liblzma.dll.7z) |
| liblzma | 5.8.1 | MinGW-w64 GCC 13 | [x86 PE](data/liblzma/x86/mcrit/liblzma_5.8.1_mingw13_x86_liblzma.dll.mcrit) / [x64 PE](data/liblzma/x64/mcrit/liblzma_5.8.1_mingw13_x64_liblzma.dll.mcrit) | [x86 PE](data/liblzma/x86/smda/liblzma_5.8.1_mingw13_x86_liblzma.dll.7z) / [x64 PE](data/liblzma/x64/smda/liblzma_5.8.1_mingw13_x64_liblzma.dll.7z) |
| liblzma | 5.8.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/liblzma/x86/mcrit/liblzma_5.8.1_msvc143_x86_liblzma.dll.mcrit) / [x64 PE](data/liblzma/x64/mcrit/liblzma_5.8.1_msvc143_x64_liblzma.dll.mcrit) | [x86 PE](data/liblzma/x86/smda/liblzma_5.8.1_msvc143_x86_liblzma.dll.7z) / [x64 PE](data/liblzma/x64/smda/liblzma_5.8.1_msvc143_x64_liblzma.dll.7z) |
<!-- /generated -->

### libsodium<a id='libsodium'></a>

libsodium provides X25519 and XSalsa20 and is linked by several ransomware families.  
Generated with `scripts/build_corpus.py`; see `data/libsodium/provenance.json` for source digests, compiler and flags.

<!-- generated: libsodium -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libsodium | 1.0.18 | MinGW-w64 GCC 13 | [x86 PE](data/libsodium/x86/mcrit/libsodium_1.0.18_mingw13_x86_libsodium-23.dll.mcrit) / [x64 PE](data/libsodium/x64/mcrit/libsodium_1.0.18_mingw13_x64_libsodium-23.dll.mcrit) | [x86 PE](data/libsodium/x86/smda/libsodium_1.0.18_mingw13_x86_libsodium-23.dll.7z) / [x64 PE](data/libsodium/x64/smda/libsodium_1.0.18_mingw13_x64_libsodium-23.dll.7z) |
| libsodium | 1.0.18 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libsodium/x86/mcrit/libsodium_1.0.18_msvc143_x86_libsodium.dll.mcrit) / [x64 PE](data/libsodium/x64/mcrit/libsodium_1.0.18_msvc143_x64_libsodium.dll.mcrit) | [x86 PE](data/libsodium/x86/smda/libsodium_1.0.18_msvc143_x86_libsodium.dll.7z) / [x64 PE](data/libsodium/x64/smda/libsodium_1.0.18_msvc143_x64_libsodium.dll.7z) |
| libsodium | 1.0.20 | MinGW-w64 GCC 13 | [x86 PE](data/libsodium/x86/mcrit/libsodium_1.0.20_mingw13_x86_libsodium-26.dll.mcrit) / [x64 PE](data/libsodium/x64/mcrit/libsodium_1.0.20_mingw13_x64_libsodium-26.dll.mcrit) | [x86 PE](data/libsodium/x86/smda/libsodium_1.0.20_mingw13_x86_libsodium-26.dll.7z) / [x64 PE](data/libsodium/x64/smda/libsodium_1.0.20_mingw13_x64_libsodium-26.dll.7z) |
| libsodium | 1.0.20 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libsodium/x86/mcrit/libsodium_1.0.20_msvc143_x86_libsodium.dll.mcrit) / [x64 PE](data/libsodium/x64/mcrit/libsodium_1.0.20_msvc143_x64_libsodium.dll.mcrit) | [x86 PE](data/libsodium/x86/smda/libsodium_1.0.20_msvc143_x86_libsodium.dll.7z) / [x64 PE](data/libsodium/x64/smda/libsodium_1.0.20_msvc143_x64_libsodium.dll.7z) |
<!-- /generated -->

### libtomcrypt<a id='libtomcrypt'></a>

LibTomCrypt is a crypto toolkit with a long history of reuse in malware. Built against LibTomMath for its bignum backend.  
Generated with `scripts/build_corpus.py`; see `data/libtomcrypt/provenance.json` for source digests, compiler and flags.

<!-- generated: libtomcrypt -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libtomcrypt | 1.18.2 | MinGW-w64 GCC 13 | [x86 PE](data/libtomcrypt/x86/mcrit/libtomcrypt_1.18.2_mingw13_x86_libtomcrypt.dll.mcrit) / [x64 PE](data/libtomcrypt/x64/mcrit/libtomcrypt_1.18.2_mingw13_x64_libtomcrypt.dll.mcrit) | [x86 PE](data/libtomcrypt/x86/smda/libtomcrypt_1.18.2_mingw13_x86_libtomcrypt.dll.7z) / [x64 PE](data/libtomcrypt/x64/smda/libtomcrypt_1.18.2_mingw13_x64_libtomcrypt.dll.7z) |
| libtomcrypt | 1.18.2 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libtomcrypt/x86/mcrit/libtomcrypt_1.18.2_msvc143_x86_libtomcrypt.dll.mcrit) / [x64 PE](data/libtomcrypt/x64/mcrit/libtomcrypt_1.18.2_msvc143_x64_libtomcrypt.dll.mcrit) | [x86 PE](data/libtomcrypt/x86/smda/libtomcrypt_1.18.2_msvc143_x86_libtomcrypt.dll.7z) / [x64 PE](data/libtomcrypt/x64/smda/libtomcrypt_1.18.2_msvc143_x64_libtomcrypt.dll.7z) |
<!-- /generated -->

### libuv<a id='libuv'></a>

libuv is the event loop behind Node.js and a good deal of C tooling.  
Generated with `scripts/build_corpus.py`; see `data/libuv/provenance.json` for source digests, compiler and flags.

<!-- generated: libuv -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libuv | 1.44.2 | MinGW-w64 GCC 13 | [x86 PE](data/libuv/x86/mcrit/libuv_1.44.2_mingw13_x86_libuv.dll.mcrit) / [x64 PE](data/libuv/x64/mcrit/libuv_1.44.2_mingw13_x64_libuv.dll.mcrit) | [x86 PE](data/libuv/x86/smda/libuv_1.44.2_mingw13_x86_libuv.dll.7z) / [x64 PE](data/libuv/x64/smda/libuv_1.44.2_mingw13_x64_libuv.dll.7z) |
| libuv | 1.44.2 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libuv/x86/mcrit/libuv_1.44.2_msvc143_x86_uv.dll.mcrit) / [x64 PE](data/libuv/x64/mcrit/libuv_1.44.2_msvc143_x64_uv.dll.mcrit) | [x86 PE](data/libuv/x86/smda/libuv_1.44.2_msvc143_x86_uv.dll.7z) / [x64 PE](data/libuv/x64/smda/libuv_1.44.2_msvc143_x64_uv.dll.7z) |
| libuv | 1.52.1 | MinGW-w64 GCC 13 | [x86 PE](data/libuv/x86/mcrit/libuv_1.52.1_mingw13_x86_libuv.dll.mcrit) / [x64 PE](data/libuv/x64/mcrit/libuv_1.52.1_mingw13_x64_libuv.dll.mcrit) | [x86 PE](data/libuv/x86/smda/libuv_1.52.1_mingw13_x86_libuv.dll.7z) / [x64 PE](data/libuv/x64/smda/libuv_1.52.1_mingw13_x64_libuv.dll.7z) |
| libuv | 1.52.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libuv/x86/mcrit/libuv_1.52.1_msvc143_x86_uv.dll.mcrit) / [x64 PE](data/libuv/x64/mcrit/libuv_1.52.1_msvc143_x64_uv.dll.mcrit) | [x86 PE](data/libuv/x86/smda/libuv_1.52.1_msvc143_x86_uv.dll.7z) / [x64 PE](data/libuv/x64/smda/libuv_1.52.1_msvc143_x64_uv.dll.7z) |
<!-- /generated -->

### libxml2<a id='libxml2'></a>

libxml2 is vendored into an enormous amount of software. ShiftMediaProject additionally publishes MSVC builds with PDBs, which would complement these.  
Generated with `scripts/build_corpus.py`; see `data/libxml2/provenance.json` for source digests, compiler and flags.

<!-- generated: libxml2 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libxml2 | 2.9.14 | MinGW-w64 GCC 13 | [x86 PE](data/libxml2/x86/mcrit/libxml2_2.9.14_mingw13_x86_libxml2.dll.mcrit) / [x64 PE](data/libxml2/x64/mcrit/libxml2_2.9.14_mingw13_x64_libxml2.dll.mcrit) | [x86 PE](data/libxml2/x86/smda/libxml2_2.9.14_mingw13_x86_libxml2.dll.7z) / [x64 PE](data/libxml2/x64/smda/libxml2_2.9.14_mingw13_x64_libxml2.dll.7z) |
| libxml2 | 2.9.14 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libxml2/x86/mcrit/libxml2_2.9.14_msvc143_x86_libxml2.dll.mcrit) / [x64 PE](data/libxml2/x64/mcrit/libxml2_2.9.14_msvc143_x64_libxml2.dll.mcrit) | [x86 PE](data/libxml2/x86/smda/libxml2_2.9.14_msvc143_x86_libxml2.dll.7z) / [x64 PE](data/libxml2/x64/smda/libxml2_2.9.14_msvc143_x64_libxml2.dll.7z) |
| libxml2 | 2.14.3 | MinGW-w64 GCC 13 | [x86 PE](data/libxml2/x86/mcrit/libxml2_2.14.3_mingw13_x86_libxml2.dll.mcrit) / [x64 PE](data/libxml2/x64/mcrit/libxml2_2.14.3_mingw13_x64_libxml2.dll.mcrit) | [x86 PE](data/libxml2/x86/smda/libxml2_2.14.3_mingw13_x86_libxml2.dll.7z) / [x64 PE](data/libxml2/x64/smda/libxml2_2.14.3_mingw13_x64_libxml2.dll.7z) |
| libxml2 | 2.14.3 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libxml2/x86/mcrit/libxml2_2.14.3_msvc143_x86_libxml2.dll.mcrit) / [x64 PE](data/libxml2/x64/mcrit/libxml2_2.14.3_msvc143_x64_libxml2.dll.mcrit) | [x86 PE](data/libxml2/x86/smda/libxml2_2.14.3_msvc143_x86_libxml2.dll.7z) / [x64 PE](data/libxml2/x64/smda/libxml2_2.14.3_msvc143_x64_libxml2.dll.7z) |
<!-- /generated -->

### lz4<a id='lz4'></a>

lz4 is a fast compressor common in modern loaders, packers and Electron-derived software.  
Generated with `scripts/build_corpus.py`; see `data/lz4/provenance.json` for source digests, compiler and flags.

<!-- generated: lz4 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| lz4 | 1.9.4 | MinGW-w64 GCC 13 | [x86 PE](data/lz4/x86/mcrit/lz4_1.9.4_mingw13_x86_liblz4.dll.mcrit) / [x64 PE](data/lz4/x64/mcrit/lz4_1.9.4_mingw13_x64_liblz4.dll.mcrit) | [x86 PE](data/lz4/x86/smda/lz4_1.9.4_mingw13_x86_liblz4.dll.7z) / [x64 PE](data/lz4/x64/smda/lz4_1.9.4_mingw13_x64_liblz4.dll.7z) |
| lz4 | 1.10.0 | MinGW-w64 GCC 13 | [x86 PE](data/lz4/x86/mcrit/lz4_1.10.0_mingw13_x86_liblz4.dll.mcrit) / [x64 PE](data/lz4/x64/mcrit/lz4_1.10.0_mingw13_x64_liblz4.dll.mcrit) | [x86 PE](data/lz4/x86/smda/lz4_1.10.0_mingw13_x86_liblz4.dll.7z) / [x64 PE](data/lz4/x64/smda/lz4_1.10.0_mingw13_x64_liblz4.dll.7z) |
| lz4 | 1.10.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/lz4/x86/mcrit/lz4_1.10.0_msvc143_x86_lz4.dll.mcrit) / [x64 PE](data/lz4/x64/mcrit/lz4_1.10.0_msvc143_x64_lz4.dll.mcrit) | [x86 PE](data/lz4/x86/smda/lz4_1.10.0_msvc143_x86_lz4.dll.7z) / [x64 PE](data/lz4/x64/smda/lz4_1.10.0_msvc143_x64_lz4.dll.7z) |
<!-- /generated -->

### mbedTLS<a id='mbedtls'></a>

mbedTLS is the TLS and crypto stack of the embedded and IoT world. One build per code generation rather than per release.  
Generated with `scripts/build_corpus.py`; see `data/mbedTLS/provenance.json` for source digests, compiler and flags.

<!-- generated: mbedTLS -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| mbedTLS | 2.16.12 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.16.12_mingw13_x86_libmbedcrypto.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.16.12_mingw13_x64_libmbedcrypto.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.16.12_mingw13_x86_libmbedcrypto.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.16.12_mingw13_x64_libmbedcrypto.dll.7z) |
| mbedTLS | 2.16.12 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.16.12_mingw13_x86_libmbedtls.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.16.12_mingw13_x64_libmbedtls.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.16.12_mingw13_x86_libmbedtls.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.16.12_mingw13_x64_libmbedtls.dll.7z) |
| mbedTLS | 2.16.12 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.16.12_mingw13_x86_libmbedx509.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.16.12_mingw13_x64_libmbedx509.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.16.12_mingw13_x86_libmbedx509.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.16.12_mingw13_x64_libmbedx509.dll.7z) |
| mbedTLS | 2.28.10 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.28.10_mingw13_x86_libmbedcrypto.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.28.10_mingw13_x64_libmbedcrypto.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.28.10_mingw13_x86_libmbedcrypto.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.28.10_mingw13_x64_libmbedcrypto.dll.7z) |
| mbedTLS | 2.28.10 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.28.10_mingw13_x86_libmbedtls.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.28.10_mingw13_x64_libmbedtls.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.28.10_mingw13_x86_libmbedtls.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.28.10_mingw13_x64_libmbedtls.dll.7z) |
| mbedTLS | 2.28.10 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_2.28.10_mingw13_x86_libmbedx509.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_2.28.10_mingw13_x64_libmbedx509.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_2.28.10_mingw13_x86_libmbedx509.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_2.28.10_mingw13_x64_libmbedx509.dll.7z) |
| mbedTLS | 3.0.0 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.0.0_mingw13_x86_libmbedcrypto.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.0.0_mingw13_x64_libmbedcrypto.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.0.0_mingw13_x86_libmbedcrypto.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.0.0_mingw13_x64_libmbedcrypto.dll.7z) |
| mbedTLS | 3.0.0 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.0.0_mingw13_x86_libmbedtls.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.0.0_mingw13_x64_libmbedtls.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.0.0_mingw13_x86_libmbedtls.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.0.0_mingw13_x64_libmbedtls.dll.7z) |
| mbedTLS | 3.0.0 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.0.0_mingw13_x86_libmbedx509.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.0.0_mingw13_x64_libmbedx509.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.0.0_mingw13_x86_libmbedx509.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.0.0_mingw13_x64_libmbedx509.dll.7z) |
| mbedTLS | 3.6.7 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.6.7_mingw13_x86_libmbedcrypto.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.6.7_mingw13_x64_libmbedcrypto.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.6.7_mingw13_x86_libmbedcrypto.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.6.7_mingw13_x64_libmbedcrypto.dll.7z) |
| mbedTLS | 3.6.7 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.6.7_mingw13_x86_libmbedtls.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.6.7_mingw13_x64_libmbedtls.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.6.7_mingw13_x86_libmbedtls.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.6.7_mingw13_x64_libmbedtls.dll.7z) |
| mbedTLS | 3.6.7 | MinGW-w64 GCC 13 | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.6.7_mingw13_x86_libmbedx509.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.6.7_mingw13_x64_libmbedx509.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.6.7_mingw13_x86_libmbedx509.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.6.7_mingw13_x64_libmbedx509.dll.7z) |
| mbedTLS | 3.6.7 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/mbedTLS/x86/mcrit/mbedTLS_3.6.7_msvc143_x86_mbedtls_all.dll.mcrit) / [x64 PE](data/mbedTLS/x64/mcrit/mbedTLS_3.6.7_msvc143_x64_mbedtls_all.dll.mcrit) | [x86 PE](data/mbedTLS/x86/smda/mbedTLS_3.6.7_msvc143_x86_mbedtls_all.dll.7z) / [x64 PE](data/mbedTLS/x64/smda/mbedTLS_3.6.7_msvc143_x64_mbedtls_all.dll.7z) |
<!-- /generated -->

### pcre2<a id='pcre2'></a>

PCRE2 is the regular expression engine used by anything current. JIT is enabled, as it is in most distributions.  
Generated with `scripts/build_corpus.py`; see `data/pcre2/provenance.json` for source digests, compiler and flags.

<!-- generated: pcre2 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| pcre2 | 10.39 | MinGW-w64 GCC 13 | [x86 PE](data/pcre2/x86/mcrit/pcre2_10.39_mingw13_x86_libpcre2-8.dll.mcrit) / [x64 PE](data/pcre2/x64/mcrit/pcre2_10.39_mingw13_x64_libpcre2-8.dll.mcrit) | [x86 PE](data/pcre2/x86/smda/pcre2_10.39_mingw13_x86_libpcre2-8.dll.7z) / [x64 PE](data/pcre2/x64/smda/pcre2_10.39_mingw13_x64_libpcre2-8.dll.7z) |
| pcre2 | 10.39 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/pcre2/x86/mcrit/pcre2_10.39_msvc143_x86_pcre2-8.dll.mcrit) / [x64 PE](data/pcre2/x64/mcrit/pcre2_10.39_msvc143_x64_pcre2-8.dll.mcrit) | [x86 PE](data/pcre2/x86/smda/pcre2_10.39_msvc143_x86_pcre2-8.dll.7z) / [x64 PE](data/pcre2/x64/smda/pcre2_10.39_msvc143_x64_pcre2-8.dll.7z) |
| pcre2 | 10.45 | MinGW-w64 GCC 13 | [x86 PE](data/pcre2/x86/mcrit/pcre2_10.45_mingw13_x86_libpcre2-8.dll.mcrit) / [x64 PE](data/pcre2/x64/mcrit/pcre2_10.45_mingw13_x64_libpcre2-8.dll.mcrit) | [x86 PE](data/pcre2/x86/smda/pcre2_10.45_mingw13_x86_libpcre2-8.dll.7z) / [x64 PE](data/pcre2/x64/smda/pcre2_10.45_mingw13_x64_libpcre2-8.dll.7z) |
| pcre2 | 10.45 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/pcre2/x86/mcrit/pcre2_10.45_msvc143_x86_pcre2-8.dll.mcrit) / [x64 PE](data/pcre2/x64/mcrit/pcre2_10.45_msvc143_x64_pcre2-8.dll.mcrit) | [x86 PE](data/pcre2/x86/smda/pcre2_10.45_msvc143_x86_pcre2-8.dll.7z) / [x64 PE](data/pcre2/x64/smda/pcre2_10.45_msvc143_x64_pcre2-8.dll.7z) |
<!-- /generated -->

### sqlite3<a id='sqlite3'></a>

SQLite is almost certainly the most widely embedded database on Windows. Built from the official amalgamation, which is how applications consume it.  
Generated with `scripts/build_corpus.py`; see `data/sqlite3/provenance.json` for source digests, compiler and flags.

<!-- generated: sqlite3 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| sqlite3 | 3.8.11.1 | MinGW-w64 GCC 13 | [x86 PE](data/sqlite3/x86/mcrit/sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll.mcrit) / [x64 PE](data/sqlite3/x64/mcrit/sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll.mcrit) | [x86 PE](data/sqlite3/x86/smda/sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll.7z) / [x64 PE](data/sqlite3/x64/smda/sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll.7z) |
| sqlite3 | 3.31.1 | MinGW-w64 GCC 13 | [x86 PE](data/sqlite3/x86/mcrit/sqlite3_3.31.1_mingw13_x86_sqlite3.dll.mcrit) / [x64 PE](data/sqlite3/x64/mcrit/sqlite3_3.31.1_mingw13_x64_sqlite3.dll.mcrit) | [x86 PE](data/sqlite3/x86/smda/sqlite3_3.31.1_mingw13_x86_sqlite3.dll.7z) / [x64 PE](data/sqlite3/x64/smda/sqlite3_3.31.1_mingw13_x64_sqlite3.dll.7z) |
| sqlite3 | 3.31.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/sqlite3/x86/mcrit/sqlite3_3.31.1_msvc143_x86_sqlite3.dll.mcrit) / [x64 PE](data/sqlite3/x64/mcrit/sqlite3_3.31.1_msvc143_x64_sqlite3.dll.mcrit) | [x86 PE](data/sqlite3/x86/smda/sqlite3_3.31.1_msvc143_x86_sqlite3.dll.7z) / [x64 PE](data/sqlite3/x64/smda/sqlite3_3.31.1_msvc143_x64_sqlite3.dll.7z) |
| sqlite3 | 3.50.4 | MinGW-w64 GCC 13 | [x86 PE](data/sqlite3/x86/mcrit/sqlite3_3.50.4_mingw13_x86_sqlite3.dll.mcrit) / [x64 PE](data/sqlite3/x64/mcrit/sqlite3_3.50.4_mingw13_x64_sqlite3.dll.mcrit) | [x86 PE](data/sqlite3/x86/smda/sqlite3_3.50.4_mingw13_x86_sqlite3.dll.7z) / [x64 PE](data/sqlite3/x64/smda/sqlite3_3.50.4_mingw13_x64_sqlite3.dll.7z) |
| sqlite3 | 3.50.4 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/sqlite3/x86/mcrit/sqlite3_3.50.4_msvc143_x86_sqlite3.dll.mcrit) / [x64 PE](data/sqlite3/x64/mcrit/sqlite3_3.50.4_msvc143_x64_sqlite3.dll.mcrit) | [x86 PE](data/sqlite3/x86/smda/sqlite3_3.50.4_msvc143_x86_sqlite3.dll.7z) / [x64 PE](data/sqlite3/x64/smda/sqlite3_3.50.4_msvc143_x64_sqlite3.dll.7z) |
<!-- /generated -->

### libpng<a id='libpng'></a>

libpng is found in old packers, installers and image-handling tooling. Built against a zlib staged into the source tree, so the build needs nothing preinstalled.  
Generated with `scripts/build_corpus.py`; see `data/libpng/provenance.json` for source digests, compiler and flags.

<!-- generated: libpng -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libpng | 1.6.50 | MinGW-w64 GCC 13 | [x86 PE](data/libpng/x86/mcrit/libpng_1.6.50_mingw13_x86_libpng16.dll.mcrit) / [x64 PE](data/libpng/x64/mcrit/libpng_1.6.50_mingw13_x64_libpng16.dll.mcrit) | [x86 PE](data/libpng/x86/smda/libpng_1.6.50_mingw13_x86_libpng16.dll.7z) / [x64 PE](data/libpng/x64/smda/libpng_1.6.50_mingw13_x64_libpng16.dll.7z) |
| libpng | 1.6.50 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libpng/x86/mcrit/libpng_1.6.50_msvc143_x86_libpng16.dll.mcrit) / [x64 PE](data/libpng/x64/mcrit/libpng_1.6.50_msvc143_x64_libpng16.dll.mcrit) | [x86 PE](data/libpng/x86/smda/libpng_1.6.50_msvc143_x86_libpng16.dll.7z) / [x64 PE](data/libpng/x64/smda/libpng_1.6.50_msvc143_x64_libpng16.dll.7z) |
<!-- /generated -->

### libtiff<a id='libtiff'></a>

libtiff has a long CVE history and is embedded widely. Codecs that would pull external dependencies are disabled; the core reader and writer is what matters for recognising reuse.  
Generated with `scripts/build_corpus.py`; see `data/libtiff/provenance.json` for source digests, compiler and flags.

<!-- generated: libtiff -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libtiff | 4.0.10 | MinGW-w64 GCC 13 | [x86 PE](data/libtiff/x86/mcrit/libtiff_4.0.10_mingw13_x86_libtiff.dll.mcrit) / [x64 PE](data/libtiff/x64/mcrit/libtiff_4.0.10_mingw13_x64_libtiff.dll.mcrit) | [x86 PE](data/libtiff/x86/smda/libtiff_4.0.10_mingw13_x86_libtiff.dll.7z) / [x64 PE](data/libtiff/x64/smda/libtiff_4.0.10_mingw13_x64_libtiff.dll.7z) |
| libtiff | 4.7.0 | MinGW-w64 GCC 13 | [x86 PE](data/libtiff/x86/mcrit/libtiff_4.7.0_mingw13_x86_libtiff.dll.mcrit) / [x64 PE](data/libtiff/x64/mcrit/libtiff_4.7.0_mingw13_x64_libtiff.dll.mcrit) | [x86 PE](data/libtiff/x86/smda/libtiff_4.7.0_mingw13_x86_libtiff.dll.7z) / [x64 PE](data/libtiff/x64/smda/libtiff_4.7.0_mingw13_x64_libtiff.dll.7z) |
| libtiff | 4.7.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/libtiff/x86/mcrit/libtiff_4.7.0_msvc143_x86_tiff.dll.mcrit) / [x64 PE](data/libtiff/x64/mcrit/libtiff_4.7.0_msvc143_x64_tiff.dll.mcrit) | [x86 PE](data/libtiff/x86/smda/libtiff_4.7.0_msvc143_x86_tiff.dll.7z) / [x64 PE](data/libtiff/x64/smda/libtiff_4.7.0_msvc143_x64_tiff.dll.7z) |
<!-- /generated -->

### wolfSSL<a id='wolfssl'></a>

wolfSSL is an embedded TLS stack. One version only: it is genuinely uncommon in Windows malware compared with OpenSSL and mbedTLS.  
Generated with `scripts/build_corpus.py`; see `data/wolfSSL/provenance.json` for source digests, compiler and flags.

<!-- generated: wolfSSL -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| wolfSSL | 5.9.2 | MinGW-w64 GCC 13 | [x86 PE](data/wolfSSL/x86/mcrit/wolfSSL_5.9.2_mingw13_x86_libwolfssl.dll.mcrit) / [x64 PE](data/wolfSSL/x64/mcrit/wolfSSL_5.9.2_mingw13_x64_libwolfssl.dll.mcrit) | [x86 PE](data/wolfSSL/x86/smda/wolfSSL_5.9.2_mingw13_x86_libwolfssl.dll.7z) / [x64 PE](data/wolfSSL/x64/smda/wolfSSL_5.9.2_mingw13_x64_libwolfssl.dll.7z) |
| wolfSSL | 5.9.2 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/wolfSSL/x86/mcrit/wolfSSL_5.9.2_msvc143_x86_wolfssl.dll.mcrit) / [x64 PE](data/wolfSSL/x64/mcrit/wolfSSL_5.9.2_msvc143_x64_wolfssl.dll.mcrit) | [x86 PE](data/wolfSSL/x86/smda/wolfSSL_5.9.2_msvc143_x86_wolfssl.dll.7z) / [x64 PE](data/wolfSSL/x64/smda/wolfSSL_5.9.2_msvc143_x64_wolfssl.dll.7z) |
<!-- /generated -->

### OpenSSL<a id='openssl'></a>

OpenSSL is the largest body of crypto code in this corpus. The three versions are chosen for architecture rather than recency: 1.1.1 has no provider layer at all and is still by far the most encountered OpenSSL, 3.0 introduced the provider architecture, and 3.5 is the current LTS.  
OpenSSL in the wild is overwhelmingly MSVC-built, so a MinGW reference matches those only weakly; its strength here is matching MinGW/GCC-built Windows binaries, and by proxy ELF builds.  

Generated with `scripts/build_corpus.py`; see `data/OpenSSL/provenance.json` for source digests, compiler and flags.

<!-- generated: OpenSSL -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| OpenSSL | 1.1.1w | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_1.1.1w_mingw13_x86_libcrypto.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_1.1.1w_mingw13_x64_libcrypto.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_1.1.1w_mingw13_x86_libcrypto.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_1.1.1w_mingw13_x64_libcrypto.7z) |
| OpenSSL | 1.1.1w | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_1.1.1w_mingw13_x86_libssl.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_1.1.1w_mingw13_x64_libssl.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_1.1.1w_mingw13_x86_libssl.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_1.1.1w_mingw13_x64_libssl.7z) |
| OpenSSL | 1.1.1w | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_1.1.1w_msvc143_x86_libcrypto.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_1.1.1w_msvc143_x64_libcrypto.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_1.1.1w_msvc143_x86_libcrypto.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_1.1.1w_msvc143_x64_libcrypto.7z) |
| OpenSSL | 1.1.1w | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_1.1.1w_msvc143_x86_libssl.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_1.1.1w_msvc143_x64_libssl.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_1.1.1w_msvc143_x86_libssl.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_1.1.1w_msvc143_x64_libssl.7z) |
| OpenSSL | 3.0.15 | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_3.0.15_mingw13_x86_libcrypto.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_3.0.15_mingw13_x64_libcrypto.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_3.0.15_mingw13_x86_libcrypto.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_3.0.15_mingw13_x64_libcrypto.7z) |
| OpenSSL | 3.0.15 | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_3.0.15_mingw13_x86_libssl.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_3.0.15_mingw13_x64_libssl.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_3.0.15_mingw13_x86_libssl.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_3.0.15_mingw13_x64_libssl.7z) |
| OpenSSL | 3.5.8 | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_3.5.8_mingw13_x86_libcrypto.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_3.5.8_mingw13_x64_libcrypto.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_3.5.8_mingw13_x86_libcrypto.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_3.5.8_mingw13_x64_libcrypto.7z) |
| OpenSSL | 3.5.8 | MinGW-w64 GCC 13 | [x86 PE](data/OpenSSL/x86/mcrit/OpenSSL_3.5.8_mingw13_x86_libssl.mcrit) / [x64 PE](data/OpenSSL/x64/mcrit/OpenSSL_3.5.8_mingw13_x64_libssl.mcrit) | [x86 PE](data/OpenSSL/x86/smda/OpenSSL_3.5.8_mingw13_x86_libssl.7z) / [x64 PE](data/OpenSSL/x64/smda/OpenSSL_3.5.8_mingw13_x64_libssl.7z) |
<!-- /generated -->

### Crypto++<a id='cryptopp'></a>

Crypto++ is a C++ crypto toolkit and a regular guest in malware. The three releases are picked where the library was restructured: 5.6.5 is the last of the 5.6 line and predates the C++11 move of 6.0, 7.0.0 follows the split of the SIMD implementations into their own translation units, and 8.9.0 is current. Any two of them overlap far less than their version numbers suggest.  
The compilation is under the Boost Software License 1.0 while the individual files are in the public domain, which is the arrangement described in upstream's License.txt.  

Generated with `scripts/build_corpus.py`; see `data/cryptopp/provenance.json` for source digests, compiler and flags.

<!-- generated: cryptopp -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| cryptopp | 5.6.5 | MinGW-w64 GCC 13 | [x86 PE](data/cryptopp/x86/mcrit/cryptopp_5.6.5_mingw13_x86_cryptopp.dll.mcrit) / [x64 PE](data/cryptopp/x64/mcrit/cryptopp_5.6.5_mingw13_x64_cryptopp.dll.mcrit) | [x86 PE](data/cryptopp/x86/smda/cryptopp_5.6.5_mingw13_x86_cryptopp.dll.7z) / [x64 PE](data/cryptopp/x64/smda/cryptopp_5.6.5_mingw13_x64_cryptopp.dll.7z) |
| cryptopp | 7.0.0 | MinGW-w64 GCC 13 | [x86 PE](data/cryptopp/x86/mcrit/cryptopp_7.0.0_mingw13_x86_cryptopp.dll.mcrit) / [x64 PE](data/cryptopp/x64/mcrit/cryptopp_7.0.0_mingw13_x64_cryptopp.dll.mcrit) | [x86 PE](data/cryptopp/x86/smda/cryptopp_7.0.0_mingw13_x86_cryptopp.dll.7z) / [x64 PE](data/cryptopp/x64/smda/cryptopp_7.0.0_mingw13_x64_cryptopp.dll.7z) |
| cryptopp | 8.9.0 | MinGW-w64 GCC 13 | [x86 PE](data/cryptopp/x86/mcrit/cryptopp_8.9.0_mingw13_x86_cryptopp.dll.mcrit) / [x64 PE](data/cryptopp/x64/mcrit/cryptopp_8.9.0_mingw13_x64_cryptopp.dll.mcrit) | [x86 PE](data/cryptopp/x86/smda/cryptopp_8.9.0_mingw13_x86_cryptopp.dll.7z) / [x64 PE](data/cryptopp/x64/smda/cryptopp_8.9.0_mingw13_x64_cryptopp.dll.7z) |
| cryptopp | 8.9.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/cryptopp/x86/mcrit/cryptopp_8.9.0_msvc143_x86_cryptopp.dll.mcrit) / [x64 PE](data/cryptopp/x64/mcrit/cryptopp_8.9.0_msvc143_x64_cryptopp.dll.mcrit) | [x86 PE](data/cryptopp/x86/smda/cryptopp_8.9.0_msvc143_x86_cryptopp.dll.7z) / [x64 PE](data/cryptopp/x64/smda/cryptopp_8.9.0_msvc143_x64_cryptopp.dll.7z) |
<!-- /generated -->

### 7-Zip<a id='7-zip'></a>

7z.dll carries the archiver and every codec, including the LZMA implementation that is among the most copy-pasted compression code in Windows malware.  
7-Zip publishes no checksums of its own; the digests recorded here were taken from the fetched archives over HTTPS.  

Generated with `scripts/build_corpus.py`; see `data/7-Zip/provenance.json` for source digests, compiler and flags.

<!-- generated: 7-Zip -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| 7-Zip | 23.01 | MinGW-w64 GCC 13 | [x86 PE](data/7-Zip/x86/mcrit/7-Zip_23.01_mingw13_x86_7z.dll.mcrit) / [x64 PE](data/7-Zip/x64/mcrit/7-Zip_23.01_mingw13_x64_7z.dll.mcrit) | [x86 PE](data/7-Zip/x86/smda/7-Zip_23.01_mingw13_x86_7z.dll.7z) / [x64 PE](data/7-Zip/x64/smda/7-Zip_23.01_mingw13_x64_7z.dll.7z) |
| 7-Zip | 23.01 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/7-Zip/x86/mcrit/7-Zip_23.01_msvc143_x86_7z.dll.mcrit) / [x64 PE](data/7-Zip/x64/mcrit/7-Zip_23.01_msvc143_x64_7z.dll.mcrit) | [x86 PE](data/7-Zip/x86/smda/7-Zip_23.01_msvc143_x86_7z.dll.7z) / [x64 PE](data/7-Zip/x64/smda/7-Zip_23.01_msvc143_x64_7z.dll.7z) |
| 7-Zip | 26.03 | MinGW-w64 GCC 13 | [x86 PE](data/7-Zip/x86/mcrit/7-Zip_26.03_mingw13_x86_7z.dll.mcrit) / [x64 PE](data/7-Zip/x64/mcrit/7-Zip_26.03_mingw13_x64_7z.dll.mcrit) | [x86 PE](data/7-Zip/x86/smda/7-Zip_26.03_mingw13_x86_7z.dll.7z) / [x64 PE](data/7-Zip/x64/smda/7-Zip_26.03_mingw13_x64_7z.dll.7z) |
| 7-Zip | 26.03 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/7-Zip/x86/mcrit/7-Zip_26.03_msvc143_x86_7z.dll.mcrit) / [x64 PE](data/7-Zip/x64/mcrit/7-Zip_26.03_msvc143_x64_7z.dll.mcrit) | [x86 PE](data/7-Zip/x86/smda/7-Zip_26.03_msvc143_x86_7z.dll.7z) / [x64 PE](data/7-Zip/x64/smda/7-Zip_26.03_msvc143_x64_7z.dll.7z) |
<!-- /generated -->

### PCRE<a id='pcre'></a>

PCRE1 ended at 8.45 but is still linked into a great deal of legacy Windows software, and it shares almost no code with PCRE2. JIT and UTF are enabled explicitly, because PCRE1's CMake build defaults both off where a distribution or a vendored copy ships them on.  

Generated with `scripts/build_corpus.py`; see `data/pcre/provenance.json` for source digests, compiler and flags.

<!-- generated: pcre -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| pcre | 8.45 | MinGW-w64 GCC 13 | [x86 PE](data/pcre/x86/mcrit/pcre_8.45_mingw13_x86_libpcre.dll.mcrit) / [x64 PE](data/pcre/x64/mcrit/pcre_8.45_mingw13_x64_libpcre.dll.mcrit) | [x86 PE](data/pcre/x86/smda/pcre_8.45_mingw13_x86_libpcre.dll.7z) / [x64 PE](data/pcre/x64/smda/pcre_8.45_mingw13_x64_libpcre.dll.7z) |
| pcre | 8.45 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/pcre/x86/mcrit/pcre_8.45_msvc143_x86_pcre.dll.mcrit) / [x64 PE](data/pcre/x64/mcrit/pcre_8.45_msvc143_x64_pcre.dll.mcrit) | [x86 PE](data/pcre/x86/smda/pcre_8.45_msvc143_x86_pcre.dll.7z) / [x64 PE](data/pcre/x64/smda/pcre_8.45_msvc143_x64_pcre.dll.7z) |
<!-- /generated -->

### abseil<a id='abseil'></a>

Abseil also covers CCTZ, which is vendored inside it as absl/time/internal/cctz, so google/cctz is not processed separately. Abseil builds as a pile of static archives, which SMDA cannot read, so they are linked into one DLL with `--whole-archive` to force every object in rather than only what an anchor references.  

Generated with `scripts/build_corpus.py`; see `data/abseil/provenance.json` for source digests, compiler and flags.

<!-- generated: abseil -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| abseil | 20220623.1 | MinGW-w64 GCC 13 | [x86 PE](data/abseil/x86/mcrit/abseil_20220623.1_mingw13_x86_abseil.dll.mcrit) / [x64 PE](data/abseil/x64/mcrit/abseil_20220623.1_mingw13_x64_abseil.dll.mcrit) | [x86 PE](data/abseil/x86/smda/abseil_20220623.1_mingw13_x86_abseil.dll.7z) / [x64 PE](data/abseil/x64/smda/abseil_20220623.1_mingw13_x64_abseil.dll.7z) |
| abseil | 20250127.1 | MinGW-w64 GCC 13 | [x86 PE](data/abseil/x86/mcrit/abseil_20250127.1_mingw13_x86_abseil.dll.mcrit) / [x64 PE](data/abseil/x64/mcrit/abseil_20250127.1_mingw13_x64_abseil.dll.mcrit) | [x86 PE](data/abseil/x86/smda/abseil_20250127.1_mingw13_x86_abseil.dll.7z) / [x64 PE](data/abseil/x64/smda/abseil_20250127.1_mingw13_x64_abseil.dll.7z) |
| abseil | 20250127.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/abseil/x86/mcrit/abseil_20250127.1_msvc143_x86_abseil_dll.dll.mcrit) / [x64 PE](data/abseil/x64/mcrit/abseil_20250127.1_msvc143_x64_abseil_dll.dll.mcrit) | [x86 PE](data/abseil/x86/smda/abseil_20250127.1_msvc143_x86_abseil_dll.dll.7z) / [x64 PE](data/abseil/x64/smda/abseil_20250127.1_msvc143_x64_abseil_dll.dll.7z) |
<!-- /generated -->

### re2<a id='re2'></a>

The two versions bracket the largest code-level split in this part of the corpus: 2022-06-01 is the last release before RE2 took a dependency on Abseil, and the current one is built on Abseil throughout. A matcher that knows only one of them recognises very little of the other.  
For the Abseil-based version, Abseil is built alongside as DLLs and only imported, so none of its object code is attributed to re2 - the import table shows `libabsl_hash`, `libabsl_strings`, `libabsl_synchronization` and the rest. What is present is the Abseil inline and template code RE2 instantiates, which any RE2 binary carries.  

Generated with `scripts/build_corpus.py`; see `data/re2/provenance.json` for source digests, compiler and flags.

<!-- generated: re2 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| re2 | 2022-06-01 | MinGW-w64 GCC 13 | [x86 PE](data/re2/x86/mcrit/re2_2022-06-01_mingw13_x86_re2.dll.mcrit) / [x64 PE](data/re2/x64/mcrit/re2_2022-06-01_mingw13_x64_re2.dll.mcrit) | [x86 PE](data/re2/x86/smda/re2_2022-06-01_mingw13_x86_re2.dll.7z) / [x64 PE](data/re2/x64/smda/re2_2022-06-01_mingw13_x64_re2.dll.7z) |
| re2 | 2022-06-01 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/re2/x86/mcrit/re2_2022-06-01_msvc143_x86_re2.dll.mcrit) / [x64 PE](data/re2/x64/mcrit/re2_2022-06-01_msvc143_x64_re2.dll.mcrit) | [x86 PE](data/re2/x86/smda/re2_2022-06-01_msvc143_x86_re2.dll.7z) / [x64 PE](data/re2/x64/smda/re2_2022-06-01_msvc143_x64_re2.dll.7z) |
| re2 | 2025-11-05 | MinGW-w64 GCC 13 | [x86 PE](data/re2/x86/mcrit/re2_2025-11-05_mingw13_x86_re2.dll.mcrit) / [x64 PE](data/re2/x64/mcrit/re2_2025-11-05_mingw13_x64_re2.dll.mcrit) | [x86 PE](data/re2/x86/smda/re2_2025-11-05_mingw13_x86_re2.dll.7z) / [x64 PE](data/re2/x64/smda/re2_2025-11-05_mingw13_x64_re2.dll.7z) |
| re2 | 2025-11-05 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/re2/x86/mcrit/re2_2025-11-05_msvc143_x86_re2.dll.mcrit) / [x64 PE](data/re2/x64/mcrit/re2_2025-11-05_msvc143_x64_re2.dll.mcrit) | [x86 PE](data/re2/x86/smda/re2_2025-11-05_msvc143_x86_re2.dll.7z) / [x64 PE](data/re2/x64/smda/re2_2025-11-05_msvc143_x64_re2.dll.7z) |
<!-- /generated -->

### nlohmann/json<a id='nlohmann_json'></a>

nlohmann/json is header-only, so none of it exists in a binary until a translation unit uses it and there is no upstream artefact to disassemble. The reference data comes from compiling a unit that instantiates the templates (`scripts/corpus/exercisers/nlohmann_json.cpp`); the functions in the binary are nlohmann's, the exerciser only selects which.  

Generated with `scripts/build_corpus.py`; see `data/nlohmann_json/provenance.json` for source digests, compiler and flags.

<!-- generated: nlohmann_json -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| nlohmann_json | 3.10.5 | MinGW-w64 GCC 13 | [x86 PE](data/nlohmann_json/x86/mcrit/nlohmann_json_3.10.5_mingw13_x86_nlohmann_json.dll.mcrit) / [x64 PE](data/nlohmann_json/x64/mcrit/nlohmann_json_3.10.5_mingw13_x64_nlohmann_json.dll.mcrit) | [x86 PE](data/nlohmann_json/x86/smda/nlohmann_json_3.10.5_mingw13_x86_nlohmann_json.dll.7z) / [x64 PE](data/nlohmann_json/x64/smda/nlohmann_json_3.10.5_mingw13_x64_nlohmann_json.dll.7z) |
| nlohmann_json | 3.11.3 | MinGW-w64 GCC 13 | [x86 PE](data/nlohmann_json/x86/mcrit/nlohmann_json_3.11.3_mingw13_x86_nlohmann_json.dll.mcrit) / [x64 PE](data/nlohmann_json/x64/mcrit/nlohmann_json_3.11.3_mingw13_x64_nlohmann_json.dll.mcrit) | [x86 PE](data/nlohmann_json/x86/smda/nlohmann_json_3.11.3_mingw13_x86_nlohmann_json.dll.7z) / [x64 PE](data/nlohmann_json/x64/smda/nlohmann_json_3.11.3_mingw13_x64_nlohmann_json.dll.7z) |
| nlohmann_json | 3.11.3 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/nlohmann_json/x86/mcrit/nlohmann_json_3.11.3_msvc143_x86_nlohmann_json.dll.mcrit) / [x64 PE](data/nlohmann_json/x64/mcrit/nlohmann_json_3.11.3_msvc143_x64_nlohmann_json.dll.mcrit) | [x86 PE](data/nlohmann_json/x86/smda/nlohmann_json_3.11.3_msvc143_x86_nlohmann_json.dll.7z) / [x64 PE](data/nlohmann_json/x64/smda/nlohmann_json_3.11.3_msvc143_x64_nlohmann_json.dll.7z) |
| nlohmann_json | 3.12.0 | MinGW-w64 GCC 13 | [x86 PE](data/nlohmann_json/x86/mcrit/nlohmann_json_3.12.0_mingw13_x86_nlohmann_json.dll.mcrit) / [x64 PE](data/nlohmann_json/x64/mcrit/nlohmann_json_3.12.0_mingw13_x64_nlohmann_json.dll.mcrit) | [x86 PE](data/nlohmann_json/x86/smda/nlohmann_json_3.12.0_mingw13_x86_nlohmann_json.dll.7z) / [x64 PE](data/nlohmann_json/x64/smda/nlohmann_json_3.12.0_mingw13_x64_nlohmann_json.dll.7z) |
| nlohmann_json | 3.12.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/nlohmann_json/x86/mcrit/nlohmann_json_3.12.0_msvc143_x86_nlohmann_json.dll.mcrit) / [x64 PE](data/nlohmann_json/x64/mcrit/nlohmann_json_3.12.0_msvc143_x64_nlohmann_json.dll.mcrit) | [x86 PE](data/nlohmann_json/x86/smda/nlohmann_json_3.12.0_msvc143_x86_nlohmann_json.dll.7z) / [x64 PE](data/nlohmann_json/x64/smda/nlohmann_json_3.12.0_msvc143_x64_nlohmann_json.dll.7z) |
<!-- /generated -->

### protobuf<a id='protobuf'></a>

Protocol Buffers, in three generations chosen where the library was rebuilt rather than by recency: 3.6.1 still parses the wire format down the old recursive path (`EpsCopyInputStream` arrives in 3.11, the table-driven parser in 3.19), 21.12 is the last release before the hard Abseil dependency and the generation embedded nearly everywhere, and 31.1 is current and Abseil-based throughout.  
31.1 is built shared so Abseil and utf8_range are imported rather than linked in; about 15% of its functions still demangle to `absl::` names, which are instantiations over protobuf's own types and are in any real protobuf binary.  
Generated with `scripts/build_corpus.py`; see `data/protobuf/provenance.json` for source digests, compiler and flags.

<!-- generated: protobuf -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| protobuf | 3.6.1 | MinGW-w64 GCC 13 | [x86 PE](data/protobuf/x86/mcrit/protobuf_3.6.1_mingw13_x86_protobuf.dll.mcrit) / [x64 PE](data/protobuf/x64/mcrit/protobuf_3.6.1_mingw13_x64_protobuf.dll.mcrit) | [x86 PE](data/protobuf/x86/smda/protobuf_3.6.1_mingw13_x86_protobuf.dll.7z) / [x64 PE](data/protobuf/x64/smda/protobuf_3.6.1_mingw13_x64_protobuf.dll.7z) |
| protobuf | 21.12 | MinGW-w64 GCC 13 | [x86 PE](data/protobuf/x86/mcrit/protobuf_21.12_mingw13_x86_protobuf.dll.mcrit) / [x64 PE](data/protobuf/x64/mcrit/protobuf_21.12_mingw13_x64_protobuf.dll.mcrit) | [x86 PE](data/protobuf/x86/smda/protobuf_21.12_mingw13_x86_protobuf.dll.7z) / [x64 PE](data/protobuf/x64/smda/protobuf_21.12_mingw13_x64_protobuf.dll.7z) |
| protobuf | 21.12 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/protobuf/x86/mcrit/protobuf_21.12_msvc143_x86_protobuf.dll.mcrit) / [x64 PE](data/protobuf/x64/mcrit/protobuf_21.12_msvc143_x64_protobuf.dll.mcrit) | [x86 PE](data/protobuf/x86/smda/protobuf_21.12_msvc143_x86_protobuf.dll.7z) / [x64 PE](data/protobuf/x64/smda/protobuf_21.12_msvc143_x64_protobuf.dll.7z) |
| protobuf | 31.1 | MinGW-w64 GCC 13 | [x86 PE](data/protobuf/x86/mcrit/protobuf_31.1_mingw13_x86_protobuf.dll.mcrit) / [x64 PE](data/protobuf/x64/mcrit/protobuf_31.1_mingw13_x64_protobuf.dll.mcrit) | [x86 PE](data/protobuf/x86/smda/protobuf_31.1_mingw13_x86_protobuf.dll.7z) / [x64 PE](data/protobuf/x64/smda/protobuf_31.1_mingw13_x64_protobuf.dll.7z) |
| protobuf | 31.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/protobuf/x86/mcrit/protobuf_31.1_msvc143_x86_protobuf.dll.mcrit) / [x64 PE](data/protobuf/x64/mcrit/protobuf_31.1_msvc143_x64_protobuf.dll.mcrit) | [x86 PE](data/protobuf/x86/smda/protobuf_31.1_msvc143_x86_protobuf.dll.7z) / [x64 PE](data/protobuf/x64/smda/protobuf_31.1_msvc143_x64_protobuf.dll.7z) |
<!-- /generated -->

### jemalloc<a id='jemalloc'></a>

jemalloc has a real, if niche, Windows presence: Firefox-derived code, and some game and anti-cheat stacks. The C++ wrapper is disabled, because it adds libstdc++ surface without adding allocator code.  

Generated with `scripts/build_corpus.py`; see `data/jemalloc/provenance.json` for source digests, compiler and flags.

<!-- generated: jemalloc -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| jemalloc | 5.3.0 | MinGW-w64 GCC 13 | [x86 PE](data/jemalloc/x86/mcrit/jemalloc_5.3.0_mingw13_x86_jemalloc.dll.mcrit) / [x64 PE](data/jemalloc/x64/mcrit/jemalloc_5.3.0_mingw13_x64_jemalloc.dll.mcrit) | [x86 PE](data/jemalloc/x86/smda/jemalloc_5.3.0_mingw13_x86_jemalloc.dll.7z) / [x64 PE](data/jemalloc/x64/smda/jemalloc_5.3.0_mingw13_x64_jemalloc.dll.7z) |
<!-- /generated -->

### libstdc++<a id='libstdcxx'></a>

`data/MinGW` carries libstdc++ and libsupc++ on x64 but not on x86: the r38 x86 report is mostly Win32 import thunks, with no `_ZN`/`_ZSt` symbols and no libgcc helpers at all, so 32-bit libstdc++ is covered nowhere else in the corpus. This recipe is x86 only for that reason - an x64 build would duplicate what r38 already has.  
Reprocessing the MinGW x86 inputs is the real fix and is a question for the maintainer; this fills the gap in the meantime.  

Generated with `scripts/build_corpus.py`; see `data/libstdc++/provenance.json` for source digests, compiler and flags.

<!-- generated: libstdc++ -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| libstdc++ | 13.2-mingw-w64 | MinGW-w64 GCC 13 | [x86 PE](data/libstdc++/x86/mcrit/libstdc++_13.2-mingw-w64_mingw13_x86_libstdcxx_exerciser.dll.mcrit) | [x86 PE](data/libstdc++/x86/smda/libstdc++_13.2-mingw-w64_mingw13_x86_libstdcxx_exerciser.dll.7z) |
<!-- /generated -->

## Runtimes

Interpreters and virtual machines that are commonly statically linked into tooling.


### Lua<a id='lua'></a>

Lua is the reference implementation of the language, embedded in a great deal of tooling.  
Generated with `scripts/build_corpus.py`; see `data/Lua/provenance.json` for source digests, compiler and flags.

<!-- generated: Lua -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| Lua | 5.1.5 | MinGW-w64 GCC 13 | [x86 PE](data/Lua/x86/mcrit/Lua_5.1.5_mingw13_x86_lua.exe.mcrit) / [x64 PE](data/Lua/x64/mcrit/Lua_5.1.5_mingw13_x64_lua.exe.mcrit) | [x86 PE](data/Lua/x86/smda/Lua_5.1.5_mingw13_x86_lua.exe.7z) / [x64 PE](data/Lua/x64/smda/Lua_5.1.5_mingw13_x64_lua.exe.7z) |
| Lua | 5.1.5 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/Lua/x86/mcrit/Lua_5.1.5_msvc143_x86_lua.exe.mcrit) / [x64 PE](data/Lua/x64/mcrit/Lua_5.1.5_msvc143_x64_lua.exe.mcrit) | [x86 PE](data/Lua/x86/smda/Lua_5.1.5_msvc143_x86_lua.exe.7z) / [x64 PE](data/Lua/x64/smda/Lua_5.1.5_msvc143_x64_lua.exe.7z) |
| Lua | 5.3.6 | MinGW-w64 GCC 13 | [x86 PE](data/Lua/x86/mcrit/Lua_5.3.6_mingw13_x86_lua.exe.mcrit) / [x64 PE](data/Lua/x64/mcrit/Lua_5.3.6_mingw13_x64_lua.exe.mcrit) | [x86 PE](data/Lua/x86/smda/Lua_5.3.6_mingw13_x86_lua.exe.7z) / [x64 PE](data/Lua/x64/smda/Lua_5.3.6_mingw13_x64_lua.exe.7z) |
| Lua | 5.4.8 | MinGW-w64 GCC 13 | [x86 PE](data/Lua/x86/mcrit/Lua_5.4.8_mingw13_x86_lua.exe.mcrit) / [x64 PE](data/Lua/x64/mcrit/Lua_5.4.8_mingw13_x64_lua.exe.mcrit) | [x86 PE](data/Lua/x86/smda/Lua_5.4.8_mingw13_x86_lua.exe.7z) / [x64 PE](data/Lua/x64/smda/Lua_5.4.8_mingw13_x64_lua.exe.7z) |
| Lua | 5.4.8 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/Lua/x86/mcrit/Lua_5.4.8_msvc143_x86_lua.exe.mcrit) / [x64 PE](data/Lua/x64/mcrit/Lua_5.4.8_msvc143_x64_lua.exe.mcrit) | [x86 PE](data/Lua/x86/smda/Lua_5.4.8_msvc143_x86_lua.exe.7z) / [x64 PE](data/Lua/x64/smda/Lua_5.4.8_msvc143_x64_lua.exe.7z) |
<!-- /generated -->

### LuaJIT<a id='luajit'></a>

LuaJIT is the runtime behind the toolkit named in issue #1; the reusable machine code an analyst meets is this interpreter and JIT core, statically linked in. Upstream carries no git tags, so versions are pinned to the commit that set the version string.  
Generated with `scripts/build_corpus.py`; see `data/LuaJIT/provenance.json` for source digests, compiler and flags.

<!-- generated: LuaJIT -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| LuaJIT | 2.0.5 | MinGW-w64 GCC 13 | [x86 PE](data/LuaJIT/x86/mcrit/LuaJIT_2.0.5_mingw13_x86_lua51.dll.mcrit) / [x64 PE](data/LuaJIT/x64/mcrit/LuaJIT_2.0.5_mingw13_x64_lua51.dll.mcrit) | [x86 PE](data/LuaJIT/x86/smda/LuaJIT_2.0.5_mingw13_x86_lua51.dll.7z) / [x64 PE](data/LuaJIT/x64/smda/LuaJIT_2.0.5_mingw13_x64_lua51.dll.7z) |
| LuaJIT | 2.0.5 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/LuaJIT/x86/mcrit/LuaJIT_2.0.5_msvc143_x86_lua51.dll.mcrit) / [x64 PE](data/LuaJIT/x64/mcrit/LuaJIT_2.0.5_msvc143_x64_lua51.dll.mcrit) | [x86 PE](data/LuaJIT/x86/smda/LuaJIT_2.0.5_msvc143_x86_lua51.dll.7z) / [x64 PE](data/LuaJIT/x64/smda/LuaJIT_2.0.5_msvc143_x64_lua51.dll.7z) |
| LuaJIT | 2.1.0-beta3 | MinGW-w64 GCC 13 | [x86 PE](data/LuaJIT/x86/mcrit/LuaJIT_2.1.0-beta3_mingw13_x86_lua51.dll.mcrit) / [x64 PE](data/LuaJIT/x64/mcrit/LuaJIT_2.1.0-beta3_mingw13_x64_lua51.dll.mcrit) | [x86 PE](data/LuaJIT/x86/smda/LuaJIT_2.1.0-beta3_mingw13_x86_lua51.dll.7z) / [x64 PE](data/LuaJIT/x64/smda/LuaJIT_2.1.0-beta3_mingw13_x64_lua51.dll.7z) |
| LuaJIT | 2.1.0-beta3 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/LuaJIT/x86/mcrit/LuaJIT_2.1.0-beta3_msvc143_x86_lua51.dll.mcrit) / [x64 PE](data/LuaJIT/x64/mcrit/LuaJIT_2.1.0-beta3_msvc143_x64_lua51.dll.mcrit) | [x86 PE](data/LuaJIT/x86/smda/LuaJIT_2.1.0-beta3_msvc143_x86_lua51.dll.7z) / [x64 PE](data/LuaJIT/x64/smda/LuaJIT_2.1.0-beta3_msvc143_x64_lua51.dll.7z) |
| LuaJIT | 2.1-rolling-2026-09-08 | MinGW-w64 GCC 13 | [x86 PE](data/LuaJIT/x86/mcrit/LuaJIT_2.1-rolling-2026-09-08_mingw13_x86_lua51.dll.mcrit) / [x64 PE](data/LuaJIT/x64/mcrit/LuaJIT_2.1-rolling-2026-09-08_mingw13_x64_lua51.dll.mcrit) | [x86 PE](data/LuaJIT/x86/smda/LuaJIT_2.1-rolling-2026-09-08_mingw13_x86_lua51.dll.7z) / [x64 PE](data/LuaJIT/x64/smda/LuaJIT_2.1-rolling-2026-09-08_mingw13_x64_lua51.dll.7z) |
<!-- /generated -->

### q3vm<a id='q3vm'></a>

q3vm is a standalone Quake 3 QVM interpreter. Its vm.c is written to be dropped into other projects, so the same shape appears in Quake3-engine derivatives and anything embedding a QVM sandbox.  
Generated with `scripts/build_corpus.py`; see `data/q3vm/provenance.json` for source digests, compiler and flags.

<!-- generated: q3vm -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| q3vm | 1.3.1 | MinGW-w64 GCC 13 | [x86 PE](data/q3vm/x86/mcrit/q3vm_1.3.1_mingw13_x86_q3vm.exe.mcrit) / [x64 PE](data/q3vm/x64/mcrit/q3vm_1.3.1_mingw13_x64_q3vm.exe.mcrit) | [x86 PE](data/q3vm/x86/smda/q3vm_1.3.1_mingw13_x86_q3vm.exe.7z) / [x64 PE](data/q3vm/x64/smda/q3vm_1.3.1_mingw13_x64_q3vm.exe.7z) |
| q3vm | 1.3.1 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/q3vm/x86/mcrit/q3vm_1.3.1_msvc143_x86_q3vm.exe.mcrit) / [x64 PE](data/q3vm/x64/mcrit/q3vm_1.3.1_msvc143_x64_q3vm.exe.mcrit) | [x86 PE](data/q3vm/x86/smda/q3vm_1.3.1_msvc143_x86_q3vm.exe.7z) / [x64 PE](data/q3vm/x64/smda/q3vm_1.3.1_msvc143_x64_q3vm.exe.7z) |
| q3vm | 2026-03-06 | MinGW-w64 GCC 13 | [x86 PE](data/q3vm/x86/mcrit/q3vm_2026-03-06_mingw13_x86_q3vm.exe.mcrit) / [x64 PE](data/q3vm/x64/mcrit/q3vm_2026-03-06_mingw13_x64_q3vm.exe.mcrit) | [x86 PE](data/q3vm/x86/smda/q3vm_2026-03-06_mingw13_x86_q3vm.exe.7z) / [x64 PE](data/q3vm/x64/smda/q3vm_2026-03-06_mingw13_x64_q3vm.exe.7z) |
| q3vm | 2026-03-06 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/q3vm/x86/mcrit/q3vm_2026-03-06_msvc143_x86_q3vm.exe.mcrit) / [x64 PE](data/q3vm/x64/mcrit/q3vm_2026-03-06_msvc143_x64_q3vm.exe.mcrit) | [x86 PE](data/q3vm/x86/smda/q3vm_2026-03-06_msvc143_x86_q3vm.exe.7z) / [x64 PE](data/q3vm/x64/smda/q3vm_2026-03-06_msvc143_x64_q3vm.exe.7z) |
<!-- /generated -->

## Loaders and shellcode

Position-independent loaders and the projects that generate them. Entries marked as compiled by MSVC are blobs committed upstream and disassembled as buffers, not rebuilt here.


### donut<a id='donut'></a>

donut generates position-independent loaders. What is covered here is the loader, not the generator: the loader is the code donut embeds in whatever it packages, so it is what turns up in samples, and upstream commits it MSVC-compiled in `loader_exe_x86.h` and `loader_exe_x64.h` - the same bytes that ship in the release binaries and the PyPI package.  
The generator is deliberately not built. It statically links the vendored `lib/aplib64.lib`, and aPLib is already a family here, so building it would duplicate aPLib under donut's name. Note that the loader blobs contain aPLib's *depacker* (`loader/depack.c`) for the same reason - that much is unavoidable, since it is part of the shipped loader.  
Generated with `scripts/build_corpus.py`; see `data/donut/provenance.json` for source digests, compiler and flags.

<!-- generated: donut -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| donut | 1.1 | MSVC (as committed upstream) | [x86 code](data/donut/x86/mcrit/donut_1.1_msvc_x86_loader_x86.mcrit) / [x64 code](data/donut/x64/mcrit/donut_1.1_msvc_x64_loader_x64.mcrit) | [x86 code](data/donut/x86/smda/donut_1.1_msvc_x86_loader_x86.7z) / [x64 code](data/donut/x64/smda/donut_1.1_msvc_x64_loader_x64.7z) |
<!-- /generated -->

### MemoryModule<a id='memorymodule'></a>

MemoryModule is the canonical in-memory PE loader, reused verbatim by a long tail of packers and loaders, almost always as a vendored copy frozen at some old commit.  
Generated with `scripts/build_corpus.py`; see `data/MemoryModule/provenance.json` for source digests, compiler and flags.

<!-- generated: MemoryModule -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| MemoryModule | 0.0.4 | MinGW-w64 GCC 13 | [x86 PE](data/MemoryModule/x86/mcrit/MemoryModule_0.0.4_mingw13_x86_DllLoader.exe.mcrit) / [x64 PE](data/MemoryModule/x64/mcrit/MemoryModule_0.0.4_mingw13_x64_DllLoader.exe.mcrit) | [x86 PE](data/MemoryModule/x86/smda/MemoryModule_0.0.4_mingw13_x86_DllLoader.exe.7z) / [x64 PE](data/MemoryModule/x64/smda/MemoryModule_0.0.4_mingw13_x64_DllLoader.exe.7z) |
| MemoryModule | 2019-02-24 | MinGW-w64 GCC 13 | [x86 PE](data/MemoryModule/x86/mcrit/MemoryModule_2019-02-24_mingw13_x86_DllLoader.exe.mcrit) / [x64 PE](data/MemoryModule/x64/mcrit/MemoryModule_2019-02-24_mingw13_x64_DllLoader.exe.mcrit) | [x86 PE](data/MemoryModule/x86/smda/MemoryModule_2019-02-24_mingw13_x86_DllLoader.exe.7z) / [x64 PE](data/MemoryModule/x64/smda/MemoryModule_2019-02-24_mingw13_x64_DllLoader.exe.7z) |
| MemoryModule | 2019-02-24 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/MemoryModule/x86/mcrit/MemoryModule_2019-02-24_msvc143_x86_DllLoader.exe.mcrit) / [x64 PE](data/MemoryModule/x64/mcrit/MemoryModule_2019-02-24_msvc143_x64_DllLoader.exe.mcrit) | [x86 PE](data/MemoryModule/x86/smda/MemoryModule_2019-02-24_msvc143_x86_DllLoader.exe.7z) / [x64 PE](data/MemoryModule/x64/smda/MemoryModule_2019-02-24_msvc143_x64_DllLoader.exe.7z) |
<!-- /generated -->

### pe_to_shellcode<a id='pe_to_shellcode'></a>

pe_to_shellcode converts PE files to shellcode. The stub2 loaders committed upstream are covered; they are MSVC-built and cannot be reproduced without Visual Studio.  
Generated with `scripts/build_corpus.py`; see `data/pe_to_shellcode/provenance.json` for source digests, compiler and flags.

<!-- generated: pe_to_shellcode -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| pe_to_shellcode | 1.0 | MSVC (as committed upstream) | [x86 code](data/pe_to_shellcode/x86/mcrit/pe_to_shellcode_1.0_msvc_x86_stub2_x86.mcrit) / [x64 code](data/pe_to_shellcode/x64/mcrit/pe_to_shellcode_1.0_msvc_x64_stub2_x64.mcrit) | [x86 code](data/pe_to_shellcode/x86/smda/pe_to_shellcode_1.0_msvc_x86_stub2_x86.7z) / [x64 code](data/pe_to_shellcode/x64/smda/pe_to_shellcode_1.0_msvc_x64_stub2_x64.7z) |
| pe_to_shellcode | 1.2 | MSVC (as committed upstream) | [x86 code](data/pe_to_shellcode/x86/mcrit/pe_to_shellcode_1.2_msvc_x86_stub2_x86.mcrit) / [x64 code](data/pe_to_shellcode/x64/mcrit/pe_to_shellcode_1.2_msvc_x64_stub2_x64.mcrit) | [x86 code](data/pe_to_shellcode/x86/smda/pe_to_shellcode_1.2_msvc_x86_stub2_x86.7z) / [x64 code](data/pe_to_shellcode/x64/smda/pe_to_shellcode_1.2_msvc_x64_stub2_x64.7z) |
<!-- /generated -->

### sRDI<a id='srdi'></a>

sRDI implements reflective DLL injection. The compiled MSVC blobs committed upstream are covered rather than a rebuild, since those are what is encountered in the wild.  
Generated with `scripts/build_corpus.py`; see `data/sRDI/provenance.json` for source digests, compiler and flags.

<!-- generated: sRDI -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| sRDI | 2018-05-27 | MSVC (as committed upstream) | [x86 code](data/sRDI/x86/mcrit/sRDI_2018-05-27_msvc_x86_ShellcodeRDI_x86.mcrit) / [x64 code](data/sRDI/x64/mcrit/sRDI_2018-05-27_msvc_x64_ShellcodeRDI_x64.mcrit) | [x86 code](data/sRDI/x86/smda/sRDI_2018-05-27_msvc_x86_ShellcodeRDI_x86.7z) / [x64 code](data/sRDI/x64/smda/sRDI_2018-05-27_msvc_x64_ShellcodeRDI_x64.7z) |
| sRDI | 2020-04-15 | MSVC (as committed upstream) | [x86 code](data/sRDI/x86/mcrit/sRDI_2020-04-15_msvc_x86_ShellcodeRDI_x86.mcrit) / [x64 code](data/sRDI/x64/mcrit/sRDI_2020-04-15_msvc_x64_ShellcodeRDI_x64.mcrit) | [x86 code](data/sRDI/x86/smda/sRDI_2020-04-15_msvc_x86_ShellcodeRDI_x86.7z) / [x64 code](data/sRDI/x64/smda/sRDI_2020-04-15_msvc_x64_ShellcodeRDI_x64.7z) |
| sRDI | 2022-06-17 | MSVC (as committed upstream) | [x86 code](data/sRDI/x86/mcrit/sRDI_2022-06-17_msvc_x86_ShellcodeRDI_x86.mcrit) / [x64 code](data/sRDI/x64/mcrit/sRDI_2022-06-17_msvc_x64_ShellcodeRDI_x64.mcrit) | [x86 code](data/sRDI/x86/smda/sRDI_2022-06-17_msvc_x86_ShellcodeRDI_x86.7z) / [x64 code](data/sRDI/x64/smda/sRDI_2022-06-17_msvc_x64_ShellcodeRDI_x64.7z) |
<!-- /generated -->

## Heaven's Gate and WOW64 transitions

Implementations of the WOW64 transition: reaching 64-bit code, and the 64-bit ntdll, from a 32-bit process. Every one of them is x86 by construction rather than by choice - they truncate pointers to `uint32_t`, read `CONTEXT.Ebx`, or use inline assembly that x64 MSVC does not implement - so each is built for x86 only.

### wow64pp<a id='wow64pp'></a>

A header-only Heaven's Gate implementation whose gate is a `constexpr` byte array copied into RWX memory rather than assembly, which is what lets it build with GCC as well as MSVC. Nothing of it exists in a binary until a translation unit uses it, so the reference data comes from an exerciser that instantiates the public surface and the `detail::` layer behind it, including both `call_function` arities - the four-argument-or-fewer and the more-than-four paths are different code. Every function in the header is `inline`, so the exerciser takes each one's address as well as calling it.  

Generated with `scripts/build_corpus.py`; see `data/wow64pp/provenance.json` for source digests, compiler and flags.

<!-- generated: wow64pp -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| wow64pp | 2020-09-19 | MinGW-w64 GCC 13 | [x86 PE](data/wow64pp/x86/mcrit/wow64pp_2020-09-19_mingw13_x86_wow64pp.dll.mcrit) | [x86 PE](data/wow64pp/x86/smda/wow64pp_2020-09-19_mingw13_x86_wow64pp.dll.7z) |
| wow64pp | 2020-09-19 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/wow64pp/x86/mcrit/wow64pp_2020-09-19_msvc143_x86_wow64pp.dll.mcrit) | [x86 PE](data/wow64pp/x86/smda/wow64pp_2020-09-19_msvc143_x86_wow64pp.dll.7z) |
<!-- /generated -->

### RtlWow64<a id='rtlwow64'></a>

A WOW64 transition library that exposes the 64-bit ntdll to 32-bit code, through `RtlInvokeX64` and a family of `RtlGetProcAddressWow64` helpers. Unlike most Heaven's Gate code it ships as a DLL with an eleven-symbol export table, so it is linked rather than copied and the same names appear wherever it is used. 26 functions, 17 of them the library's own.  

Generated with `scripts/build_corpus.py`; see `data/RtlWow64/provenance.json` for source digests, compiler and flags.

<!-- generated: RtlWow64 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| RtlWow64 | 2021-02-12 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/RtlWow64/x86/mcrit/RtlWow64_2021-02-12_msvc143_x86_RtlWow64.dll.mcrit) | [x86 PE](data/RtlWow64/x86/smda/RtlWow64_2021-02-12_msvc143_x86_RtlWow64.dll.7z) |
<!-- /generated -->

### wowGrail<a id='wowgrail'></a>

Issues 32-bit direct syscalls by walking the WOW64 ntdll and calling `Wow64SystemServiceEx`, rather than by the usual far-return gate. It is a proof-of-concept executable rather than a library, so what is recorded is the tool itself. Built `Release|Win32` specifically, which upstream requires because Debug instrumentation moves the memory layout the technique depends on. Of its 41 functions only 9 are wowGrail's own; the rest is the `std::string` and `std::wstring` machinery its `get64b_CSTR` and `get64b_WSTR` helpers instantiate.  

Generated with `scripts/build_corpus.py`; see `data/wowGrail/provenance.json` for source digests, compiler and flags.

<!-- generated: wowGrail -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| wowGrail | 2021-05-27 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/wowGrail/x86/mcrit/wowGrail_2021-05-27_msvc143_x86_wowGrail.exe.mcrit) | [x86 PE](data/wowGrail/x86/smda/wowGrail_2021-05-27_msvc143_x86_wowGrail.exe.7z) |
<!-- /generated -->

### HeavensGate2<a id='heavensgate2'></a>

A compact Heaven's Gate implementation reaching 64-bit code from a 32-bit process by far-returning through selector 0x33. The gate is a patched byte array rather than assembly, which is what lets it carry no MSVC-only assembly syntax at all. Built with optimization and inlining disabled as its project file specifies, and with no C runtime in the image - it links `IgnoreAllDefaultLibraries` with `main` as the entry point, which is why the runtime filter is turned off for it. 15 functions, 12 of them its own.  

Generated with `scripts/build_corpus.py`; see `data/HeavensGate2/provenance.json` for source digests, compiler and flags.

<!-- generated: HeavensGate2 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| HeavensGate2 | 2017-07-23 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/HeavensGate2/x86/mcrit/HeavensGate2_2017-07-23_msvc143_x86_HeavensGate.exe.mcrit) | [x86 PE](data/HeavensGate2/x86/smda/HeavensGate2_2017-07-23_msvc143_x86_HeavensGate.exe.7z) |
<!-- /generated -->

### NTTITONHeavensGate<a id='nttitonheavensgate'></a>

A second Heaven's Gate demonstration, and a useful contrast to the others: it implements the gate in `__declspec(naked)` functions with full inline assembly rather than in patched byte arrays, so its emitted shape differs even though the technique is the same. Only the `Heavens Gate` subdirectory of its repository is compiled - one named translation unit, nothing globbed - and nothing else in that tree is built, referenced or recorded. The repository ships no build system, so the compile and link lines come from the recipe. 26 functions, 20 of them its own.  

Generated with `scripts/build_corpus.py`; see `data/NTTITONHeavensGate/provenance.json` for source digests, compiler and flags.

<!-- generated: NTTITONHeavensGate -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| NTTITONHeavensGate | 2017-06-16 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/NTTITONHeavensGate/x86/mcrit/NTTITONHeavensGate_2017-06-16_msvc143_x86_HeavensGate.exe.mcrit) | [x86 PE](data/NTTITONHeavensGate/x86/smda/NTTITONHeavensGate_2017-06-16_msvc143_x86_HeavensGate.exe.7z) |
<!-- /generated -->

## WinAPI obfuscation

Projects that hide which Windows APIs a binary calls - by resolving imports from hashes at run time, or by rewriting the import table so a call appears to target something else.

### WinApiObfuscator<a id='winapiobfuscator'></a>

Resolves imports at run time by hashing export names with MurmurHash2A, so the import table carries no recognisable API names. The hash and the export-table walk are ordinary out-of-line functions; the rest is a template wrapper instantiated once per resolved function type, which is why the artefact is almost entirely the library's own code - 170 of 180 functions on x64 and 194 of 204 on x86. Built at `/Od`: the level was chosen cautiously rather than measured, because at `/O2` much of the wrapper collapses into its callers.  

Generated with `scripts/build_corpus.py`; see `data/WinApiObfuscator/provenance.json` for source digests, compiler and flags.

<!-- generated: WinApiObfuscator -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| WinApiObfuscator | 2.0.0.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/WinApiObfuscator/x86/mcrit/WinApiObfuscator_2.0.0.0_msvc143_x86_winapi_obfuscator.dll.mcrit) / [x64 PE](data/WinApiObfuscator/x64/mcrit/WinApiObfuscator_2.0.0.0_msvc143_x64_winapi_obfuscator.dll.mcrit) | [x86 PE](data/WinApiObfuscator/x86/smda/WinApiObfuscator_2.0.0.0_msvc143_x86_winapi_obfuscator.dll.7z) / [x64 PE](data/WinApiObfuscator/x64/smda/WinApiObfuscator_2.0.0.0_msvc143_x64_winapi_obfuscator.dll.7z) |
<!-- /generated -->

### nt_wrapper<a id='nt_wrapper'></a>

A header-only C++20 wrapper over the native NT API, built against a pinned copy of phnt rather than a vcpkg-resolved one. Built at `/Od`, and not as a preference: `NTW_INLINE` is `__forceinline` and appears 958 times across 56 headers, so at `/O2` cl folds essentially the whole library into its caller and there is nothing left to record - upstream's own test CMakeLists forces `/Od` even in Release for the same reason. The consequence is worth stating rather than leaving to be discovered: this sample describes an unoptimised consumer, and an `/O2` consumer has hardly any nt_wrapper functions left to match.  
The exerciser is five translation units rather than one, each compiled with failure tolerated and the link taking whatever objects were produced, so one bad spelling costs one slice of coverage instead of the family. That is safe here only because every function the library provides is inline. 140 functions on each architecture, 126 of them the library's own.  

Generated with `scripts/build_corpus.py`; see `data/nt_wrapper/provenance.json` for source digests, compiler and flags.

<!-- generated: nt_wrapper -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| nt_wrapper | 2021-02-02 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/nt_wrapper/x86/mcrit/nt_wrapper_2021-02-02_msvc143_x86_nt_wrapper.dll.mcrit) / [x64 PE](data/nt_wrapper/x64/mcrit/nt_wrapper_2021-02-02_msvc143_x64_nt_wrapper.dll.mcrit) | [x86 PE](data/nt_wrapper/x86/smda/nt_wrapper_2021-02-02_msvc143_x86_nt_wrapper.dll.7z) / [x64 PE](data/nt_wrapper/x64/smda/nt_wrapper_2021-02-02_msvc143_x64_nt_wrapper.dll.7z) |
<!-- /generated -->

### APICallProxy<a id='apicallproxy'></a>

Proxies Win32 calls through a kernel driver, so the work a process appears to do in user mode is performed by `APICallProxy.sys` on its behalf via IOCTLs. The driver is the only part worth recording - the seven user-mode executables beside it hold one to four functions each and cannot clear the eight-function floor. Built `Release|x64` only, which is the single project configuration carrying the link libraries. This is the corpus's first kernel-mode artefact: the runner's WDK was confirmed present by probe rather than assumed, and the recipe records that a `.sys` links runtime the msvcrt/ucrt baseline cannot recognise, so some kernel glue stays under this family's name.  
It also vendors two third parties without reproducing their terms: `DisableDSE/hde64.h` is Vyacheslav Patkov's Hacker Disassembler Engine, carrying a copyright line and no grant of permission, and roughly 25 of its functions are wbenny/KSOCKET's `Ks*` socket layer renamed to `APIProxy*` - that one is MIT, so what is missing is the attribution rather than the permission.  

Generated with `scripts/build_corpus.py`; see `data/APICallProxy/provenance.json` for source digests, compiler and flags.

<!-- generated: APICallProxy -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| APICallProxy | 2022-12-09 | MSVC 19.44 (Visual Studio 2022, v143) | [x64 PE](data/APICallProxy/x64/mcrit/APICallProxy_2022-12-09_msvc143_x64_APICallProxy.sys.mcrit) | [x64 PE](data/APICallProxy/x64/smda/APICallProxy_2022-12-09_msvc143_x64_APICallProxy.sys.7z) |
<!-- /generated -->

### CallObfuscator<a id='callobfuscator'></a>

Rewrites a PE's import table so calls to one API appear to target another. What is recorded is the tool, not its output - a patched binary is somebody else's code with this project's edits applied. Its injected shellcode is worth knowing about: it is not a byte blob but ordinary C++ static member functions, each `__declspec(noinline)` and address-taken in a static table, so the linker can neither discard nor fold them. The x86 artefact carries 89 unnamed functions against x64's none; those are the `__ehhandler$` and `__unwindfunclet$` fragments that 32-bit C++ exception handling emits and the PDB records no symbol for, which is why the symbol gate ignores functions below three instructions.  

Generated with `scripts/build_corpus.py`; see `data/CallObfuscator/provenance.json` for source digests, compiler and flags.

<!-- generated: CallObfuscator -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| CallObfuscator | 2.0 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/CallObfuscator/x86/mcrit/CallObfuscator_2.0_msvc143_x86_cobf.exe.mcrit) / [x64 PE](data/CallObfuscator/x64/mcrit/CallObfuscator_2.0_msvc143_x64_cobf.exe.mcrit) | [x86 PE](data/CallObfuscator/x86/smda/CallObfuscator_2.0_msvc143_x86_cobf.exe.7z) / [x64 PE](data/CallObfuscator/x64/smda/CallObfuscator_2.0_msvc143_x64_cobf.exe.7z) |
<!-- /generated -->

## Offensive tooling

Public offensive-tooling code bases that are copied into implants more or less verbatim. Every one of them needs Visual Studio - ATL, the DIA SDK, MASM, or in BlackBone's driver's case a WDK - and they are built on a windows-2022 runner by `.github/workflows/windows-reference-data.yml` rather than approximated with GCC.
### VX-API<a id='vx-api'></a>

A collection of Win32 API-abuse routines. Upstream ships no static-library or DLL configuration, so the sources are compiled into one and linked with `/OPT:NOREF`, which keeps routines nothing calls - the point here is coverage, not a minimal binary. A small number of sources need ATL or `__try`/`__except` and are skipped.  

Generated with `scripts/build_corpus.py`; see `data/VX-API/provenance.json` for source digests, compiler and flags.

<!-- generated: VX-API -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| VX-API | 2.01.015 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/VX-API/x86/mcrit/VX-API_2.01.015_msvc143_x86_vxapi.dll.mcrit) / [x64 PE](data/VX-API/x64/mcrit/VX-API_2.01.015_msvc143_x64_vxapi.dll.mcrit) | [x86 PE](data/VX-API/x86/smda/VX-API_2.01.015_msvc143_x86_vxapi.dll.7z) / [x64 PE](data/VX-API/x64/smda/VX-API_2.01.015_msvc143_x64_vxapi.dll.7z) |
<!-- /generated -->

### BlackBone<a id='blackbone'></a>

A Windows memory-hacking library: process and module management, manual PE mapping, local and remote hooking, pattern search. Built in its `Release(DLL)` configuration, which statically compiles the vendored AsmJit and rewolf-wow64ext sources into the same image - so functions from those projects are present here under the BlackBone family, as they are in any real BlackBone DLL. BeaEngine is imported from its own DLL and is not. The kernel driver is a separate family, [BlackBoneDrv](#blackbonedrv), because it shares no code with this image.  

Generated with `scripts/build_corpus.py`; see `data/BlackBone/provenance.json` for source digests, compiler and flags.

<!-- generated: BlackBone -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| BlackBone | 2023-07-17 | MSVC 19.44 (Visual Studio 2022, v143) | [x86 PE](data/BlackBone/x86/mcrit/BlackBone_2023-07-17_msvc143_x86_BlackBone.dll.mcrit) / [x64 PE](data/BlackBone/x64/mcrit/BlackBone_2023-07-17_msvc143_x64_BlackBone.dll.mcrit) | [x86 PE](data/BlackBone/x86/smda/BlackBone_2023-07-17_msvc143_x86_BlackBone.dll.7z) / [x64 PE](data/BlackBone/x64/smda/BlackBone_2023-07-17_msvc143_x64_BlackBone.dll.7z) |
<!-- /generated -->

### BlackBoneDrv<a id='blackbonedrv'></a>

BlackBone's kernel driver, from the same commit as the library above and in its own solution. It does from ring 0 what the library cannot do from ring 3: manually maps images into other processes, injects and queues APCs, remaps one process's memory into another, edits VAD nodes and PTEs to hide or reprotect regions, hooks the SSDT and patches handle-table entries - all reached from user mode through a single `DeviceIoControl` switch. A separate family rather than a second component of `BlackBone`, because the two images have not one function in common: that one is C++ linked against the ucrt, this is C compiled against `ntifs.h`. Built `Win10Release|x64`, which is upstream's own CI configuration and the only one of the four whose undocumented structure layouts describe a kernel anyone still runs; all eight of the project's configurations are x64 and it refuses to compile for x86 at all.  
Read its 321 functions with two subtractions in mind. 58 of them are not code at all: they are MSVC string-literal COMDAT symbols (`??_C@_...`), which sit in the driver's code sections and are disassembled as one- to six-instruction fragments. A further 112 reach three instructions or fewer, almost all of them import thunks into `ntoskrnl`. What is left is 144 functions of ten instructions or more, which is the driver's own code and lines up with the 139 functions counted in its source - the small excess being static helpers and AVL callbacks the file-by-file count does not reach. Match quality should be judged on those 144, not on 321.

Eight of them are not this project's code, and a match on those eight is a match on Windows kernel source: `ldrreloc.c`'s four `Ldr*` relocation routines say in the file that they are Windows Research Kernel source, usable only under a licence agreement the repository does not carry, and `VadHelpers.c`'s four `Mi*` AVL routines are the same kernel's code carried in without a copyright header at all.  

Generated with `scripts/build_corpus.py`; see `data/BlackBoneDrv/provenance.json` for source digests, compiler and flags.

<!-- generated: BlackBoneDrv -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| BlackBoneDrv | 2023-07-17 | MSVC 19.44 (Visual Studio 2022, v143) | [x64 PE](data/BlackBoneDrv/x64/mcrit/BlackBoneDrv_2023-07-17_msvc143_x64_BlackBoneDrv10.sys.mcrit) | [x64 PE](data/BlackBoneDrv/x64/smda/BlackBoneDrv_2023-07-17_msvc143_x64_BlackBoneDrv10.sys.7z) |
<!-- /generated -->

### SysWhispers<a id='syswhispers'></a>

The v1 generator, whose stubs resolve their own syscall number inline: each loads the PEB from `gs:[60h]` and walks major version, minor version and build number down a chain of comparisons before issuing the syscall. That ladder is the recognisable part, and it is what an implant carries when it copies this generator's output. SysWhispers2 and 3 emit 2- to 15-instruction stubs that differ only by one immediate and would form a large, low-value cluster, so they are not covered.  
The DLL holds the generated stubs and nothing else - no C runtime, no entry point - and exports them so each carries its name.  

Generated with `scripts/build_corpus.py`; see `data/SysWhispers/provenance.json` for source digests, compiler and flags.

<!-- generated: SysWhispers -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| SysWhispers | 2021-07-06 | MSVC 19.44 (Visual Studio 2022, v143) | [x64 PE](data/SysWhispers/x64/mcrit/SysWhispers_2021-07-06_msvc143_x64_syscalls.dll.mcrit) | [x64 PE](data/SysWhispers/x64/smda/SysWhispers_2021-07-06_msvc143_x64_syscalls.dll.7z) |
<!-- /generated -->

## String obfuscation

Four compile-time string obfuscators, which hide literals by encrypting them during compilation and decrypting on first use, and one post-build patcher that does the same job from outside the compiler. None of the four exists in a binary until something uses it - the C++ ones are header-only and almost entirely `constexpr`, and the Rust one encodes in `const` context - so the reference data comes from an exerciser or driver that uses the library; the functions recorded are the library's own.

These are the one group here where the optimization level is not a free choice, and it differs per project - the level each was built at is recorded in `build_flags` and argued in `notes`, because it decides what survives into the binary at all. Reference data built at one level will not match a consumer built at another.

All four of the compile-time obfuscators are portable, and all four are also built for Linux: these are the corpus's only ELF artefacts, and every one of them is an ELF row beside the PE row in the same table. Same pinned commit, same exerciser or driver, same optimization level - only the container differs, so the two are directly comparable. They are shared objects rather than executables on purpose: a `-shared` ELF links glibc, libstdc++ and libm dynamically, so none of their code enters the sample under a library's name, and they are built `-fvisibility=hidden` so that only the exerciser's entry point is exported and the library's own calls stay direct, which is what the PE builds get for free from `__declspec(dllexport)`.

### Obfuscate<a id='obfuscate'></a>

adamyaxley/Obfuscate encrypts each literal with a key derived from its source line and decrypts it on first use. It instantiates per (length, line), so a binary carries one small cluster of functions per obfuscated string rather than one shared routine. Built at `-O0`: at `-O2` every instantiation collapses to a five-byte `endbr64; ret` stub, because the destructor's zeroing loop is dead-store eliminated and the function survives only because `thread_local` takes its address.  

Generated with `scripts/build_corpus.py`; see `data/Obfuscate/provenance.json` for source digests, compiler and flags.

<!-- generated: Obfuscate -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| Obfuscate | 2026-06-03 | GCC 13 (Linux, glibc) | [x86 ELF](data/Obfuscate/x86/mcrit/Obfuscate_2026-06-03_gcc13_x86_ay_obfuscate.so.mcrit) / [x64 ELF](data/Obfuscate/x64/mcrit/Obfuscate_2026-06-03_gcc13_x64_ay_obfuscate.so.mcrit) | [x86 ELF](data/Obfuscate/x86/smda/Obfuscate_2026-06-03_gcc13_x86_ay_obfuscate.so.7z) / [x64 ELF](data/Obfuscate/x64/smda/Obfuscate_2026-06-03_gcc13_x64_ay_obfuscate.so.7z) |
| Obfuscate | 2026-06-03 | MinGW-w64 GCC 13 | [x86 PE](data/Obfuscate/x86/mcrit/Obfuscate_2026-06-03_mingw13_x86_ay_obfuscate.dll.mcrit) / [x64 PE](data/Obfuscate/x64/mcrit/Obfuscate_2026-06-03_mingw13_x64_ay_obfuscate.dll.mcrit) | [x86 PE](data/Obfuscate/x86/smda/Obfuscate_2026-06-03_mingw13_x86_ay_obfuscate.dll.7z) / [x64 PE](data/Obfuscate/x64/smda/Obfuscate_2026-06-03_mingw13_x64_ay_obfuscate.dll.7z) |
<!-- /generated -->

### StringObfuscatorCT<a id='stringobfuscatorct'></a>

Snowapril's compile-time obfuscator, instantiated per call site through `__COUNTER__`, so even identical strings at different sites emit different functions. Built at `-O0`, which is the only level that emits anything: there is no `constexpr` variable forcing compile-time evaluation, so at `-O0` the encryption is emitted as real runtime code and at `-O1` and above it inlines into the caller and disappears entirely.  
Built with `SOURCE_DATE_EPOCH` pinned, because upstream seeds its generator from `__TIME__` and without that the cipher constants and the mangled symbol names change on every rebuild.  

Generated with `scripts/build_corpus.py`; see `data/StringObfuscatorCT/provenance.json` for source digests, compiler and flags.

<!-- generated: StringObfuscatorCT -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| StringObfuscatorCT | 2019-12-11 | GCC 13 (Linux, glibc) | [x86 ELF](data/StringObfuscatorCT/x86/mcrit/StringObfuscatorCT_2019-12-11_gcc13_x86_snowapril_obfuscator.so.mcrit) / [x64 ELF](data/StringObfuscatorCT/x64/mcrit/StringObfuscatorCT_2019-12-11_gcc13_x64_snowapril_obfuscator.so.mcrit) | [x86 ELF](data/StringObfuscatorCT/x86/smda/StringObfuscatorCT_2019-12-11_gcc13_x86_snowapril_obfuscator.so.7z) / [x64 ELF](data/StringObfuscatorCT/x64/smda/StringObfuscatorCT_2019-12-11_gcc13_x64_snowapril_obfuscator.so.7z) |
| StringObfuscatorCT | 2019-12-11 | MinGW-w64 GCC 13 | [x86 PE](data/StringObfuscatorCT/x86/mcrit/StringObfuscatorCT_2019-12-11_mingw13_x86_snowapril_obfuscator.dll.mcrit) / [x64 PE](data/StringObfuscatorCT/x64/mcrit/StringObfuscatorCT_2019-12-11_mingw13_x64_snowapril_obfuscator.dll.mcrit) | [x86 PE](data/StringObfuscatorCT/x86/smda/StringObfuscatorCT_2019-12-11_mingw13_x86_snowapril_obfuscator.dll.7z) / [x64 PE](data/StringObfuscatorCT/x64/smda/StringObfuscatorCT_2019-12-11_mingw13_x64_snowapril_obfuscator.dll.7z) |
<!-- /generated -->

### StringObfuscator<a id='stringobfuscator'></a>

katursis/StringObfuscator templates on string length alone, so a binary using it carries one decrypt routine per distinct length rather than one per string - adding more strings of a length already present adds no new code. Built at `-O2`, which upstream requires and which this corpus confirmed the reason for: at `-O0` the obfuscation does not happen and the exerciser's literals were recoverable from the binary with `strings`, where at `-O1` and `-O2` none were. Its `decrypt()` survives `-O2` because it carries `__attribute__((noinline))`, guarded by `#ifdef __GNUC__` - which is why there is no MSVC build of it here.  

Generated with `scripts/build_corpus.py`; see `data/StringObfuscator/provenance.json` for source digests, compiler and flags.

<!-- generated: StringObfuscator -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| StringObfuscator | 2021-08-07 | GCC 13 (Linux, glibc) | [x86 ELF](data/StringObfuscator/x86/mcrit/StringObfuscator_2021-08-07_gcc13_x86_katursis_str_obfuscator.so.mcrit) / [x64 ELF](data/StringObfuscator/x64/mcrit/StringObfuscator_2021-08-07_gcc13_x64_katursis_str_obfuscator.so.mcrit) | [x86 ELF](data/StringObfuscator/x86/smda/StringObfuscator_2021-08-07_gcc13_x86_katursis_str_obfuscator.so.7z) / [x64 ELF](data/StringObfuscator/x64/smda/StringObfuscator_2021-08-07_gcc13_x64_katursis_str_obfuscator.so.7z) |
| StringObfuscator | 2021-08-07 | MinGW-w64 GCC 13 | [x86 PE](data/StringObfuscator/x86/mcrit/StringObfuscator_2021-08-07_mingw13_x86_katursis_str_obfuscator.dll.mcrit) / [x64 PE](data/StringObfuscator/x64/mcrit/StringObfuscator_2021-08-07_mingw13_x64_katursis_str_obfuscator.dll.mcrit) | [x86 PE](data/StringObfuscator/x86/smda/StringObfuscator_2021-08-07_mingw13_x86_katursis_str_obfuscator.dll.7z) / [x64 PE](data/StringObfuscator/x64/smda/StringObfuscator_2021-08-07_mingw13_x64_katursis_str_obfuscator.dll.7z) |
<!-- /generated -->

### obfstr<a id='obfstr'></a>

CasualX/obfstr is the Rust entry in this group, and the first Rust family this tooling generates rather than inherits. Its decoder, `obfstr::xref::inner`, is `#[inline(never)]` and generic over `const SEED: u64`, so it emits exactly one monomorphization per obfuscated item and each one is a different shape: the seed selects the arithmetic and drives a control-flow flattening pass around it. Unlike the C++ obfuscators above, it emits that same one-per-string shape in debug and in release alike, so the optimization level is not the provenance hazard here; release is what is recorded.  
The driver crate is `#![no_std]` with `panic = "abort"`, because a stock Rust `cdylib` would pull thousands of Rust std and core functions into the sample under this family's name - the same trap `-static-libstdc++` is for the C++ families. `OBFSTR_SEED` is left unset, which is upstream's own reproducible default.  

Generated with `scripts/build_corpus.py`; see `data/obfstr/provenance.json` for source digests, compiler and flags.

<!-- generated: obfstr -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| obfstr | 0.4.6 | GCC 13 (Linux, glibc) | [x86 ELF](data/obfstr/x86/mcrit/obfstr_0.4.6_gcc13_x86_obfstr_driver.so.mcrit) / [x64 ELF](data/obfstr/x64/mcrit/obfstr_0.4.6_gcc13_x64_obfstr_driver.so.mcrit) | [x86 ELF](data/obfstr/x86/smda/obfstr_0.4.6_gcc13_x86_obfstr_driver.so.7z) / [x64 ELF](data/obfstr/x64/smda/obfstr_0.4.6_gcc13_x64_obfstr_driver.so.7z) |
| obfstr | 0.4.6 | MinGW-w64 GCC 13 | [x86 PE](data/obfstr/x86/mcrit/obfstr_0.4.6_mingw13_x86_obfstr_driver.dll.mcrit) / [x64 PE](data/obfstr/x64/mcrit/obfstr_0.4.6_mingw13_x64_obfstr_driver.dll.mcrit) | [x86 PE](data/obfstr/x86/smda/obfstr_0.4.6_mingw13_x86_obfstr_driver.dll.7z) / [x64 PE](data/obfstr/x64/smda/obfstr_0.4.6_mingw13_x64_obfstr_driver.dll.7z) |
<!-- /generated -->

### obfstr<a id='obfstr'></a>

The Rust equivalent, and the only one of these four that keeps a function alive by design: `xref::inner` is `#[inline(never)]` and generic over a `const SEED: u64`, so it emits exactly one monomorphization per obfuscated string in both debug and release, each a different shape because the seed drives a per-string control-flow-flattening table. The seed derives from the file, line, column and the string itself, so identical strings at different call sites still emit distinct functions. Measured here, 46 strings gave 46 `obfstr::` functions on each architecture.  
This is the corpus's first generated Rust family. The driver crate is `#![no_std]` with `panic = "abort"` so that Rust's standard library does not enter the sample under obfstr's name; `OBFSTR_SEED` is left unset, which is what makes release builds byte-identical across rebuilds.  

Generated with `scripts/build_corpus.py`; see `data/obfstr/provenance.json` for source digests, compiler and flags.

<!-- generated: obfstr -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| obfstr | 0.4.6 | GCC 13 (Linux, glibc) | [x86 ELF](data/obfstr/x86/mcrit/obfstr_0.4.6_gcc13_x86_obfstr_driver.so.mcrit) / [x64 ELF](data/obfstr/x64/mcrit/obfstr_0.4.6_gcc13_x64_obfstr_driver.so.mcrit) | [x86 ELF](data/obfstr/x86/smda/obfstr_0.4.6_gcc13_x86_obfstr_driver.so.7z) / [x64 ELF](data/obfstr/x64/smda/obfstr_0.4.6_gcc13_x64_obfstr_driver.so.7z) |
| obfstr | 0.4.6 | MinGW-w64 GCC 13 | [x86 PE](data/obfstr/x86/mcrit/obfstr_0.4.6_mingw13_x86_obfstr_driver.dll.mcrit) / [x64 PE](data/obfstr/x64/mcrit/obfstr_0.4.6_mingw13_x64_obfstr_driver.dll.mcrit) | [x86 PE](data/obfstr/x86/smda/obfstr_0.4.6_mingw13_x86_obfstr_driver.dll.7z) / [x64 PE](data/obfstr/x64/smda/obfstr_0.4.6_mingw13_x64_obfstr_driver.dll.7z) |
<!-- /generated -->

### Obfuscator4g3nt47<a id='obfuscator4g3nt47'></a>

4g3nt47/Obfuscator is not a compile-time obfuscator at all, and is here for contrast as much as for coverage: it is a standalone command-line tool that opens an already-built binary, finds every string prefixed with the marker `[OBFS_ENC]`, XORs it with a rolling key and writes a new file. Nothing of it is ever linked into the program it protects. The only part that propagates downstream is a copy-pasted ten-line `obfs_decode()`, which the upstream README asks you to paste into your own source, so it appears in whatever shape your own compiler gives it rather than in the shape recorded here. What this family identifies is the tool binary itself.  
Seven functions is the whole project - `obfs_encode`, `obfs_decode`, `obfs_find_offset`, `obfs_filecpy`, `obfs_read_until_null`, `obfs_run` and `main` - so the recipe sets `min_functions=7` against the corpus-wide floor of eight, and the runtime residue it used to clear that floor on is now measured by a baseline probe instead. Built at `-O0`, not upstream's `-Os`: `obfs_decode` is byte-identical to `obfs_encode`, so identical-code folding reduces it to a one-instruction tail jump at `-Os` and `-O2`. Compiled directly rather than through upstream's Makefile, which hardcodes `-s` on the link line, never creates the `bin/` directory it writes objects to, and installs a `bin/main` that no rule builds.  

Generated with `scripts/build_corpus.py`; see `data/Obfuscator4g3nt47/provenance.json` for source digests, compiler and flags.

<!-- generated: Obfuscator4g3nt47 -->
| Name     | Version | Compiler | MCRIT | SMDA |
|----------|---------|----------|-------|------|
| Obfuscator4g3nt47 | 2023-02-26 | MinGW-w64 GCC 13 | [x86 PE](data/Obfuscator4g3nt47/x86/mcrit/Obfuscator4g3nt47_2023-02-26_mingw13_x86_obfuscator.exe.mcrit) / [x64 PE](data/Obfuscator4g3nt47/x64/mcrit/Obfuscator4g3nt47_2023-02-26_mingw13_x64_obfuscator.exe.mcrit) | [x86 PE](data/Obfuscator4g3nt47/x86/smda/Obfuscator4g3nt47_2023-02-26_mingw13_x86_obfuscator.exe.7z) / [x64 PE](data/Obfuscator4g3nt47/x64/smda/Obfuscator4g3nt47_2023-02-26_mingw13_x64_obfuscator.exe.7z) |
<!-- /generated -->
