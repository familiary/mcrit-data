# Ingesting sample-derived reference data

A proposal, not an implementation. Nothing in `scripts/corpus/` reads this yet.

Every family in `data/` today was compiled here from pinned source. That is
what makes the corpus's central claim cheap: when a report says a body is
`inflate` from libzlib 1.3, it is, because we fetched 1.3 and built it. The
family label is true by construction and nobody has to be trusted.

Some families cannot be reached that way. Issue #15 is the case that forced
this: a family whose code only exists as shipped binaries, where there is no
source to pin and no build to run. The question is what it would take to file
such a thing here without weakening what the rest of the corpus means.

The answer is not a flag on `Recipe`. It is a second track with its own
provenance shape, its own admission rules, and a marker that follows the data
into every report it produces.


## What breaks if you reuse `Recipe`

`Recipe` and `provenance.json` assume a build at every level. From
`pipeline.py`, the fields each entry carries and what happens to them:

| field | build-derived | sample-derived |
| --- | --- | --- |
| `source` | git commit or tarball sha256 | nothing to pin |
| `built_artifact` | path in the source tree | no source tree |
| `compiler` | banner from `toolchain.version()` | unknown, and guessing is worse than blank |
| `build_flags` | recorded from the recipe | unknowable |
| `toolchain` | the id that built it | never ran |
| `sha256` | of a binary we produced | of a binary someone acquired — now the primary key |

Four of six become empty or false. `Artifact.is_blob` already carries a
precedent worth reading: it sets `toolchain: None` and
`compiler: "MSVC (upstream, exact version unknown)"`, and `Recipe.slug`
hardcodes the producer to `msvc` rather than naming the toolchain that merely
ran the extraction — "a lie baked into the filename" is the comment. Blobs are
the closest thing the corpus has to this track, and they stop short of it: the
bytes are still committed upstream in a repository we clone at a pinned ref.


## The three problems that actually decide this

### 1. Attribution stops being free

Build-derived: we compiled it, so we know what it is.

Sample-derived: the family label is a *claim* about a binary. If the claim is
wrong, MCRIT does not degrade gracefully — it confidently names the wrong
family, forever, in every future investigation that hits those bodies. That is
the exact failure this corpus exists to prevent, so the claim has to carry its
evidence as a field, not as a sentence in `notes`.

Minimum: who attributes it, in what published analysis, and what the
attribution rests on. A vendor blog naming a hash is evidence. "It was in a
folder called blacklotus" is not.

### 2. Contamination, and why the corpus can already solve it

A malware sample is mostly not the malware. Statically linked CRT, vendored
libraries, compiler glue. `baseline.py` (2,904 lines) and `drop_crt_glue`
exist to subtract exactly that for builds, and they work because the toolchain
is known. For a sample it is not, so none of that machinery applies directly.

Left unsolved this is fatal, and the repo has refused data over it twice
already: monomorph dropped upstream's `-static` because a static link put
1,393 glibc and zlib bodies under monomorph's name, and VX-API's static CRT
put 1,947 Microsoft functions into one family.

But the corpus is now the instrument that fixes it. `data/MSVC`, `data/MinGW`,
`data/Rust`, `data/Golang`, `data/libstdc++` and ~60 library families are
already here. So the subtraction runs the other way round: **match the sample
against the corpus first, and admit only the residue.** Every body that hits a
known family is by definition not this family's; what survives is the
candidate. This is the one part of the design that is stronger here than it
would be in a greenfield tool, and it should be mandatory rather than
optional — an ingestion that cannot account for most of an image has not
established anything.

The residue still needs a floor and a human look. A body that matches nothing
is not thereby the malware's; it may be a library the corpus lacks.

### 3. Redistribution is a maintainer question, not a technical one

An SMDA report is a near-complete reconstruction of the code. For the families
here that is fine — they are MIT, BSD, Apache. For a sample there is usually
no licence at all, and for leaked or criminal code there is certainly none.
Whether derived disassembly of such a binary can be committed to a public
repository is a question for @danielplohmann and is not answerable from
inside the pipeline. It is also the reason this document stops at a proposal.

Note the repo already declines on licence grounds alone: SysWhispers2_x86 is
out because it ships no licence file, and that was recorded as a maintainer
decision rather than a technical one.


## Shape of the thing

A sibling to `Recipe`, not a variant of it.

```python
@dataclass
class SampleSource:
    """A binary the maintainer supplies. The pipeline never fetches one."""
    sha256: str              # primary identity; the file is verified against it
    acquired_from: str       # "MalwareBazaar", "VirusTotal", ...
    acquired: str            # ISO date
    # Why this binary is believed to be this family. Required, and required to
    # cite something checkable.
    attribution: str
    attribution_source: str  # URL of the published analysis
```

```python
@dataclass
class SampleRecipe:
    family: str
    version: str             # a campaign or first-seen date; there is no release
    sample: SampleSource
    artifacts: List[Artifact]
    # Corpus families whose bodies must be subtracted before anything is
    # admitted. Not a hint - the run fails if the match rate is implausible.
    subtract: List[str]
    min_functions: Optional[int] = None
    notes: str = ""
```

Deliberately absent: `Source`, `BuildStep`, `toolchains`, `build_flags`,
`requires`. A `SampleRecipe` cannot express a build, so it cannot accidentally
become one.

**Filename and marker.** `Recipe.slug` produces
`<family>_<version>_<toolchain>_<arch>_<component>`. The producer slot is
where blobs already put `msvc`; sample-derived data puts `sample`, so the
track is visible in every filename, every README row and every link, and
cannot be lost by copying a file. `provenance.json` gains
`"derived_from": "sample"` and omits `compiler`, `toolchain`, `build_flags`
rather than filling them with placeholders.

**`validate --deep` has to learn the distinction.** A PicHash shared between
two build-derived families is a leakage finding — the corpus's one standing
finding, `__scrt_common_main_seh`, is of that kind. A PicHash shared between a
sample-derived family and a build-derived one is the opposite: it is the
subtraction working, and it means the sample-derived side should not have
admitted that body. The existing check would report it as a collision and be
wrong about what it means.


## Work, in order

1. `SampleSource` / `SampleRecipe`, the `sample` producer slug, and the
   `derived_from` provenance field. Small; the dataclasses are the easy part.
2. A subtract-and-residue pass. The real work. Needs a decision on what
   "matched" means at this stage — PicHash equality is exact and cheap,
   minhash is what MCRIT actually does — and a hard floor on what fraction of
   an image must be accounted for.
3. Teach `validate` and `validate --deep` the two classes, so a cross-class
   collision reads as a subtraction failure rather than leakage.
4. A README section stating plainly that these bodies are not build-verified
   and what that means for a match. The corpus's credibility rests on the
   distinction being loud.
5. Only then, a first family.

Steps 1-4 are useful on their own and carry no sample. Step 5 needs the
licensing answer from step 3 of the previous section.


## What this does not do

It does not acquire samples. Input is a local file the maintainer already
holds, verified against a hash stated in the recipe. Nothing in the pipeline
reaches out to a malware repository, and nothing should: that is a credentialed,
audited, accountable act, and burying it in a build script would be the wrong
place for it.
