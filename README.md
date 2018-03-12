## Description

Wrapper to make querying gemini databases a bit easier

## Installation

To install (requires conda):

```bash
conda create -n env-name python=2.7
source activate env-name
conda install pip
pip install yaml
conda install -c bioconda gemini
pip install gemini-query-python
```

## Usage

Can be run in four modes:

```
usage: gemini_wrapper [-h] {sample,variant,table,info} ...

optional arguments:
  -h, --help            show this help message and exit

Modes:
  {sample,variant,table,info}
                        Mode to run in.
    sample              Searches for a given sample and returns a list of all
                        variants present in that sample
    variant             Searches database for given variant.
    table               Returns a table containing given fields and filtered
                        using given filtering options.
    info                Prints the fields present in the database
```

'table' to generate a table using a given set of filters containing a given set of fields.

```
usage: gemini_wrapper table [-h] -i INPUT [-c PRESETS_CONFIG]
                            [-pf PRESETFILTER] [-ef EXTRAFILTER]
                            [-pF PRESETFIELDS] [-eF EXTRAFIELDS] [--nofilter]
                            [--flattened] [--hidesamples] [--genes GENES]
                            [-f FILTER] [-F FIELDS] -o OUTPUT
                            [--check_undrrover]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input database to query.
  -c PRESETS_CONFIG, --presets_config PRESETS_CONFIG
                        Config file containing a number of preset values with
                        space for user-defined presets.
  -pf PRESETFILTER, --presetfilter PRESETFILTER
                        Preset filter options. One of: standard (Primary
                        annotation blocks and variants passing filters);
                        standard_transcripts (Standard but will prioritise a
                        given list of transcripts, the default); Can be
                        combined one of the following (separated by a comma):
                        lof (frameshift, stopgain, splicing variants and
                        variants deemed LoF by VEP); lof_pathogenic (lof and
                        variants classified Pathogenic by ENIGMA (using data
                        from BRCA exchange). E.g. -sf standard_transcripts,lof
  -ef EXTRAFILTER, --extrafilter EXTRAFILTER
                        Additional fields to use in addition to the presets,
                        combined with the AND operator.
  -pF PRESETFIELDS, --presetfields PRESETFIELDS
                        Can be 'base' (a set of basic fields), or 'explore'
                        which included population frequencies and various
                        effect prediction scores in addition to the base
                        fields. Can include user-defined sets of fields in the
                        presets.yaml file.
  -eF EXTRAFIELDS, --extrafields EXTRAFIELDS
                        A comma separated list of fields to include in
                        addition to the chosen presets.
  --nofilter            Flag. If set will include filtered variants in the
                        output
  --flattened           Flag. If set will output a table with one sample per
                        line.
  --hidesamples         Flag. Hide sample lists.
  --genes GENES         List of genes to include. If not specified will
                        include all
  -f FILTER, --filter FILTER
                        Filter string in SQL WHERE structure, overwrites
                        presets.
  -F FIELDS, --fields FIELDS
                        Comma separated list of fields to extract, overwrites
                        presets.
  -o OUTPUT, --output OUTPUT
                        File to write sample query table to.
  --check_undrrover     Flag. If set the table output will include UNDR-ROVER
                        concordance metrics.
```

## Examples
