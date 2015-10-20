## CMS Setup

The CMS data model consists of tables encoded as CSV files.
The following section explains how to prepare *patient-viz* for
the use of CMS data and download the example dataset.

In order to set up the tool for CMS data please run the following command:

```bash
./setup.sh --default
```

This downloads all necessary files for label creation of claims data events
and also example patient claims data. Note that, by downloading the data,
you agree with the respective terms and conditions of the sources
(info pages can be accessed when running the script). You will
be prompted to confirm before downloading (this can be silenced
via `-s`). In total, required space will be approximately `3 GB`.
Processing of some files may take a while letting the script appear
to be frozen (which is not the case!). If you plan on converting many
patient files run `./setup.sh --default --burst`.

If you only want to partially download the example data and descriptions
refer to the help: `./setup.sh -h`. The tool works without any of this data
but uses git submodules which need to be initialized manually
when no setup is performed.

## Running the tool

After setting up the tool, files can be viewed with the following command:

```bash
./start.sh -p json/AEF023C2029F05BC.json --start
```

where the argument after `-p` points to one of the previously created
event sequence files which can be found in `json/`. The command starts
a server which can be stopped using `./start.sh --stop`.

The list of available files can be seen using:

```bash
./start.sh --list
```

Patient files can be created manually from the example claims data by
issuing the following commands:

```bash
./cms_get_patient.py -p AEF023C2029F05BC -f format.json -o json/%p.json -c style_classes.json -- cms
./build_dictionary.py -p json/AEF023C2029F05BC.json -c config.txt -o json/dictionary.json
./start.sh --list-update
```

`./cms_analyze.py -f format.json -- cms` can be used to see which patient ids for `-p` are available.

Own data can be loaded by passing the event sequence file as argument to `-p`
and the dictionary file as argument to `-d`. For further information you
can consult the help (`./start.sh -h`) and the [JSON specification](spec.md).

## Using Shelve Input

Shelve input data is a faster access for CMS data. Setting up the tool is the
same as described in section [CMS Setup](#cms-setup). However, it is not necessary
to download the example dataset. *patient-viz* provides a shelve wrapper that
converts tables into the standard CMS model on the fly. The following section
explains how to use this wrapper.

In order to use a shelve database you need to manually convert
patients and update the `config.txt` file. This can be done by
copying `config_shelve.txt` to `config.txt` as initial config file
and correcting the paths.

Converting a patient:

```bash
./shelve_access.py -p AEF023C2029F05BC -c config.txt | ./cms_get_patient.py -p AEF023C2029F05BC -f format_shelve.json -o json/%p.json -c style_classes.json -- -
./build_dictionary.py -p json/AEF023C2029F05BC.json -c config.txt -o json/dictionary.json
./start.sh --list-update
```

or in short:

```bash
./setup.sh --shelve --do-convert --convert AEF023C2029F05BC
```

The list of available patient ids can be seen using:

```bash
./shelve_access.py -c config.txt -l
```

The `./start.sh` and `./setup.sh` scripts also accept `--shelve` as argument to use this behavior.
