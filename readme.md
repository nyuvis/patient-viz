# patient-viz

*patient-viz* is a tool allowing to view and explore insurance claim
or other time sequence event data. The web-based tool is mostly written in
[d3](http://d3js.org/) and uses [python](https://www.python.org/) and shell on the back-end.
Example data from medical insurance claim data can be downloaded automatically.
We also have a [live demo](http://nyuvis.github.io/patient-viz/index.html)!
The project is a joint product of [Josua Krause](http://josuakrause.github.io/info/), Narges Sharif Razavian,
Enrico Bertini, and [David Sontag](http://cs.nyu.edu/~dsontag/).

[![The tool in action!](overview.png)](http://nyuvis.github.io/patient-viz/index.html)

[![Build Status](https://travis-ci.org/nyuvis/patient-viz.svg?branch=master)](https://travis-ci.org/nyuvis/patient-viz)

## Setup

Setting up the project can be done without prerequisites on *MacOS* and *linux*.
For windows you need to install [git](https://msysgit.github.io/).
You can use *git BASH* to execute the shell commands.

In order to set up the tool please run the following command:

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

The system can also handle data stored in a shelve db. However, you need to manually convert
patients stored this way and update the `config.txt` file.
(Note: copy `config_shelve.txt` to `config.txt` as initial config file)

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

## Feature Extraction and Model Creation

The data can also be used for predictive modeling.
Please refer to the [documentation](feature_extraction/extract.md).

## Publications

* 2015 Workshop on Visual Analytics in Healthcare - Demo [[PDF]](pub/vahc_2015_demo.pdf)
* AMIA 2015 Annual Symposium - Demo [[PDF]](pub/amia_2015_demo.pdf)

## Contributing

Pull requests are highly appreciated :)
Also, feel free to open [issues](https://github.com/nyuvis/patient-viz/issues) for any questions or bugs you may encounter.
