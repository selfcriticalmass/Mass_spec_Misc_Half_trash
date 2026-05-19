#!/usr/bin/env python3
"""Convert mzXML files to mzML format.

Usage as CLI:
    python convert_mzxml_to_mzml.py                  # convert all .mzXML in cwd
    python convert_mzxml_to_mzml.py -i file.mzXML    # convert a single file
    python convert_mzxml_to_mzml.py -d /path/to/dir  # convert all in a directory
    python convert_mzxml_to_mzml.py -i file.mzXML -o out.mzML  # specify output

Usage as import:
    from convert_mzxml_to_mzml import convert_mzxml_to_mzml
    convert_mzxml_to_mzml_to_mzml("input.mzXML", "output.mzML")
"""

import argparse
import base64
import glob
import os
import sys
import xml.etree.ElementTree as ET
import zlib

import numpy as np
from psims.mzml import MzMLWriter


# mzXML 3.2 namespace. Some files may omit the namespace prefix entirely,
# so every find/findall call also falls back to an unqualified tag name.
NS = {"mzXML": "http://sashimi.sourceforge.net/schema_revision/mzXML_3.2"}


def decode_peaks(peaks_data: str, precision: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Decode base64 + zlib-compressed interleaved m/z and intensity arrays.

    mzXML stores spectral data as a base64-encoded, zlib-compressed binary
    blob of alternating float64 (or float32) values: [mz1, int1, mz2, int2, ...].
    This function reverses that encoding and returns two numpy arrays.
    """
    raw = base64.b64decode(peaks_data)
    decompressed = zlib.decompress(raw)
    dtype = np.float64 if precision == 64 else np.float32
    values = np.frombuffer(decompressed, dtype=dtype)
    mzs = values[0::2]
    ints = values[1::2]
    return mzs, ints


def convert_mzxml_to_mzml(input_path: str, output_path: str) -> None:
    """Convert a single mzXML file to mzML format.

    The conversion walks every <scan> element in the mzXML, decodes its
    binary peak data, preserves the precursor m/z (for MS²+ scans), and
    writes a standards-compliant mzML file via the psims library.

    Args:
        input_path:  Path to the input .mzXML file.
        output_path: Path to write the output .mzML file.
    """
    tree = ET.parse(input_path)
    root = tree.getroot()

    # The <msRun> element holds all scans and the total scan count.
    ms_run = root.find("mzXML:msRun", NS)
    if ms_run is None:
        ms_run = root.find("msRun")

    scan_count = int(ms_run.get("scanCount", 0))

    # MzMLWriter uses a context-manager API that guarantees proper XML
    # structure (cvList → fileDescription → run → spectrumList → index).
    with open(output_path, "wb") as out:
        with MzMLWriter(out) as writer:
            writer.controlled_vocabularies()
            writer.file_description(["MSn spectrum"])

            with writer.run(id=1):
                with writer.spectrum_list(scan_count):
                    scans = ms_run.findall("mzXML:scan", NS)
                    if not scans:
                        scans = ms_run.findall("scan")

                    for scan in scans:
                        scan_num = int(scan.get("num"))
                        ms_level = int(scan.get("msLevel"))

                        # Retention time in mzXML is ISO 8601 duration (e.g. "PT335.616S").
                        rt_str = scan.get("retentionTime", "PT0S")
                        retention_time = float(rt_str.replace("PT", "").replace("S", ""))

                        # Precursor m/z is only present for MS² and higher.
                        precursor = scan.find("mzXML:precursorMz", NS)
                        precursor_mz = None
                        if precursor is not None:
                            precursor_mz = float(precursor.text)

                        # The <peaks> element contains the compressed binary data.
                        peaks_elem = scan.find("mzXML:peaks", NS)
                        if peaks_elem is None:
                            peaks_elem = scan.find("peaks")

                        mzs, intensities = np.array([]), np.array([])
                        if peaks_elem is not None and peaks_elem.text:
                            precision = int(peaks_elem.get("precision", "64"))
                            mzs, intensities = decode_peaks(peaks_elem.text.strip(), precision)

                        precursor_info = None
                        if precursor_mz is not None:
                            precursor_info = {
                                "mz": precursor_mz,
                                "intensity": None,
                                "charge": None,
                            }

                        # psims expects scan-level metadata as a list of CV params
                        # or short-hand strings like "MS level 1".
                        scan_params = [
                            f"MS level {ms_level}",
                            {
                                "MS:1000016": retention_time,
                                "unit_accession": "UO:0000031",
                                "unit_name": "second",
                            },
                        ]

                        writer.write_spectrum(
                            mzs,
                            intensities,
                            id=f"scan={scan_num}",
                            precursor_information=precursor_info,
                            scan_params=scan_params,
                        )

    print(f"Converted: {os.path.basename(input_path)} -> {os.path.basename(output_path)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert mzXML files to mzML format.",
    )
    parser.add_argument(
        "-i", "--input",
        help="Path to a single .mzXML file to convert.",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output .mzML file path (only valid with --input).",
    )
    parser.add_argument(
        "-d", "--directory",
        help="Directory containing .mzXML files to convert (default: current directory).",
    )

    args = parser.parse_args()

    if args.input:
        # Single-file mode
        output = args.output or os.path.splitext(args.input)[0] + ".mzML"
        convert_mzxml_to_mzml(args.input, output)
        return

    # Directory mode
    target_dir = args.directory or "."
    mzxml_files = sorted(glob.glob(os.path.join(target_dir, "*.mzXML"))) + \
                  sorted(glob.glob(os.path.join(target_dir, "*.mzxml")))
    if not mzxml_files:
        print(f"No mzXML files found in {target_dir}.")
        return

    for mzxml_file in mzxml_files:
        mzml_file = os.path.splitext(mzxml_file)[0] + ".mzML"
        convert_mzxml_to_mzml(mzxml_file, mzml_file)

    print(f"\nDone. Converted {len(mzxml_files)} file(s).")


if __name__ == "__main__":
    main()
