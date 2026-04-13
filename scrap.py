import marimo

__generated_with = "0.22.5"
app = marimo.App(width="medium")


@app.cell
def _():
    import rainbow as rb
    import numpy as np
    from psims.mzml.writer import MzMLWriter
    import os

    def convert_d_to_mzml(d_path: str, output_dir: str = None, get_file_str: str = "DATA.MS") -> str:
        """
        Convert an Agilent .D directory to an mzML file.

        Parameters
        ----------
        d_path : str
            Path to the Agilent .D directory.
        output_dir : str, optional
            Directory to write the mzML file. Defaults to the same directory as the .D file.
        get_file_str: str
            The name for the binary inside the folder. Defaults to 'DATA.MS'

        Returns
        -------
        str
            Path to the written mzML file.
        """
        d_path = d_path.rstrip("/\\")
        basename = os.path.splitext(os.path.basename(d_path))[0]
        out_dir = output_dir or os.path.dirname(d_path) or "."
        out_path = os.path.join(out_dir, basename + ".mzML")

        datadir = rb.read(d_path)
        datafile = datadir.get_file(get_file_str)

        rts = datafile.xlabels
        mzs = datafile.ylabels
        intensities = datafile.data

        with MzMLWriter(open(out_path, "wb"), close=True) as writer:
            writer.controlled_vocabularies()
            writer.file_description(["MS1 spectrum"])
            writer.software_list([{"id": "rainbow", "version": "1.0"}])
            writer.instrument_configuration_list([{"id": "IC1", "component_list": []}])
            writer.data_processing_list([{"id": "DP1", "processing_methods": []}])

            with writer.run(id=basename):
                with writer.spectrum_list(count=len(rts)):
                    for i, rt in enumerate(rts):
                        intensity_row = intensities[i]
                        mask = intensity_row > 0
                        mz_array = mzs[mask]
                        intensity_array = intensity_row[mask]

                        writer.write_spectrum(
                            mz_array=mz_array,
                            intensity_array=intensity_array,
                            id=f"scan={i+1}",
                            params=[
                                {"ms level": 1},
                                {"total ion current": float(intensity_array.sum())},
                            ],
                            scan_params=[
                                {"scan start time": float(rt), "unit_name": "minute"}
                            ],
                        )

        return out_path


    # Convert a list of .D directories to mzML, returns list of output paths
    convert_batch = lambda d_paths, output_dir=None: [
        convert_d_to_mzml(p, output_dir) for p in d_paths
    ]
    return (convert_batch,)


@app.cell
def _():
    import glob

    return (glob,)


@app.cell
def _(glob):
    tims_data = glob.glob("/Users/zr4/Desktop/OneDrive - Oak Ridge National Laboratory/Data/Tschaplinski_Lab_data/LowRes-GCMS/*.D")
    return (tims_data,)


@app.cell
def _(convert_batch, tims_data):
    convert_batch(tims_data)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
