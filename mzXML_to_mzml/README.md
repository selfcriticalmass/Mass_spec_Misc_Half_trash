# mzXML to mzML Converter

Converts mass spectrometry data from the legacy **mzXML** format to the modern **mzML** standard (HUPO-PSI).

## Requirements

- Python 3.10+
- [psims](https://github.com/mobiusklein/psims) — mzML writer
- [numpy](https://numpy.org/) — binary array decoding

Install with [uv](https://github.com/astral-sh/uv):

```bash
uv add psims numpy
```

Or with pip:

```bash
pip install psims numpy
```

## CLI Usage

### Convert all mzXML files in the current directory

```bash
python convert_mzxml_to_mzml.py
```

### Convert all mzXML files in a specific directory

```bash
python convert_mzxml_to_mzml.py -d /path/to/data
```

### Convert a single file

```bash
python convert_mzxml_to_mzml.py -i sample.mzXML
```

### Convert a single file with a custom output path

```bash
python convert_mzxml_to_mzml.py -i sample.mzXML -o converted_sample.mzML
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `-i`, `--input` | Path to a single `.mzXML` file to convert |
| `-o`, `--output` | Output `.mzML` file path (only valid with `--input`) |
| `-d`, `--directory` | Directory containing `.mzXML` files (default: `.`) |

## Programmatic Usage

Import the conversion function into your own code:

```python
from convert_mzxml_to_mzml import convert_mzxml_to_mzml

# Convert a single file
convert_mzxml_to_mzml("sample.mzXML", "sample.mzML")
```

Batch convert in a script:

```python
import os
from convert_mzxml_to_mzml import convert_mzxml_to_mzml

data_dir = "/path/to/mzxml_files"
for fname in os.listdir(data_dir):
    if fname.lower().endswith(".mzxml"):
        src = os.path.join(data_dir, fname)
        dst = os.path.join(data_dir, os.path.splitext(fname)[0] + ".mzML")
        convert_mzxml_to_mzml(src, dst)
```

## How It Works

### Peak data decoding (`decode_peaks`)

mzXML stores spectral peak data as a **base64-encoded, zlib-compressed** binary blob of interleaved floating-point values:

```
[mz₁, intensity₁, mz₂, intensity₂, mz₃, intensity₃, ...]
```

The decoding pipeline:
1. **Base64 decode** — converts the text blob back to raw bytes
2. **zlib decompress** — inflates the compressed binary data
3. **numpy frombuffer** — interprets the bytes as float64 (or float32) values
4. **Array slicing** — `values[0::2]` extracts m/z, `values[1::2]` extracts intensities

### XML parsing

The script uses Python's `xml.etree.ElementTree` to parse the mzXML tree. mzXML 3.2 uses a namespace (`http://sashimi.sourceforge.net/schema_revision/mzXML_3.2`), but some files omit it. Every `find()`/`findall()` call therefore tries the namespaced tag first, then falls back to the bare tag name.

### mzML writing

The [psims](https://github.com/mobiusklein/psims) library provides `MzMLWriter`, which enforces the correct mzML document structure through a context-manager API:

```
cvList → fileDescription → run → spectrumList → [index]
```

For each scan, the converter extracts:
- **Scan number** → used as the spectrum `id` (`scan=1`, `scan=2`, ...)
- **MS level** → stored as a CV param (`MS level 1`, `MS level 2`, etc.)
- **Retention time** → parsed from ISO 8601 duration format (`PT335.616S` → `335.616` seconds)
- **Precursor m/z** → preserved for MS²+ scans as precursor information
- **Peak arrays** → decoded binary data passed directly to the writer

The resulting mzML files are indexed and compatible with tools like pymzml, pyOpenMS, and mzmine.
