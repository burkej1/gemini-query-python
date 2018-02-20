"""Main"""
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


def get_table(db, args, options):
    """Returns a table of variants based on the fields and filter options provided"""
    query = "SELECT {fields} FROM variants WHERE {where_filter}" \
                .format(fields=', '.join(options.final_fields),
                        where_filter=options.final_filter)
    print("Generating a table from the following query:")
    print(query)
    db.run(
        query, show_variant_samples=True
    )  # Hardcoded the boolean here, might want to change
    table_lines = [str(db.header)]
    for row in db:
        table_lines.append(str(row))
    return table_lines


def get_sample_variants(db, args, options):
    """Returns a table of variants present in a given sample (by BSID or full sample name)"""
    sampleid = args["sampleid"]
    if re.match("BS\d\d\d\d\d\d", sampleid):
        # If a BSID is given find the corresponding full name in the database
        print("Searching for BSID.")
        idquery = "SELECT name FROM samples WHERE name LIKE '%{bsid}%'".format(
            bsid=sampleid)
        db.run(idquery)
        matches = []
        for row in db:
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
                .format(fields=', '.join(options.final_fields),
                        where_filter=options.final_filter,
                        genotypeinfo=genotype_information)
    print("Generating a table from the following query filtered to only include " \
          "variants present in the given sample:")
    print(query)
    print(gt_filter)
    # # Recreating the gemini database object to clear the previous query
    # db = GeminiQuery.GeminiQuery(args["input"])
    db.run(query, gt_filter, show_variant_samples=True)
    table_lines = [str(db.header)]
    for row in db:
        table_lines.append(str(row))
    return table_lines


def get_variant_information(db, args, options):
    """Retrieves genotype and depth information for all carriers of a given variant along with the
    original variant entry"""
    variant = args["variant"]
    gt_info_fields = [
        "gt_ref_depths", "gt_alt_depths", "gt_alt_freqs", "gt_quals"
    ]
    get_carriers_query = "SELECT vep_hgvsc FROM variants WHERE vep_hgvsc == '{variant}'".format(
        variant=variant)
    get_carriers_query = "SELECT {fields} FROM variants WHERE vep_hgvsc == '{variant}'" \
                             .format(fields=', '.join(options.final_fields), variant=variant)
    db.run(get_carriers_query, show_variant_samples=True)
    variant_matches = []
    original_header = db.header
    for row in db:
        original_variant_info = str(row)
        variant_matches.append(row["variant_samples"])

    if len(variant_matches) > 1:
        print("Multiple matches found, exiting.")
        quit()
    elif not variant_matches:
        print("No matches found, exiting.")
        quit()

    # Instantiating an empty dictionary to store everything
    genotype_info_dictionary = {}
    for field in gt_info_fields:
        # Build a separate query for each genotype query (better return structure this way)
        genotype_query_formatted_samples = []  # List containing field.sampleid values
        for sample in variant_matches[0]:  # Completing the above list
            genotype_query_formatted_samples.append('.'.join([field, sample]))
        # Building a query from the above list
        genotype_query = "SELECT {gtinfo} FROM variants WHERE vep_hgvsc == '{variant}'" \
                             .format(gtinfo=', '.join(genotype_query_formatted_samples),
                                     variant=variant)
        # Running the query against the database
        db.run(genotype_query)
        # Getting the sample IDs from the header
        headerids = [
            headerid.lstrip(field + '.')
            for headerid in str(db.header).split('\t')
        ]
        # Creating a dictionary stored under the current GT field being queried
        genotype_info_dictionary[field] = {}
        for row in db:
            for s_index, value in enumerate(str(row).split('\t')):
                # Storing the sample IDs and values as key-value pairs
                genotype_info_dictionary[field][headerids[s_index]] = value

    # Formatting the genotype information table
    header = ["Sample"]
    header.extend(gt_info_fields)
    gt_table_lines = [
        "Variant Entry:", original_header, original_variant_info, "",
        "Carrier Information:", '\t'.join(header)
    ]
    for sample in variant_matches[0]:
        workingline = [sample]
        for field in gt_info_fields:
            workingline.append(genotype_info_dictionary[field][sample])
        gt_table_lines.append('\t'.join(workingline))
    return gt_table_lines


def main():
    """Main function which parses arguments and calls relevant functions"""
    # Defining the argument parser
    # Top level parser
    parser = argparse.ArgumentParser(prog="gemini_wrapper")
    # Shared argument parser (inherited by subparsers)
    shared_arguments = argparse.ArgumentParser(add_help=False)
    shared_arguments.add_argument(  # Database input
        "-i", "--input", help="Input database to query.", required=True)
    shared_arguments.add_argument(  # Preset filters
        "-pf",
        "--presetfilter",
        help=
        "Preset filter options. One of: standard (Primary annotation blocks and variants " \
        "passing filters); standard_transcripts (Standard but will prioritise a given " \
        "list of transcripts); Can be combined one of the following " \
        "(separated by a comma): lof (frameshift, stopgain, splicing variants and " \
        "variants deemed LoF by VEP); lof_pathogenic (lof and variants classified " \
        "Pathogenic by ENIGMA (using data from BRCA exchange). " \
        "E.g. -sf standard_transcripts,lof",
        default=None)
    shared_arguments.add_argument(  # Extra filters
        "-ef",
        "--extrafilter",
        help="Additional fields to use in addition to the presets, combined with the AND " \
             "operator.",
        default=None)
    shared_arguments.add_argument(  # Preset fields
        "-pF",
        "--presetfields",
        help="Can be 'base' (a set of basic fields), or 'explore' which included population " \
             "frequencies and various effect prediction scores in addition to the base " \
             "fields.",
        default=None, choices=['base', 'explore'])
    shared_arguments.add_argument(  # Extra fields
        "-eF",
        "--extrafields",
        help="A comma separated list of fields to include in addition to the chosen presets.",
        default=None)
    # Below are more manual options that will override defaults
    shared_arguments.add_argument(  # Manual fields
        "-F",
        "--fields",
        help="Comma separated list of fields to extract, overwrites presets.",
        default=None)
    shared_arguments.add_argument(  # Manual filters
        "-f",
        "--filters",
        help="Filter string in SQL WHERE structure, overwrites presets.",
        default=None)
    # Need to add a an argument for transcript lists, not sure whether to take a 
    # file or string as input

    # Setting up subparsers
    subparsers = parser.add_subparsers(
        title="Modes", help="Mode to run in.", dest="mode")
    # Sample parser
    parser_sample = subparsers.add_parser("sample",
                                          help="Searches for a given sample and returns a list " \
                                               "of all variants present in that sample",
                                          parents=[shared_arguments])
    parser_sample.add_argument(
        "-o",
        "--output",
        help="File to write sample query table to.",
        required=True)
    parser_sample.add_argument(
        "-S", "--sampleid", help="Sample ID to query", required=True)
    # Might also want to add an argument that will take a list of samples/BSIDs
    # Variant parser
    parser_variant = subparsers.add_parser(
        "variant",
        help="Searches database for given variant.",
        parents=[shared_arguments])
    parser_variant.add_argument(
        "-o",
        "--output",
        help="File to write variant query table to.",
        required=True)
    parser_variant.add_argument(
        "-v",
        "--variant",
        help="Variant to query in HGVS format. E.g. NM_000059.3:c.6810_6817del",
        required=True)
    # Table parser
    parser_table = subparsers.add_parser("table",
                                         help="Returns a table containing given fields and  " \
                                              "filtered using given filtering options.",
                                         parents=[shared_arguments])
    parser_table.add_argument(
        "-o", "--output", help="File to write output table to.", required=True)
    # Info parser
    parser_info = subparsers.add_parser(
        "info",
        help="Prints the fields present in the database",
        parents=[shared_arguments])

    arguments = vars(parser.parse_args())  # Parsing the arguments and storing as a dictionary

    options = classes.Options()  # Setting up the options class with a number of defaults
    options.update_with_arguments(
        arguments
    )  # Updating the program options based on the passed arguments

    gemini_db = GeminiQuery.GeminiQuery(
        arguments["input"])  # Creating the gemini database object

    # Calling relevant function depending on the chosen mode
    if arguments["mode"] == "sample":
        output_table = get_sample_variants(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "variant":
        output_table = get_variant_information(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "table":
        output_table = get_table(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "info":
        print_comprehension = [
            print(field) for field in get_fields(gemini_db).split('\t')
        ]


if __name__ == "__main__":
    main()
