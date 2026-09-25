/* How an exerciser's entry point is made visible, on either container.
 *
 * Every exerciser here is compiled into a shared library so SMDA has
 * something to read - a DLL on Windows, a .so on Linux - and its entry point
 * has to survive into the export table without a .def file or a version
 * script. The two toolchains spell that differently and only one of the two
 * spellings exists per platform: __declspec(dllexport) is MSVC/MinGW syntax
 * and the native GCC rejects it, while __attribute__((visibility("default")))
 * is meaningless to cl.
 *
 * One header rather than the same four lines in each exerciser, and one
 * header rather than one exerciser per platform, because the whole point of
 * these files is that the Windows and the Linux reference data for a family
 * come from the *same* translation unit: two copies that drift apart would
 * make a difference in the reports impossible to attribute to the platform.
 *
 * It is included with a quoted path and no -I, so it resolves next to the
 * exerciser that includes it under both cl and gcc. The MinGW artefacts
 * built through it are unchanged: CORPUS_EXPORT expands to exactly the
 * __declspec(dllexport) that was written out by hand before, and a rebuild of
 * Obfuscate 2026-06-03 mingw13_x64 through this header came back with the
 * same 231 functions its provenance record names.
 *
 * _WIN32 is the right test rather than _MSC_VER: mingw-w64's GCC defines it,
 * targets a PE, and needs the dllexport spelling despite being GCC.
 *
 * INCLUDE IT WITHOUT MOVING ANY LINE OF THE FILE THAT INCLUDES IT. This is
 * not a style rule. adamyaxley/Obfuscate templates obfuscated_data on
 * <N, KEY, CHAR_TYPE> with KEY defaulting to ay::generate_key(__LINE__), so
 * every AY_OBFUSCATE in ay_obfuscate.cpp is keyed on its own source line:
 * adding this include above them on its own line, with a blank line after
 * it, moved 35 call sites down by two and changed every key, every mangled
 * name and every function body in an artefact that had been committed. The
 * function count was identical - 231 on x64, 225 on x86, exactly as the
 * provenance record says - so nothing failed and nothing in the pipeline
 * noticed; it was caught by comparing the recovered symbol names of a
 * rebuild against the committed report. That exerciser therefore includes
 * this header on the line that used to be blank. Anything keyed on
 * __LINE__, __COUNTER__ or a file offset deserves the same care.
 */

#ifndef CORPUS_EXPORT_H
#define CORPUS_EXPORT_H

#if defined(_WIN32)
#define CORPUS_EXPORT __declspec(dllexport)
#else
#define CORPUS_EXPORT __attribute__((visibility("default")))
#endif

#endif /* CORPUS_EXPORT_H */
