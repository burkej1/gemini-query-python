"""Contains primary functions for each mode and the main() function."""
from __future__ import print_function
import argparse
import re
import classes
from gemini import GeminiQuery  # Importing the gemini query class


def get_fields(db):
    """Returns all fields in the given database"""
    query = "SELECT * FROM variants limit 1"
    db.run(query)
    return db.header


def get_table(geminidb, args, options):
    """Returns a table of variants based on the fields and filter options provided"""
    # Constructing the query
    query = "SELECT {fields} FROM variants WHERE {where_filter}" \
                .format(fields=options.query_fields(),
                        where_filter=options.query_filter())
    # Run the query. If flattened is set to true samples must be included.
    geminidb.run(query, show_variant_samples=(args["hidesamples"] or args["flattened"]))

    # Using the QueryProcessing class to return the query in the chosen output format
    query_result = classes.QueryProcessing(geminidb)

    # Return format based on arguments
    if args["check_undrrover"]:
        if args["flattened"]:
            return query_result.flattened_lines_ur()
        else:
            return query_result.regular_lines_ur()

    if args["flattened"]:
        return query_result.flattened_lines()
    elif args["filtersamples"]:
        return query_result.regular_lines_filtersamples()
    else:
        return query_result.regular_lines()


def get_sample_variants(geminidb, args, options):
    """Returns a table of variants present in a given sample (by BSID or full sample name)"""
    sampleid = args["sampleid"]
    if re.match(r"BS\d\d\d\d\d\d", sampleid):
        # If a BSID is given find the corresponding full name in the database
        print("Searching for BSID.")
        idquery = "SELECT name FROM samples WHERE name LIKE '%{bsid}%'".format(bsid=sampleid)
        geminidb.run(idquery)
        matches = []
        for row in geminidb:
            matches.append(str(row))
        if len(matches) > 1:
            print("Multiple matches for given BSID, exiting.")
            quit()
        elif not matches:
            print("No matches found for given BSID, exiting.")
            quit()
        else:
            print("Found: {match}".format(match=matches[0]))
        fullsampleid = matches[0]
        gt_filter = "gt_types.{fullsampleid} == HET OR " \
                    "gt_types.{fullsampleid} == HOM_ALT".format(fullsampleid=fullsampleid)
    else:
        # If a BSID is not given it's assumed the full name was given
        fullsampleid = sampleid
        gt_filter = "gt_types.{fullsampleid} == HET OR " \
                    "gt_types.{fullsampleid} == HOM_ALT".format(fullsampleid=fullsampleid)
    genotype_information = "gts.{fsi}, gt_ref_depths.{fsi}, gt_alt_depths.{fsi}, " \
                           "gt_alt_freqs.{fsi}".format(fsi=fullsampleid)
    query = "SELECT {fields}, {genotypeinfo} FROM variants WHERE {where_filter}" \
                .format(fields=options.query_fields(),
                        where_filter=options.query_filter(),
                        genotypeinfo=genotype_information)
    print("Generating a table from the following query filtered to only include " \
          "variants present in the given sample:")
    print(query)
    print(gt_filter)
    geminidb.run(query, gt_filter, show_variant_samples=args["hidesamples"])
    table_lines = [str(geminidb.header)]
    for row in geminidb:
        table_lines.append(str(row))
    return table_lines



def get_variant_information(geminidb, args, options):
    # Getting the list of variants (or one, doesn't matter I think)
    if args["partial"]:
        vls = ["vep_hgvsc LIKE '%{}%'".format(v) for v in args["variant"].split(',')]
    else:
        vls = ["vep_hgvsc == '{}'".format(v) for v in args["variant"].split(',')]
    vfilter = '(' + ' OR '.join(vls) + ')' if len(vls) > 1  else '(' + ''.join(vls) + ')'
    print(vfilter)

    # Constructing the query
    query = "SELECT {fields} FROM variants WHERE {where_filter} AND {vfilter}" \
                .format(fields=options.query_fields(),
                        where_filter=options.query_filter(),
                        vfilter=vfilter)
    # Run the query. If flattened is set to true samples must be included.
    geminidb.run(query, show_variant_samples=(args["hidesamples"] or args["flattened"]))

    # Using the QueryProcessing class to return the query in the chosen output format
    query_result = classes.QueryProcessing(geminidb)
    if args["check_undrrover"]:
        if args["flattened"]:
            return query_result.flattened_lines_ur()
        else:
            return query_result.regular_lines_ur()

    if args["flattened"]:
        return query_result.flattened_lines()
    else:
        return query_result.regular_lines()



def parse_arguments():
    """Creates the argument parser, parses and returns arguments"""
    # Dictionary containing helptext (to make the parser more readable)
    helptext_dict = {
        "presets_config" : "Config file containing a number of preset values with space for " \
                           "user-defined presets.",
        "presetfilter"   : "Preset filter options. One of: standard (Primary annotation "     \
                           "blocks and variants passing filters); standard_transcripts "      \
                           "(Standard but will prioritise a given list of transcripts, the "  \
                           "default); Can be combined one of the following (separated by a "  \
                           "comma): lof (frameshift, stopgain, splicing variants and "        \
                           "variants deemed LoF by VEP); lof_pathogenic (lof and variants "   \
                           "classified Pathogenic by ENIGMA (using data from BRCA "           \
                           "exchange). E.g. -sf standard_transcripts,lof",
        "extrafilter"    : "Additional fields to use in addition to the presets, combined "   \
                           "with the AND operator.",
        "presetfields"   : "Can be 'base' (a set of basic fields), or 'explore' which "       \
                           "included population frequencies and various effect prediction "   \
                           "scores in addition to the base fields. Can include user-defined " \
                           "sets of fields in the presets.yaml file.",
        "extrafields"    : "A comma separated list of fields to include in addition to the "  \
                           "chosen presets.",
        "filter"         : "Filter string in SQL WHERE structure, overwrites presets.",
        "fields"         : "Comma separated list of fields to extract, overwrites presets.",
        "sample"         : "Searches for a given sample and returns a list of all variants "  \
                           "present in that sample",
        "output"         : "File to write sample query table to.",
        "sampleid"       : "Sample ID to query",
        "variant"        : "Searches database for given variant.",
        "variantname"    : "Variant to query in HGVS format. E.g. NM_000059.3:c.6810_6817del",
        "table"          : "Returns a table containing given fields and filtered using "      \
                           "given filtering options.",
        "info"           : "Prints the fields present in the database",
        "nofilter"       : "Flag. If set will include filtered variants in the output (DEPRE" \
                           "CATED)",
        "check_undrrover": "Flag. If set the table output will include UNDR-ROVER "           \
                           "concordance metrics.",
        "flattened"      : "Flag. If set will output a table with one sample per line.",
        "hidesamples"    : "Flag. Hide sample lists.",
        "genes"          : "List of genes to include. If not specified will include all",
        "partial"        : "Flag. Allow partial matching of variants.",
        "filtersamples"  : "Flag. Filter sample lists to only include GT filter PASS."
    }
    # Defining the argument parser
    # Top level parser
    parser = argparse.ArgumentParser(prog="gemini_wrapper")
    # Shared argument parser (inherited by subparsers)
    shared_arguments = argparse.ArgumentParser(add_help=False)
    shared_arguments.add_argument("-i", "--input",
                                  help="Input database to query.",
                                  required=True)
    shared_arguments.add_argument("-c", "--presets_config",
                                  help=helptext_dict["presets_config"],
                                  default=None)
    shared_arguments.add_argument("-pf", "--presetfilter",
                                  help=helptext_dict["presetfilter"],
                                  default="standard")
    shared_arguments.add_argument("-ef", "--extrafilter",
                                  help=helptext_dict["extrafilter"],
                                  default=None)
    shared_arguments.add_argument("-pF", "--presetfields",
                                  help=helptext_dict["presetfields"],
                                  default="base")
    shared_arguments.add_argument("-eF", "--extrafields",
                                  help=helptext_dict["extrafields"],
                                  default=None)
    shared_arguments.add_argument("--nofilter",
                                  help=helptext_dict["nofilter"],
                                  action="store_true")
    shared_arguments.add_argument("--flattened",
                                  help=helptext_dict["flattened"],
                                  action="store_true")
    shared_arguments.add_argument("--hidesamples",
                                  help=helptext_dict["hidesamples"],
                                  action="store_false")
    shared_arguments.add_argument("--genes",
                                  help=helptext_dict["genes"],
                                  default=None)
    shared_arguments.add_argument("--check_undrrover",
                                  help=helptext_dict["check_undrrover"],
                                  action="store_true")
    shared_arguments.add_argument("--filtersamples",
                                  help=helptext_dict["filtersamples"],
                                  action="store_true")
    # Below are manual options that will override defaults
    shared_arguments.add_argument("-f", "--filter", help=helptext_dict["filter"], default=None)
    shared_arguments.add_argument("-F", "--fields", help=helptext_dict["fields"], default=None)
    # Setting up subparsers
    subparsers = parser.add_subparsers(title="Modes", help="Mode to run in.", dest="mode")
    # Sample
    parser_sample = subparsers.add_parser("sample",
                                          help=helptext_dict["sample"],
                                          parents=[shared_arguments])
    parser_sample.add_argument("-o", "--output",
                               help=helptext_dict["output"],
                               required=True)
    parser_sample.add_argument("-S", "--sampleid",
                               help=helptext_dict["sampleid"],
                               required=True)
    # Variant
    parser_variant = subparsers.add_parser("variant",
                                           help=helptext_dict["variant"],
                                           parents=[shared_arguments])
    parser_variant.add_argument("-o", "--output",
                                help=helptext_dict["output"],
                                required=True)
    parser_variant.add_argument("-v", "--variant",
                                help=helptext_dict["variantname"],
                                required=True)
    parser_variant.add_argument("--partial",
                                  help=helptext_dict["partial"],
                                  action="store_true")
    # Table
    parser_table = subparsers.add_parser("table",
                                         help=helptext_dict["table"],
                                         parents=[shared_arguments])
    parser_table.add_argument("-o", "--output",
                              help=helptext_dict["output"],
                              required=True)
    # Info
    parser_info = subparsers.add_parser("info",
                                        help=helptext_dict["info"],
                                        parents=[shared_arguments])

    arguments = vars(parser.parse_args())  # Parsing the arguments and storing as a dictionary

    return arguments


def main():
    """Main function which parses arguments and calls relevant functions"""
    # Parsing arguments
    arguments = parse_arguments()

    # Processing the presets config file
    presets = classes.Presets(arguments["presets_config"])

    # Passing the arguments and presets to a query constructor object
    queryformatter = classes.QueryConstructor(arguments, presets)

    # Creating the gemini database object
    gemini_db = GeminiQuery.GeminiQuery(
        arguments["input"])

    # Calling relevant function depending on the chosen mode
    if arguments["mode"] == "sample":
        output_table = get_sample_variants(gemini_db, arguments, queryformatter)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "variant":
        output_table = get_variant_information(gemini_db, arguments, queryformatter)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "table":
        output_table = get_table(gemini_db, arguments, queryformatter)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "info":
        print_comprehension = [
            print(field) for field in get_fields(gemini_db).split('\t')
        ]


if __name__ == "__main__":
    main()
