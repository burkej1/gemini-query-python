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
pip install git+https://github.com/burkej1/gemini-query-python
```

## Usage

Can be run in four modes sample, variant, table and info.

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


### Table

Generates a table using a given set of filters containing a given set of fields.

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
                        output (DEPRECATED)
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

### Variant

Searches the database for a given variant (using c. HGVS notation). The --partial option allows regex matching (not yet implemented).

### Sample

Returns a list of all variants present in a given sample. Full sample ID or BS ID only can be given.

### Info

Returns a list of all fields present in the database.

## Presets

### Filter Presets

There are several included filter presets:

Name | Description
------------ | -------------
standard | All variants in vep_pick transcripts or given transcripts (by config or hard-coded). All preset filters include this unless otherwise stated.
lof | All Loss of Function (LoF) variants.
lof_pathogenic | All LoF variants and variants classified Pathogenic by BRCA exchange
reportable | All LoF or Pathogenic by BRCA exchange variants in _BRCA1_, _BRCA2_, _TP53_, _PALB2_ and _ATM_:c.7271T>G.

### Field Set Presets

There are also several predefined sets of useful fields.

## Examples

### Table
All reportable variants (one per line)
```
gemini_wrapper table -i my.db -o reportable_vars.tsv -pf reportable
```

All reportable variants (flattened to one sample per line and appending UNDR ROVER call information)
```
gemini_wrapper table -i my.db -o reportable_vars.tsv -pf reportable --flattened --check_undrrover
```

All variants in TP53, PALB2 and ATM with a REVEL score greater than 0.5 (-ef adds filters, -eF adds fields)
```
gemini_wrapper table -i my.db -o reportable_vars.tsv -pf standard \
  -ef "vep_rvl_revel_score > 0.5" -eF vep_rvl_revel_score \
  --genes TP53,PALB2,ATM 
```

### Sample
All variants associated with a given BSID
```
gemini_wrapper sample -i my.db -o test.tsv -S BS123456
```

All the hidesamples option can be used to suppress the sample lists if there are a lot of common variants
```
gemini_wrapper sample -i my.db -o test.tsv -S BS123456 --hidesamples
```

### Variant
Search the database for a given variant and return the entry along with detailed sample information if present
```
gemini_wrapper variant -i my.db -o test.tsv -v "NM_000059.3:c.12345G>A"
```

