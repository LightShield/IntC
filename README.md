# IntC

C prototype of **IntentCompile**: compile a baseline against a checkable
contract, not as-if.

Companion to the paper *[Compiling Against Intent](https://github.com/LightShield/IntC)*
(PDF: [`main.pdf`](main.pdf)).

From `poc/`:

```
pip install -e .[test]
python reproduce.py --check    # no CBMC
python reproduce.py            # Windows: CBMC 6.11.0 + MSVC 19.29 /O2
```

Replay, toolchain pins, and expected outcomes: [`ARTIFACT_README.md`](ARTIFACT_README.md).

| Path | Role |
|---|---|
| `poc/intentc/` | Compiler |
| `poc/cases/` | Contracts, C baselines, harnesses |
| `poc/reproduce.py` | Rebuild catalog / ablation / timed tables |
| `experiments/eval/` | Shipped JSON, TeX, ASM |
| `main.tex` / `main.pdf` | Paper (named snapshot) |

MIT. Extracts are not whole-program compiles of DPDK, Zephyr, or OGRE.
