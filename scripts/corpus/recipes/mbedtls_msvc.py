"""mbedTLS built with MSVC, beside the MinGW build of the same tag.

data/mbedTLS carries only MinGW artefacts. mbedTLS is one of the two crypto
stacks that actually turn up inside Windows ransomware and commodity loaders
- the other being OpenSSL - and those binaries are MSVC-built, so this is the
compiler the family should have had first.

A separate registry entry rather than another toolchain on the MinGW recipe,
for the reason spelled out in sqlite3_msvc.py: one Recipe has one build list
and these steps are cmd.exe, not sh.

Only 3.6.7 is covered, of the four versions the MinGW side carries.

  * 3.6.7 is the current LTS and what anything built today links.
  * 2.28.10 is the other line worth having, and it is deliberately left for
    later rather than dropped on judgement: its CMakeLists.txt declares
    cmake_minimum_required(VERSION 2.8.12), which CMake 4 refuses outright
    unless CMAKE_POLICY_VERSION_MINIMUM is passed. That is a cache variable
    and so would be legitimate here, but it makes the build's success depend
    on which CMake the runner image happens to carry - the same reason
    lz4_msvc.py holds back lz4 1.9.4. 3.6.7 declares 3.5.1 and has no such
    dependency.
  * 2.16.12 is 2019 code and the survey's own risk list names it as one of
    the versions v143 may simply reject; 3.0.0 is a short-lived release
    between the two LTS lines and is the least likely of the four to be met
    in the wild.

What was read rather than assumed, in CMakeLists.txt and library/CMakeLists
.txt at mbedtls-3.6.7:

  * USE_SHARED_MBEDTLS_LIBRARY and USE_STATIC_MBEDTLS_LIBRARY are upstream's
    own options and select "add_library(... SHARED ...)" or "... STATIC ..."
    for all three libraries. Exactly one of the two must be on or the
    configure stops with a FATAL_ERROR. This recipe uses the static one, for
    the reason worked through under "Why this recipe links its own DLL"
    below.
  * MBEDTLS_FATAL_WARNINGS defaults ON and, in its MSVC branch, appends /WX
    to a CMAKE_C_FLAGS that the MSVC branch above it has already set to
    "/W3 /utf-8". The MinGW recipe turns the option off too, but for a
    different failure (-Werror=format= on a time_t), so the reason is
    re-derived here rather than copied: under v143 it is /WX at /W3 over a
    2024 code base, which is a coin flip this build does not need to take.
  * the generated sources - error.c, version_features.c,
    ssl_debug_helpers_generated.c, psa_crypto_driver_wrappers.h - are
    committed in the pinned tree, and GEN_FILES defaults OFF on Windows
    hosts as well as elsewhere, so neither Perl nor the Python jinja
    generators are needed. That is unchanged by the static configuration:
    a full static build run locally with GEN_FILES at its default invoked
    neither. Python is looked for but only to print a configuration
    warning, and is not REQUIRED. The framework submodule is still needed
    at configure time - CMakeLists.txt:318 FATAL_ERRORs without it and
    add_subdirectory(framework) is unconditional - but framework/CMake
    Lists.txt is a one-line comment and contributes no build targets.
  * link_to_source, the one place upstream makes a symlink, is called only
    from the tests branch and copies rather than links on a non-Unix host
    anyway. ENABLE_TESTING is off here and already defaults off for MSVC
    upstream, because "the test suites currently have compile errors with
    MSVC".
  * the MSVC branch of the compiler-flag block touches CMAKE_C_FLAGS only,
    not CMAKE_C_FLAGS_RELEASE, so the per-configuration override below is
    not fighting upstream for the same variable. The only other MSVC branch
    in the tree is library/CMakeLists.txt:213, which rewrites /MD to /MT
    across the flag variables - but only if MSVC_STATIC_RUNTIME is on, and
    it defaults OFF. Nothing anywhere appends /Zi.

Why the three-DLL shape the MinGW recipe uses is impossible here:

The first attempt at this recipe configured with USE_SHARED_MBEDTLS_LIBRARY
=ON and CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON - mbedTLS has no export
machinery of its own, so without that variable mbedcrypto.dll would export
nothing and produce no import library. It got mbedcrypto.dll and
mbedx509.dll, then LNK1120 on the third library with four unresolved
externals. Looking up where each one is defined settles it: not one of the
four is a function. All four are *data* objects, each defined in a different
DLL from the translation unit that reads it.

  * library/constant_time.c:29

        volatile mbedtls_ct_uint_t mbedtls_ct_zero = 0;

    declared "extern volatile mbedtls_ct_uint_t mbedtls_ct_zero;" at
    library/constant_time_impl.h:69 and read at :91 by the static inline
    mbedtls_ct_compiler_opaque(), which every constant-time helper used in
    ssl_msg.c and ssl_tls12_server.c goes through. constant_time.c is in
    src_crypto, so the object lives in mbedcrypto. Both the definition and
    the use sit under "#if !defined(MBEDTLS_CT_ASM)", and
    constant_time_impl.h only defines MBEDTLS_CT_ASM for
    "MBEDTLS_HAVE_ASM && __GNUC__" - which is why this symbol does not
    exist at all in a GCC build and the MinGW recipe never meets it. A
    local GCC build of the same tag confirms it: nm over libmbedcrypto.a
    finds mbedtls_x509_crt_profile_default, _suiteb and psa_to_ssl_errors
    and no mbedtls_ct_zero.
  * library/psa_util.c:84

        const mbedtls_error_pair_t psa_to_ssl_errors[] = ...

    declared "extern const mbedtls_error_pair_t psa_to_ssl_errors[7];" at
    library/psa_util_internal.h:64 under "#if defined(MBEDTLS_USE_PSA_CRYPTO)
    || defined(MBEDTLS_SSL_PROTO_TLS1_3)", which the default
    mbedtls_config.h reaches by way of TLS 1.3. psa_util.c is src_crypto;
    ssl_tls13_keys.c:31, ssl_tls13_client.c:29 and ssl_tls13_generic.c:34
    are src_tls.
  * library/x509_crt.c:89 and :142

        const mbedtls_x509_crt_profile mbedtls_x509_crt_profile_default =
        const mbedtls_x509_crt_profile mbedtls_x509_crt_profile_suiteb =

    both unguarded, and declared - as plain "extern", no annotation - in
    the *public* header include/mbedtls/x509_crt.h:324 and :336. ssl_tls.c
    takes their addresses at :6102 and :6128. x509_crt.c is src_x509.

CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS does export them. CMake's bindexplib sorts
each COFF symbol into functions and data and writes the data ones into the
generated .def tagged DATA, so mbedcrypto.dll really does export
mbedtls_ct_zero. What a DATA export puts in the import library, though, is
only __imp_<name> - the pointer to the object - and no thunk. A translation
unit that was not compiled with __declspec(dllimport) emits a reference to
the bare name, and nothing supplies it. CMake documents precisely this
limitation of the feature: "For global data symbols, __declspec(dllimport)
must still be used when compiling against the code in the DLL. All other
function symbols will be automatically exported and imported by callers."
mbedTLS supplies no dllimport - grepping the 3.6.7 tree for dllimport or
dllexport returns no hit in any file - so the four references stay bare and
the link fails. The function symbols in the same cross-DLL position resolve
through their thunks, which is why mbedx509.dll links against mbedcrypto.dll
without a murmur and why exactly these four names, and no others, come back.

GNU ld covers the same gap with auto-import pseudo-relocations, patching the
data references at load time; that is the only reason the MinGW recipe's
libmbedtls.dll links. MSVC has no such mechanism and no cache variable can
invent one.

This is upstream's position and not a consequence of the flags chosen here.
Mbed-TLS/mbedtls#470, "Annotate visibility/exportability of functions
(support shared DLL build in Windows)", has been open since 2016, and #1130,
on USE_SHARED_MBEDTLS_LIBRARY failing under CMake/MSVC, since 2017.
Upstream's own MSVC build is not CMake at all but visualc/VS2017/
mbedTLS.vcxproj, which is <ConfigurationType>StaticLibrary</ConfigurationType>
over all 142 library .c files - crypto, x509 and tls in a single archive, no
DLL anywhere. So: upstream's CMake does not support a shared MSVC build of
the protocol library, and 3.6.7 is not a tag that happens to be broken - no
3.6.x tag links this, because the annotations the link needs have never been
written.

Why this recipe links its own DLL:

The way out is the one cryptopp_msvc.py already uses for a project that
ships only a static library: build the archives, then link the *whole*
archive into a DLL of this recipe's own making. Every one of those four
references then becomes an intra-image reference and resolves trivially,
because there is no DLL boundary left to cross - and the TLS layer, which
is the part a two-DLL fallback would have thrown away, stays in the corpus.
It is also the shape upstream itself supports.

What was checked against the pinned tree before writing the link line, some
of it by configuring and building the static tree locally under GCC, which
exercises the same CMakeLists paths:

  * the archives. library/CMakeLists.txt:285-303 adds the three STATIC
    targets and gives each an explicit OUTPUT_NAME - mbedcrypto, mbedx509,
    mbedtls. There is no DEBUG_POSTFIX or ARCHIVE_OUTPUT_DIRECTORY anywhere
    in the tree; grepping for POSTFIX/OUTPUT_NAME/ARCHIVE_OUTPUT finds only
    those three OUTPUT_NAME lines. With a single-configuration generator
    each lands beside its CMakeLists, so build-<arch>/library/*.lib, and
    MSVC's empty static-library prefix makes the names exactly
    mbedcrypto.lib, mbedx509.lib, mbedtls.lib.
  * everest and p256m. 3rdparty/CMakeLists.txt add_subdirectory()s both
    unconditionally from the root, and each calls add_library() with no
    STATIC/SHARED keyword, so they follow BUILD_SHARED_LIBS - off - and are
    static whichever way USE_STATIC/USE_SHARED is set. Their files are
    build-<arch>/3rdparty/everest/everest.lib and
    build-<arch>/3rdparty/p256-m/p256m.lib; the failing shared link's own
    command line named exactly those two paths, so this is read off a real
    build rather than inferred. They are named on the link line as ordinary
    archives, not whole-archived: nm over both of them after a local build
    finds *zero* defined global symbols, because everest.c is wrapped in
    "#if defined(MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED)" and p256-m behind
    its driver switch, neither of which the default mbedtls_config.h turns
    on. Whole-archiving two empty archives would add nothing; listing them
    ordinarily costs nothing and cannot fail.
  * duplicate symbols, which is the failure mode of /WHOLEARCHIVE (LNK2005).
    The three source lists in library/CMakeLists.txt:13-128 are disjoint -
    src_crypto has no x509 or ssl file, src_x509 is pkcs7/x509*, src_tls is
    debug/mps/net_sockets/ssl*. That was then checked rather than trusted:
    nm --defined-only -g over all five archives from a local static build
    gives 875 global definitions in mbedcrypto, 106 in mbedx509, 300 in
    mbedtls, 0 in everest and 0 in p256m, and **no symbol is defined in more
    than one of them**. CMake does not merge a static dependency's objects
    into its dependant's archive, so nothing is duplicated that way either.
    The same run shows 83 of libmbedtls.a's undefined symbols resolved by
    mbedcrypto and 11 by mbedx509 - the 94 references, four of them data,
    that this link turns into intra-image ones.
  * the whole-archive link itself, which was then done rather than reasoned
    about. Whole-archiving pulls in objects nothing references, so an object
    can arrive carrying an external that was never needed before; the way to
    find out is to try it. Linking all three archives under
    --whole-archive against a one-function anchor, GNU ld's spelling of the
    same operation, succeeds with no unresolved symbol and no duplicate
    definition and yields an image with 1266 text symbols. (It has to be
    linked as an executable to answer the question: as a shared object it
    fails on "relocation R_X86_64_PC32 against symbol
    mbedtls_x509_crt_profile_suiteb ... recompile with -fPIC", which is an
    ELF requirement that static archives are not built for and that PE/COFF
    does not have. The symbol it names is worth noticing anyway - it is one
    of the four.) What is left outside the image after that is the Win32
    import libraries and the CRT, which the line below names in full.
  * the Win32 import libraries. library/CMakeLists.txt:226 adds "ws2_32
    bcrypt" for WIN32; net_sockets.c:50 and x509_crt.c:2695 also carry
    "#pragma comment(lib, \\"ws2_32.lib\\")", so ws2_32 would arrive through
    the objects anyway, but bcrypt does not - entropy_poll.c:42 includes
    <bcrypt.h> and calls BCryptGenRandom at :60 with no pragma. link.exe
    adds no default libraries of its own beyond what the objects' directives
    name, so the rest have to be spelled out. What is spelled out is
    CMAKE_C_STANDARD_LIBRARIES plus those two - which is precisely the set
    CMake put on the link line that did produce mbedcrypto.dll and
    mbedx509.dll, so it cannot be short. An import library nothing
    references contributes nothing to the image.
  * /Z7 rather than /Zi, the point cryptopp_msvc.py turns on: /Z7 puts the
    debug info in the .obj files themselves, which is what survives being
    packed into a .lib by one step and unpacked by a separate link. With
    /Zi the objects would instead carry a path to a compiler PDB that the
    wrapper link has to find. Nothing upstream fights it - see the flag note
    above - and because CMP0091 is OLD here the compiler flags are whatever
    CMAKE_C_FLAGS_RELEASE says and nothing else, which is the same path that
    already carried /MD into the artefacts that built.
  * /GL, the other thing cryptopp_msvc.py has to turn off, is not an issue:
    nothing in mbedTLS's CMake enables whole-program optimisation, and
    CMAKE_INTERPROCEDURAL_OPTIMIZATION is left at its default off, so the
    archives hold machine code rather than IL and the wrapper link is not
    silently an LTCG link.
  * CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS is now irrelevant and is dropped: it
    only ever applies to SHARED and MODULE targets, and there are none left.
    The DLL this recipe links exports nothing at all, which is fine and is
    the same position cryptopp_msvc.py is in - nothing needs an import
    library, and the PDB rather than the export table is what names
    functions for SMDA.
  * with ENABLE_PROGRAMS=OFF and ENABLE_TESTING=OFF the default target is
    just the five archives - include/ and pkgconfig/ only register install
    rules and configure_file()s, and apidoc is an ADD_CUSTOM_TARGET without
    ALL - so a plain "cmake --build build-<arch>" is enough and nothing
    needs naming.

What was weighed and rejected:

  * dropping mbedtls.dll and shipping only the two libraries that do link
    shared. It works and is a one-line change, but it throws away the whole
    of src_tls - both TLS state machines, the record layer, the ciphersuite
    tables, session tickets and cache - from the MSVC side, which is a
    large part of why the family is in the corpus. The whole-archive DLL
    keeps it.
  * /FORCE:UNRESOLVED on the shared link. It would hand back an mbedtls.dll,
    and a broken one: those four references would be linked against nothing
    and the library would fault on its first certificate verification. A
    corpus of reference binaries cannot carry an image that does not work.
  * USE_STATIC_MBEDTLS_LIBRARY=ON with ENABLE_PROGRAMS=ON, letting the
    programs be the artefacts. It does put the protocol code into PEs, but
    it replaces the artefact set with some fifty executables that each
    duplicate whatever crypto they touch, and it newly compiles programs/
    and the mbedtls_test object library (tests/src/*.c plus
    framework/tests/src/*.c, built whenever ENABLE_PROGRAMS is on) under
    v143 - untried code next to an upstream comment that the test suites
    "currently have compile errors with MSVC". ENABLE_PROGRAMS stays off.
  * three DLLs, each whole-archiving what it depends on - mbedx509.dll
    whole-archiving mbedcrypto.lib and mbedtls.dll whole-archiving both.
    That would link, and it would put every one of mbedcrypto's 875
    functions into all three artefacts. Three copies of one body is exactly
    what this corpus must not contain: PicHash would report a family
    matching itself.
"""

from ..recipe import Artifact, BuildStep, Recipe, Source


# See xz_msvc.py for why the per-configuration variable and not
# CMAKE_C_FLAGS: CMake's MSVC Release default carries no debug-info flag at
# all, so the objects would come back with nothing for a PDB to be built
# from, and overriding the per-configuration variable leaves CMake's own
# initialisation - /machine on the 32-bit leg among it - in place.
#
# /Z7, not /Zi, because these objects are archived by one step and linked by
# another; see the docstring.
#
# /MD is spelled out rather than left to CMAKE_MSVC_RUNTIME_LIBRARY.
# mbedTLS declares cmake_minimum_required(VERSION 3.5.1), so CMP0091 is OLD
# and the runtime flag is whatever CMAKE_C_FLAGS_<CONFIG> says - which means
# replacing that variable without /MD in it would silently hand the build
# cl's default /MT and file the static MSVC C runtime under the mbedTLS name.
_CFLAGS = '-DCMAKE_C_FLAGS_RELEASE="/MD /O2 /Ob2 /DNDEBUG /Z7"'

# NMake Makefiles: nmake ships with MSVC itself, the generator is
# single-configuration so CMAKE_BUILD_TYPE means what it says and the
# archives land beside their CMakeLists rather than under a Release/
# subdirectory, and the target architecture comes from the developer
# environment the workflow sets up.
#
# No CMAKE_SHARED_LINKER_FLAGS_RELEASE and no CMAKE_WINDOWS_EXPORT_ALL_
# SYMBOLS: nothing here is a shared library, so neither variable is reached.
# The link this recipe cares about is the explicit one below.
_CMAKE = ('cmake -S . -B build-{arch} -G "NMake Makefiles" '
          '-DCMAKE_BUILD_TYPE=Release '
          '-DUSE_STATIC_MBEDTLS_LIBRARY=ON -DUSE_SHARED_MBEDTLS_LIBRARY=OFF '
          '-DENABLE_TESTING=OFF -DENABLE_PROGRAMS=OFF '
          '-DMBEDTLS_FATAL_WARNINGS=OFF %s' % _CFLAGS)

# The anchor translation unit, written from a step so that nothing outside
# the fetched tree is part of the build - the mechanism cryptopp_msvc.py
# uses. link needs at least one object of its own; /WHOLEARCHIVE supplies
# the rest. Upstream source is untouched. No % anywhere: cmd.exe would try
# to expand it.
_ANCHOR_SRC = ('python -c "'
               "open('anchor.c','w').write("
               "'int mbedtls_msvc_anchor(void){return 0;}')"
               '"')

# /MD here too, or this single object would drag the static CRT in, and /Z7
# to match the archives so the one object is not the only thing missing from
# the PDB.
_ANCHOR = "cl /nologo /c /O2 /MD /Z7 /Foanchor.obj anchor.c"

_WHOLE = " ".join(
    "/WHOLEARCHIVE:build-{arch}\\library\\%s.lib" % name
    for name in ("mbedcrypto", "mbedx509", "mbedtls"))

# The two in-tree third-party archives, as ordinary libraries: a local build
# shows both define no global symbols under the default configuration, so
# whole-archiving them would import nothing, while naming them costs nothing
# if a future configuration does reach them.
_3RDPARTY = ("build-{arch}\\3rdparty\\everest\\everest.lib "
             "build-{arch}\\3rdparty\\p256-m\\p256m.lib")

# CMAKE_C_STANDARD_LIBRARIES plus upstream's own ws2_32 and bcrypt, which is
# exactly the set CMake put on the link line that produced mbedcrypto.dll
# and mbedx509.dll. link.exe adds no default libraries beyond what the
# objects' own directives name, and an import library nothing references
# contributes nothing to the image, so this is stated in full rather than
# pared down to what a reading of the sources says is reachable.
_SYSLIBS = ("ws2_32.lib bcrypt.lib kernel32.lib user32.lib gdi32.lib "
            "winspool.lib shell32.lib ole32.lib oleaut32.lib uuid.lib "
            "comdlg32.lib advapi32.lib")

# One DLL, not the three .lib files nmake just produced: SMDA cannot read a
# static library, and three DLLs cannot be linked at all (see the docstring).
# /WHOLEARCHIVE forces every object in, including the ones nothing
# references, which is the whole point.
#
# /DEBUG so a PDB is written from the /Z7 info the objects carry, /Brepro so
# the PE carries no build timestamp and two runs of identical source record
# the same sha256, /OPT:NOREF so unreferenced routines survive and /OPT:NOICF
# so two routines that compiled to identical bodies stay apart - a crypto
# library is full of near-twin bodies. /INCREMENTAL:NO because /DEBUG
# otherwise implies incremental linking, and an incremental image reaches
# its functions through a jump table that would be disassembled as part of
# this family; the /OPT:NO* forms are not documented to suppress it the way
# /OPT:REF is, so it is said outright.
_LINK = ('link /nologo /DLL /DEBUG /Brepro /INCREMENTAL:NO '
         '/OPT:NOREF /OPT:NOICF %s '
         '/PDB:mbedtls_all.pdb /OUT:mbedtls_all.dll anchor.obj %s %s'
         % (_WHOLE, _3RDPARTY, _SYSLIBS))


RECIPES = {
    "mbedTLS_3.6.7_msvc": Recipe(
        family="mbedTLS",
        version="3.6.7",
        upstream="https://github.com/Mbed-TLS/mbedtls",
        license="Apache-2.0",
        # The fetch stage initialises submodules; mbedTLS >= 3.6 needs the
        # framework submodule at configure time even with testing disabled.
        source=Source(git_url="https://github.com/Mbed-TLS/mbedtls.git",
                      git_ref="mbedtls-3.6.7"),
        build=[
            BuildStep(_CMAKE),
            BuildStep("cmake --build build-{arch}"),
            BuildStep(_ANCHOR_SRC),
            BuildStep(_ANCHOR),
            BuildStep(_LINK),
            # Cheap insurance, as in xz_msvc.py: puts the names the build
            # actually wrote into the log the workflow prints on failure.
            BuildStep("dir build-{arch}\\library", allow_failure=True),
        ],
        # One artefact, deliberately not called mbedtls.dll: under MinGW
        # that name means the protocol layer alone, and this image is all
        # three libraries at once.
        artifacts=[Artifact(path="mbedtls_all.dll",
                            component="mbedtls_all.dll",
                            pdb="mbedtls_all.pdb")],
        toolchains=["msvc_x86", "msvc_x64"],
        # Not the same string as the MinGW recipe, and deliberately not:
        # that one records -O2 because upstream's GNU-compiler branch
        # overwrites CMAKE_C_FLAGS_RELEASE with "-O2". The MSVC branch sets
        # no per-configuration flags at all, so what governs this build is
        # the value passed on the command line.
        build_flags="/MD /O2 /Ob2 /Z7 (CMake Release, with /Z7 in place of "
                    "a PDB-writing /Zi so the debug info rides in the .obj "
                    "files and survives being archived and re-linked) plus "
                    "the /W3 /utf-8 upstream appends for MSVC, /WX "
                    "suppressed with MBEDTLS_FATAL_WARNINGS=OFF; the three "
                    "static archives then linked whole into one DLL with "
                    "/DEBUG /Brepro /INCREMENTAL:NO /OPT:NOREF /OPT:NOICF. "
                    "No interprocedural optimization: mbedTLS enables none "
                    "and the wrapper link would otherwise be an LTCG link "
                    "that undoes /WHOLEARCHIVE.",
        notes="One artefact where the MinGW side has three, and that is the "
              "trade this recipe makes knowingly. mbedtls_all.dll is "
              "mbedcrypto, mbedx509 and mbedtls - primitives, certificate "
              "handling and the TLS/DTLS protocol - linked whole into a "
              "single image, so the component separation the MinGW "
              "artefacts carry is lost while the code coverage is complete. "
              "The three-DLL shape is not available under MSVC at any "
              "setting: the protocol library reads four data objects "
              "defined in the other two (mbedtls_ct_zero and "
              "psa_to_ssl_errors from mbedcrypto, "
              "mbedtls_x509_crt_profile_default and _suiteb from mbedx509) "
              "and mbedTLS annotates nothing with __declspec(dllimport), "
              "which MSVC requires for a cross-DLL data reference and MinGW "
              "does not need because ld auto-imports. Upstream has had that "
              "open as issue #470 since 2016 and ships a static-library "
              "Visual Studio project rather than a DLL one, so this recipe "
              "builds the shape upstream supports and wraps it. Matching "
              "against the MinGW artefacts therefore compares one image "
              "here with three there; the function bodies are what the "
              "corpus matches on and no body appears twice, because the "
              "three archives share no symbol. The DLL exports nothing - "
              "nothing needs an import library and the PDB, not the export "
              "table, is what names functions for SMDA. No external "
              "dependencies: it links ws2_32 and bcrypt from Win32 and is "
              "built against the DLL runtime, so the MSVC C runtime is "
              "imported rather than linked in and stays attributed to "
              "data/MSVC. Two in-tree third-party libraries, Everest "
              "(HACL* Curve25519) and p256-m, are compiled by upstream's "
              "CMake, but their translation units are guarded by "
              "MBEDTLS_ECDH_VARIANT_EVEREST_ENABLED and the p256-m driver "
              "switch, neither of which the default mbedtls_config.h turns "
              "on - nm over both archives finds no defined global symbol at "
              "all - so no code from either reaches this artefact. mbedTLS "
              "and wolfSSL implement the same primitives and both appear in "
              "this corpus - a cross-family PicHash hit between them is two "
              "independent implementations of one algorithm, not code "
              "leaking from one family into the other.",
    ),
}
