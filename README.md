# SQIsignTriangle with Qlapoti

This repository contains C and SageMath implementations for **SQIsignTriangle**,
a SQIsign-variant research prototype built on top of the SQIsign NIST Round 2
codebase and the Qlapoti ideal-to-isogeny translation algorithm.

The code is organized as two complementary implementations:

- `C-implementation/`: a C implementation derived from
  [SQISign/the-sqisign](https://github.com/SQISign/the-sqisign), with the
  ideal-to-isogeny step replaced by the Qlapoti-based implementation from
  [KULeuven-COSIC/Qlapoti](https://github.com/KULeuven-COSIC/Qlapoti).
- `Sage-implementation/`: a SageMath proof-of-concept implementation of
  SQIsign, PRISM, and SQIsignTriangle, sharing the same underlying
  quaternion, elliptic-curve, 2-dimensional isogeny, and Qlapoti routines.

The top-level README gives the common entry points. For implementation-level
details, see `C-implementation/README.md`, `C-implementation/SQIsign_README.md`,
and `Sage-implementation/README.md`.

## Background

SQIsign is a compact post-quantum signature scheme based on supersingular
isogenies and quaternion ideals. The upstream SQIsign repository provides a
C implementation with CMake build support, KAT generation, tests, benchmarks,
and parameter sets for NIST security levels 1, 3, and 5.

Qlapoti provides an efficient algorithm for translating quaternion ideals to
isogenies. Its public repository contains both a SageMath implementation and a
C implementation integrated into the SQIsign NIST Round 2 codebase.

This repository combines those ingredients with SQIsignTriangle:

- the SageMath side is intended for experimentation, validation, and
  algorithmic clarity;
- the C side is intended for compiled tests, KATs, and performance
  measurements following the SQIsign build and benchmarking workflow.

## Repository Layout

```text
.
|-- C-implementation/
|   |-- apps/                 # KAT, examples, benchmarks, fuzzing binaries
|   |-- include/              # Public SQIsign headers
|   |-- KAT/                  # Known-answer test vectors
|   |-- scripts/precomp/      # Sage/Python precomputation scripts
|   |-- src/                  # C implementation modules
|   |-- test/                 # Top-level SQIsign tests
|   |-- README.md             # Qlapoti-specific C implementation notes
|   `-- SQIsign_README.md     # Original SQIsign README copied locally
`-- Sage-implementation/
    |-- sqisign_triangle.py   # SQIsignTriangle implementation and demo
    |-- sqisign.py            # SQIsign implementation and demo
    |-- prism.py              # PRISM implementation and demo
    |-- bench_sqi_triangle.py # SQIsignTriangle benchmark script
    |-- bench_sqi.py          # SQIsign benchmark script
    |-- bench_prism.py        # PRISM benchmark script
    |-- qlapoti.py            # Qlapoti ideal-to-isogeny routines
    |-- quaternions.py        # Quaternion ideal routines
    |-- theta/                # 2-dimensional theta-isogeny code
    `-- README.md             # Sage usage and module overview
```

## C Implementation

### Requirements

- CMake 3.13 or later
- A C11-compatible compiler
- GMP 6.0.0 or later, unless building with `-DGMP_LIBRARY=MINI`
- SageMath, only if rerunning the precomputation scripts
- Optional: Valgrind, for heap-memory measurements with Massif

### Build

From the top-level repository directory:

```sh
cd C-implementation
mkdir -p build
cd build
cmake -DSQISIGN_BUILD_TYPE=ref -DCMAKE_BUILD_TYPE=Release ..
make
```

The build produces libraries, tests, KAT generators, examples, and benchmark
binaries for `lvl1`, `lvl3`, and `lvl5`.

Useful CMake options inherited from SQIsign include:

- `-DSQISIGN_BUILD_TYPE=ref`: reference implementation
- `-DSQISIGN_BUILD_TYPE=broadwell`: optimized finite-field arithmetic for
  Intel Broadwell and later
- `-DGMP_LIBRARY=SYSTEM`: link against the system GMP library
- `-DGMP_LIBRARY=BUILD`: build GMP as part of the project
- `-DGMP_LIBRARY=MINI`: use the bundled mini-gmp sources
- `-DENABLE_SIGN=OFF`: build verification functionality only
- `-DCMAKE_BUILD_TYPE=Release`: optimized build with assertions disabled
- `-DCMAKE_BUILD_TYPE=Debug`, `ASAN`, `MSAN`, `LSAN`, or `UBSAN`: debugging
  and sanitizer builds

### Test

From `C-implementation/build`:

```sh
make test
```

or:

```sh
ctest
```

The test suite includes KAT tests, random self-tests for key generation,
signing and verification, and sub-library unit tests. If long-running tests
hit CTest's default timeout, use:

```sh
ctest --timeout <seconds>
```

### Known-Answer Tests

KAT files are stored in `C-implementation/KAT`. They can be regenerated with:

```sh
cd C-implementation/build
apps/PQCgenKAT_sign_lvl1
apps/PQCgenKAT_sign_lvl3
apps/PQCgenKAT_sign_lvl5
```

### Benchmarks

For full SQIsign-style key generation, signing, and verification benchmarks:

```sh
cd C-implementation/build/apps
./benchmark_lvl1 --iterations=10
./benchmark_lvl3 --iterations=10
./benchmark_lvl5 --iterations=10
```

The C implementation also includes Qlapoti-oriented benchmarks for the
ideal-to-isogeny step:

```sh
cd C-implementation/build/src/id2iso/ref/lvl1/test
./sqisign_id2iso_benchmark_dim2id2iso_lvl1 --iterations=10
./sqisign_id2iso_benchmark_qlapoti_normeq_lvl1 --iterations=10
```

Replace `lvl1` by `lvl3` or `lvl5` to benchmark the other parameter sets.

### Precomputations

The generated constants in `C-implementation/src/precomp` are already included,
so precomputation is not required for a normal build.

To rerun the precomputation scripts, use a recent SageMath version and run:

```sh
cd C-implementation/build
make precomp
make
```

See `C-implementation/README.md` and `C-implementation/SQIsign_README.md` for
the full description of the Qlapoti changes, SQIsign build options, pqm4 notes,
and third-party code notices.

## SageMath Implementation

The SageMath implementation is a proof of concept. It favors readability and
experimentation over optimized arithmetic; in particular, parts of the elliptic
curve and isogeny arithmetic use SageMath functionality directly.

### Requirements

- SageMath
- Python execution through `sage --python`

The supported parameter levels are `1`, `3`, and `5`.

### Run SQIsignTriangle

```sh
cd Sage-implementation
sage --python -O sqisign_triangle.py 1
```

If the level argument is omitted, level 1 is used.

The same code can be imported from Sage/Python:

```python
from sqisign_triangle import SQIsignTriangle, SQIsignTriangle_verify
import params

lvl = 1  # 3 or 5
params.set_sqi_triangle_params(lvl)

alice = SQIsignTriangle()
msg = "Hello world"
sigma = alice.sign(msg)

ok = SQIsignTriangle_verify(msg, sigma, alice.pk)
print(f"Verification: {ok}")
```

### Benchmark SQIsignTriangle

```sh
cd Sage-implementation
sage --python -O bench_sqi_triangle.py 1
```

The benchmark averages key generation, signing, and verification timings over
10 runs.

### Run the Other Sage Prototypes

SQIsign:

```sh
cd Sage-implementation
sage --python -O sqisign.py 1
sage --python -O bench_sqi.py 1
```

PRISM:

```sh
cd Sage-implementation
sage --python -O prism.py 1
sage --python -O bench_prism.py 1
```

See `Sage-implementation/README.md` for the module-by-module description.

## Main Differences from the SQIsign C Codebase

The C implementation follows the SQIsign NIST Round 2 project structure, but
modifies the ideal-to-isogeny component to use Qlapoti. The most relevant local
changes are:

- replacement of the original `dim2id2iso_ideal_to_isogeny_clapotis`
  implementation by a Qlapoti-based version;
- additional Qlapoti norm-equation solving code in the quaternion module;
- updated `id2iso` tests and benchmarks;
- updated precomputation scripts and constants for the Qlapoti integration;
- the original SQIsign README is preserved as `C-implementation/SQIsign_README.md`.

## References

- [SQISign/the-sqisign](https://github.com/SQISign/the-sqisign): upstream
  SQIsign C implementation.
- [KULeuven-COSIC/Qlapoti](https://github.com/KULeuven-COSIC/Qlapoti):
  SageMath and C implementations accompanying Qlapoti.
- [SQIsign specification](https://sqisign.org/): specifications and supporting
  documentation for SQIsign.
- [Qlapoti paper](https://eprint.iacr.org/2025/1604): "Qlapoti: Simple and
  Efficient Translation of Quaternion Ideals to Isogenies".

## Licenses

The two implementation directories keep their own licenses and notices:

- `C-implementation/` follows the SQIsign licensing and notices. See
  `C-implementation/LICENSE`, `C-implementation/NOTICE`, and
  `C-implementation/COPYING.LGPL`.
- `Sage-implementation/` is licensed under the MIT License. See
  `Sage-implementation/LICENSE`.

Please check the corresponding subdirectory before redistributing code or
derived artifacts.
