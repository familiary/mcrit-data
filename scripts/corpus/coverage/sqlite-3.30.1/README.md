# SQLite 3.30.1 dependency coverage

[Tracker 60](https://github.com/r0ny123/mcrit-data/issues/60) identifies this
amalgamation as a reusable dependency. It is built separately in the existing
sqlite3 family; no consumer program, SQLite shell or operational extension is
compiled. The helper-tree references continue to exclude sqlite3.c.

The official archive SHA-256 is
adf051d4c10781ea5cfabbbc4a2577b6ceca68590d23b58b8260a8e24cc5f081.
Git mirror commit 25e9591209453dc0904f8f0f1c4d5090c836e19b has VERSION 3.30.1
and manifest.uuid 18db032d058f1436ce3dea84081f4ee5a0f2259ad97301d43c426bc7f3df1b0b,
matching SQLITE_SOURCE_ID. The official sqlite3.c and sqlite3.h are byte-identical
to the files at consumer commit 45c42c710fc3a9d7acdcd1f7acf966cc4ce07a49:
source SHA-256 e0a86381558c57a8e1a4a80fe94e842ad4ef1804a135452e253a4962c67229a6,
header SHA-256 5c4e58eef24c86bcce35d09017f48e3e7f71cf1fdcfcaf7932c4cf9f72131e1b.

This uses default features without FTS/RTREE/JSON1 defines. Existing later-version
rows use those feature defines, so their comparison changes profile and version
together. No causal version-only claim is made. Source is unmodified; retained
unnamed fragments and runtime residue are disclosed, not renamed or filtered
through a shared-tooling change. The real consumer program is not built.

## Completed local axes

| Image | Kept | Removed | Excluded | Image total | Distinct hashes >=10 instructions | Conservative named new hashes vs all prior SQLite images |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | 1278 | 4 | 0 | 1282 | 1077 | 1076 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | 1324 | 12 | 0 | 1336 | 1124 | 1035 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | 1321 | 53 | 0 | 1374 | 1100 | 520 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | 1314 | 58 | 0 | 1372 | 1128 | 514 |

The local subtotal is 5237 kept + 127 removed + 0 excluded = 5364 recovered
functions. MSVC x86/x64 are declared for the scoped CI build but not counted
as built in this snapshot. The recipe uses /MD /O2 /Zi /GL- /Brepro and
/OPT:NOREF /OPT:NOICF /Brepro /INCREMENTAL:NO, with no /LTCG.

The MinGW x86 unnamed 37/45-instruction bodies are not counted as novel named
implementations. Linux x86 has a 423-instruction unnamed body within the ELF
sqlite3Pragma symbol; both this body and its named owner are excluded from
novelty. Linux x86 retains four qualifying startup bodies, also excluded.
Full runtime/fragment names and exact hashes are in sqlite_3301.py.

## Between the new local axes

| Pair | Shared distinct hashes >=10 instructions |
| --- | ---: |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` / `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | 0 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | 1 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | 0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | 0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | 89 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | 0 |

## Comparisons with prior references

| New image | Earlier image | Earlier hashes | Shared | New outside earlier |
| --- | --- | ---: | ---: | ---: |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.31.1_mingw13_x64_sqlite3.dll` | 1462 | 1 | 1076 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.31.1_mingw13_x86_sqlite3.dll` | 1500 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.31.1_msvc143_x64_sqlite3.dll` | 2307 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.31.1_msvc143_x86_sqlite3.dll` | 2387 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.50.4_mingw13_x64_sqlite3.dll` | 1683 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.50.4_mingw13_x86_sqlite3.dll` | 1732 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.50.4_msvc143_x64_sqlite3.dll` | 2654 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.50.4_msvc143_x86_sqlite3.dll` | 2749 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll` | 1150 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` | `sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll` | 1171 | 0 | 1077 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.31.1_mingw13_x64_sqlite3.dll` | 1462 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.31.1_mingw13_x86_sqlite3.dll` | 1500 | 83 | 1041 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.31.1_msvc143_x64_sqlite3.dll` | 2307 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.31.1_msvc143_x86_sqlite3.dll` | 2387 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.50.4_mingw13_x64_sqlite3.dll` | 1683 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.50.4_mingw13_x86_sqlite3.dll` | 1732 | 34 | 1090 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.50.4_msvc143_x64_sqlite3.dll` | 2654 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.50.4_msvc143_x86_sqlite3.dll` | 2749 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll` | 1150 | 0 | 1124 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` | `sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll` | 1171 | 30 | 1094 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.31.1_mingw13_x64_sqlite3.dll` | 1462 | 576 | 524 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.31.1_mingw13_x86_sqlite3.dll` | 1500 | 0 | 1100 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.31.1_msvc143_x64_sqlite3.dll` | 2307 | 1 | 1099 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.31.1_msvc143_x86_sqlite3.dll` | 2387 | 0 | 1100 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.50.4_mingw13_x64_sqlite3.dll` | 1683 | 163 | 937 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.50.4_mingw13_x86_sqlite3.dll` | 1732 | 0 | 1100 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.50.4_msvc143_x64_sqlite3.dll` | 2654 | 1 | 1099 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.50.4_msvc143_x86_sqlite3.dll` | 2749 | 0 | 1100 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll` | 1150 | 122 | 978 |
| `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll` | 1171 | 0 | 1100 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.31.1_mingw13_x64_sqlite3.dll` | 1462 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.31.1_mingw13_x86_sqlite3.dll` | 1500 | 608 | 520 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.31.1_msvc143_x64_sqlite3.dll` | 2307 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.31.1_msvc143_x86_sqlite3.dll` | 2387 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.50.4_mingw13_x64_sqlite3.dll` | 1683 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.50.4_mingw13_x86_sqlite3.dll` | 1732 | 171 | 957 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.50.4_msvc143_x64_sqlite3.dll` | 2654 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.50.4_msvc143_x86_sqlite3.dll` | 2749 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.8.11.1_mingw13_x64_sqlite3.dll` | 1150 | 0 | 1128 |
| `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `sqlite3_3.8.11.1_mingw13_x86_sqlite3.dll` | 1171 | 131 | 997 |

## Shared new-axis hashes and names

Names explain matching hashes; matching names alone are not code evidence.

| Image pair | PicHash | Names in first image | Names in second image |
| --- | --- | --- | --- |
| `sqlite3_3.30.1_gcc14_x64_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x64_sqlite3.dll` | `0x7d1f0f4fd2f44550` | doubleToInt64 | doubleToInt64 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x005e5ffe07267f4d` | sqlite3VdbeAllocUnpackedRecord | _sqlite3VdbeAllocUnpackedRecord |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x03f25707a812e11e` | sqlite3BtreeCommit | _sqlite3BtreeCommit |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x05ff93b8148d515b` | btreeParseCellAdjustSizeForOverflow.isra.0 | _btreeParseCellAdjustSizeForOverflow.isra.0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x06cf0e7f12de7a5b` | valueToText | _valueToText |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x07f543374a460f63` | cellSizePtrNoPayload | _cellSizePtrNoPayload |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x08cc9d22c68c078e` | sqlite3_value_text16be | _sqlite3_value_text16be |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x0dbaeb06c0afbf38` | pcache1Shrink | _pcache1Shrink |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x131bf2030015f9e5` | vdbeSorterFlushThread | _vdbeSorterFlushThread |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x144c913bf499f8c0` | sqlite3_create_function_v2 | _sqlite3_create_function_v2 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x1a73e46222bc94b2` | selectPopWith | _selectPopWith |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x1d8b89b977b2ca4e` | nocaseCollatingFunc | _nocaseCollatingFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x2155c32d9c024041` | exprNodeIsDeterministic | _exprNodeIsDeterministic |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x26a47393a59838bf` | sqlite3CodeVerifySchema | _sqlite3CodeVerifySchema |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x26d13b5dd81b8dc0` | sqlite3BtreeSavepoint.part.0 | _sqlite3BtreeSavepoint.part.0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x2942f4d61fb8a09a` | vdbePmaReaderBgIncrInit | _vdbePmaReaderBgIncrInit |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x2c91cdeb367a754f` | sqlite3RenameTokenMap | _sqlite3RenameTokenMap |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x31f9a2300c75229d` | sqlite3ValueNew | _sqlite3ValueNew |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x38b0f5e96b52639b` | sqlite3_bind_text | _sqlite3_bind_text |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x3989dc1e5331eb4d` | renameColumnSelectCb | _renameColumnSelectCb |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x3b0728689d6c11e0` | btreeLeaveAll | _btreeLeaveAll |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x3c87b27ad13cf1cf` | sqlite3_prepare_v2 | _sqlite3_prepare_v2 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x43a7b23c83114aa3` | selectWindowRewriteSelectCb | _selectWindowRewriteSelectCb |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x4924ec422ba13c72` | pragmaVtabRowid | _pragmaVtabRowid |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x4b73c22cfe3027aa` | sqlite3_str_appendchar | _sqlite3_str_appendchar |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x4d4006cdcff37fd1` | sqlite3_column_bytes | _sqlite3_column_bytes |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x4e337447a41e0ac9` | sqlite3GetVarint32 | _sqlite3GetVarint32 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x6052fbea6b076852` | sqlite3_bind_blob | _sqlite3_bind_blob |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x610edaf5eb933a33` | sqlite3ReleaseTempReg.part.0 | _sqlite3ReleaseTempReg.part.0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x627e8d908b70ef2e` | sqlite3_prepare16_v3 | _sqlite3_prepare16_v3 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x631871fd0d7a1ac6` | sqlite3_str_value | _sqlite3_str_value |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x6a9c14d34016ac1c` | valueBytes | _valueBytes |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x6e234d977eab4de2` | computeYMD_HMS | _computeYMD_HMS |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x6ef28f56ccd0498b` | checkConstraintExprNode | _checkConstraintExprNode |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x707ea4685f38c906` | sqlite3_bind_text16 | _sqlite3_bind_text16 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x7164ba3939bf8eb9` | rowSetNDeepTree | _rowSetNDeepTree |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x75e68710e6ffb411` | sqlite3IndexAffinityOk | _sqlite3IndexAffinityOk |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x78708b4f4a1fc449` | sqlite3_blob_bytes | _sqlite3_blob_bytes |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x7b0366f853004163` | sqlite3_column_bytes16 | _sqlite3_column_bytes16 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x7c4ef5559f7a901f` | minMaxValue | _minMaxValue |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x7c919e522350dfb6` | sqlite3_value_blob | _sqlite3_value_blob |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x7dd36bbc134b7a8b` | rankStepFunc | _rankStepFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x82985a4349ebc90c` | sqlite3SchemaToIndex.part.0 | _sqlite3SchemaToIndex.part.0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x857fa618b6e61f87` | rowSetEntryMerge | _rowSetEntryMerge |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x86356af927bd8255` | sqlite3Atoi | _sqlite3Atoi |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x8705fa005eeeff99` | sqlite3_prepare_v3 | _sqlite3_prepare_v3 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x95c859ea4ca78598` | pcache1Fetch | _pcache1Fetch |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x9716e46b41891859` | sqlite3_strnicmp | _sqlite3_strnicmp |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x9805518da146e77c` | cume_distStepFunc, percent_rankStepFunc | _cume_distStepFunc, _percent_rankStepFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x9c3dec0338fae357` | whereScanInitIndexExpr.constprop.0 | _whereScanInitIndexExpr.constprop.0 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0x9e274726b1fc2d1e` | sqlite3BtreeUpdateMeta | _sqlite3BtreeUpdateMeta |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xa2ce2a504ed0cce1` | sqlite3GetVarint | _sqlite3GetVarint |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xa3314c52b6f0dd47` | sqlite3BinaryCompareCollSeq | _sqlite3BinaryCompareCollSeq |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xa61fc53d8584271d` | sqlite3ValueBytes | _sqlite3ValueBytes |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xa95b8a97eb81d0d6` | sqlite3UpsertNew | _sqlite3UpsertNew |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xab1653e6d9ae3e12` | pcache1Truncate | _pcache1Truncate |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xab295b4d71bbe203` | pcache1Rekey | _pcache1Rekey |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xac17bef97675e3fc` | btreeParseCellPtrIndex | _btreeParseCellPtrIndex |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xad0a2ae636ee0568` | sqlite3_db_readonly | _sqlite3_db_readonly |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb11d2487176c1840` | sqlite3_create_window_function | _sqlite3_create_window_function |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb29c0611d8c11a1b` | row_numberStepFunc | _row_numberStepFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb4d608cb4bdde2f3` | sqlite3_value_bytes16 | _sqlite3_value_bytes16 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb62ac6fb5cf141ca` | sqlite3BtreePayloadChecked | _sqlite3BtreePayloadChecked |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb6792a99aafb92af` | sqlite3_keyword_check | _sqlite3_keyword_check |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb7de238fd2bfdfa3` | last_valueValueFunc | _last_valueValueFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xb8a8cad88fa805df` | sqlite3_prepare16_v2 | _sqlite3_prepare16_v2 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xbaa4b67d6ff1492e` | sqlite3_value_text | _sqlite3_value_text |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xbfa6033dd494f84c` | walRestartHdr | _walRestartHdr |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xc2c59acc4de8c3da` | sqlite3_value_text16, sqlite3_value_text16le | _sqlite3_value_text16, _sqlite3_value_text16le |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xc8594d1e4ac59073` | walHashGet | _walHashGet |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xc86176471f25ee07` | sqlite3_column_value | _sqlite3_column_value |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xc9d19994ca20a805` | renameUnmapExprCb | _renameUnmapExprCb |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xca49b6bc529a9e28` | sqlite3_value_bytes | _sqlite3_value_bytes |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xcadc809be12ebe75` | btreeHeapInsert | _btreeHeapInsert |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xd23563c5e85cacb6` | vdbeMemAddTerminator | _vdbeMemAddTerminator |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xd2a7a1aa61c01e77` | cume_distInvFunc, percent_rankInvFunc | _cume_distInvFunc, _percent_rankInvFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xd3e2d5eb1cfa18e8` | insertElement | _insertElement |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xd4e01f5b0f4604ac` | vdbeIncrPopulateThread | _vdbeIncrPopulateThread |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xdcd8a12fbdc437ef` | sqlite3_value_double | _sqlite3_value_double |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xe6ce1cab99acfcc7` | sqlite3_prepare | _sqlite3_prepare |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xe917c5392c5873e4` | sqlite3_stmt_busy | _sqlite3_stmt_busy |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xeab689132ffa5b03` | dense_rankStepFunc | _dense_rankStepFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xebe15e0824b995b4` | sqlite3BeginWriteOperation | _sqlite3BeginWriteOperation |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xf4f122b1babf3b61` | ntileInvFunc | _ntileInvFunc |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xf512c21be2f5182c` | sqlite3_prepare16 | _sqlite3_prepare16 |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xf68f9162070bee91` | btreePageLookup | _btreePageLookup |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xfa289c9986c73ff1` | resolveRemoveWindowsCb | _resolveRemoveWindowsCb |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xfc9933263b1aaf61` | pcache1Cachesize | _pcache1Cachesize |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xfcb7ea73b958592e` | exprIdxCover | _exprIdxCover |
| `sqlite3_3.30.1_gcc14_x86_libsqlite3.so` / `sqlite3_3.30.1_mingw13_x86_sqlite3.dll` | `0xffd94251266b3224` | sqlite3WhereSplit | _sqlite3WhereSplit |
