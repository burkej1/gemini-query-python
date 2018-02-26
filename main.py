"""Main"""
from __future__ import print_function
import argparse
import re
import classes
from gemini import GeminiQuery  # Importing the gemini query class


def undrrover_concordance(gemini_row):
    """Calculates concordance between UNDR-ROVER and GATK sample lists"""
    undrrover_l = gemini_row["vep_undrrover_sample"].split('&')
    undrrover_pct = gemini_row["vep_undrrover_pct"].split('&')
    undrrover_s = set(undrrover_l)
    # Undrrover strips the _S123 from the end of the s, doing the same to GATK
    gatk_l = [re.sub(r"_S\d\d\d", "", sample) for sample in gemini_row["variant_samples"]]
    gatk_s = set(gatk_l)
    concordant_s = gatk_s.intersection(undrrover_s)
    gatk_only = gatk_s.difference(undrrover_s)
    undrrover_only = undrrover_s.difference(gatk_s)
    try:
        concordance_percentage = float(len(concordant_s)) / float(len(gatk_s))
    except ZeroDivisionError:
        # Indicates a variant with no GATK samples, not sure how this can happen yet
        concordance_percentage = 999
    # Using the original lists to match the samples to their pct
    undrrover_only_ordered = [sample for sample in undrrover_l if sample in undrrover_only]
    undrrover_only_pct = [undrrover_pct[undrrover_l.index(sample)]
                          for sample
                          in undrrover_l if sample in undrrover_only]
    return concordance_percentage, gatk_only, undrrover_only


def get_fields(db):
    """Returns all fields in the given database"""
    query = "SELECT * FROM variants limit 1"
    db.run(query)
    return db.header


def get_table(geminidb, args, options):
    """Returns a table of variants based on the fields and filter options provided"""
    if args["check_undrrover"]:
        query = "SELECT {fields} FROM variants WHERE {where_filter}" \
                    .format(fields=options.query_fields() +
                            ", vep_undrrover_sample, vep_undrrover_pct",
                            where_filter=options.query_filter())
        geminidb.run(query, show_variant_samples=True)
        table_lines = [str(geminidb.header) +
                       "\tConcordance Percentage\tGATK Only Samples\tUNDR-ROVER Only Samples"]
        for row in geminidb:
            conc_pct, gatk_only, undrrover_only = undrrover_concordance(row)
            metricsrow = str(row) + "\t{conc}\t{gatk}\t{undrrover}".format(conc=conc_pct,
                                                                           gatk=gatk_only,
                                                                           undrrover=undrrover_only)
            table_lines.append(metricsrow)
        return(table_lines)
    else:
        query = "SELECT {fields} FROM variants WHERE {where_filter}" \
                    .format(fields=options.query_fields(),
                            where_filter=options.query_filter())
        # print("Generating a table from the following query:")
        # print(query)
        geminidb.run(
            query, show_variant_samples=True
        )  # Hardcoded the boolean here, might want to change
        table_lines = [str(geminidb.header)]
        for row in geminidb:
            table_lines.append(str(row))
        return table_lines


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
    geminidb.run(query, gt_filter, show_variant_samples=True)
    table_lines = [str(geminidb.header)]
    for row in geminidb:
        table_lines.append(str(row))
    return table_lines


def get_variant_information(geminidb, args, options):
    """Retrieves genotype and depth information for all carriers of a given variant along with the
    original variant entry"""
    variant = args["variant"]

    if ',' in variant:
        # # # # Temporary feature
        # If the variant is a comma separated list of variants do this instead
        variantlist = variant.split(',')
        varlines = []
        for var in variantlist:
            is_found = False
            varquery = "SELECT {fields} FROM variants WHERE vep_hgvsc == '{var}'" \
                .format(fields=options.query_fields(), var=var)
            geminidb.run(varquery, show_variant_samples=True)
            for varline in geminidb:
                is_found = True  # Set to found if there is at least one line in the db
                varlines.append("{var}\tTRUE\t".format(var=var) + str(varline))
            if not is_found:
                varlines.append("{var}\tFALSE".format(var=var))
        query_header = "Search Variant\tIn Database\t" + str(geminidb.header)
        return([query_header] + varlines)

    gt_info_fields = ["gt_ref_depths", "gt_alt_depths", "gt_alt_freqs", "gt_quals"]
    get_carriers_query = "SELECT {fields} FROM variants WHERE vep_hgvsc == '{variant}'" \
                             .format(fields=options.query_fields(), variant=variant)
    geminidb.run(get_carriers_query, show_variant_samples=True)
    variant_matches = []
    original_header = geminidb.header
    for row in geminidb:
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
        gq_formatted_samples = []  # List containing field.sampleid values
        for sample in variant_matches[0]:  # Completing the above list
            gq_formatted_samples.append('.'.join([field, sample]))
        # Building a query from the above list
        genotype_query = "SELECT {gtinfo} FROM variants WHERE vep_hgvsc == '{variant}'" \
                             .format(gtinfo=', '.join(gq_formatted_samples),
                                     variant=variant)
        # Running the query against the database
        geminidb.run(genotype_query)
        # Getting the sample IDs from the header
        headerids = [
            headerid.lstrip(field + '.')
            for headerid in str(geminidb.header).split('\t')
        ]
        # Creating a dictionary stored under the current GT field being queried
        genotype_info_dictionary[field] = {}
        for row in geminidb:
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
        "nofilter"       : "Flag. If set will include filtered variants in the output",
        "check_undrrover": "Flag. If set the table output will include UNDR-ROVER "           \
                           "concordance metrics."
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
                                  default="presets.config")
    shared_arguments.add_argument("-pf", "--presetfilter",
                                  help=helptext_dict["presetfilter"],
                                  default="standard_transcripts")
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
    # Table
    parser_table = subparsers.add_parser("table",
                                         help=helptext_dict["table"],
                                         parents=[shared_arguments])
    parser_table.add_argument("-o", "--output",
                              help=helptext_dict["output"],
                              required=True)
    parser_table.add_argument("--check_undrrover",
                              help=helptext_dict["check_undrrover"],
                              action="store_true")
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
