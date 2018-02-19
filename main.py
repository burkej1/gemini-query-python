from __future__ import print_function
from gemini import GeminiQuery  # Importing the gemini query class
import argparse  
import re
import classes


def get_fields(db):
    """Returns all fields in the given database"""
    query = "SELECT * FROM variants limit 1"
    db.run(query)
    return db.header


def get_table(db, args, options):
    """Returns a table of variants based on the fields and filter options provided"""
    query = "SELECT {fields} FROM variants WHERE {where_filter}" \
                .format(fields=', '.join(options.fields), 
                                         where_filter=options.where_filters)
    print("Generating a table from the following query:")
    print(query)
    db.run(query, show_variant_samples=True)  # Hardcoded the boolean here, might want to change
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
        idquery = "SELECT name FROM samples WHERE name LIKE '%{bsid}%'".format(bsid=sampleid)
        db.run(idquery)
        matches = []
        for row in db:
            matches.append(str(row))
        if len(matches) > 1:
            print("Multiple matches for given BSID, exiting.")
            quit()
        elif len(matches) == 0:
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
    genotype_information = "gts.{fsi}, gt_ref_depths.{fsi}, gt_alt_depths.{fsi}, gt_alt_freqs.{fsi}" \
                               .format(fsi=fullsampleid)
    query = "SELECT {fields}, {genotypeinfo} FROM variants WHERE {where_filter}" \
                .format(fields=', '.join(options.fields), 
                                         where_filter=options.where_filters, 
                                         genotypeinfo=genotype_information)
    print("Generating a table from the following query filtered to only include variants present in the " \
          "given sample:")
    print(query)
    print(gt_filter)
    # # Recreating the gemini database object to clear the previous query
    # db = GeminiQuery.GeminiQuery(args["input"])  
    db.run(query, gt_filter, show_variant_samples=False)
    table_lines = [str(db.header)]
    for row in db:
        table_lines.append(str(row))
    return table_lines


def main():
    """Main function which parses arguments and calls relevant functions"""
    # parser.add_argument("-M", "--mode", help="Mode to run in. " \
    #                                          "sample - returns all variants in a given sample; " \
    #                                          "variant - search for a given variant; " \
    #                                          "table - returns a table of variants from given criteria; " \
    #                                          "info - print the fields present in the database.")

    # Defining the argument parser
    # Top level parser
    parser = argparse.ArgumentParser(prog="gemini_wrapper")
    # Shared argument parser (inherited by subparsers)
    shared_arguments = argparse.ArgumentParser(add_help=False)
    shared_arguments.add_argument("-i", "--input", help="Input database to query.", required=True)
    shared_arguments.add_argument("-sf", "--simple_filter", help="Preset filter options.", default=None)
    # Below are more manual options that will override defaults
    shared_arguments.add_argument("-f", "--fields", help="Comma separated list of fields to extract.", 
                                  default=None)
    shared_arguments.add_argument("-w", "--where", help="Filter string in SQL WHERE structure.", default=None)
    # Need to add a an argument for transcript lists, not sure whether to take a file or string as input #

    # Setting up subparsers
    subparsers = parser.add_subparsers(title="Modes", help="Mode to run in.", dest="mode")
    # Sample parser
    parser_sample = subparsers.add_parser("sample", help="Searches for a given sample and returns a list " \
                                                         "of all variants present in that sample", 
                                          parents=[shared_arguments])
    parser_sample.add_argument("-o", "--output", help="File to write sample query table to.", required=True)
    parser_sample.add_argument("-S", "--sampleid", help="Sample ID to query", required=True)
    # Might also want to add an argument that will take a list of samples/BSIDs
    # Variant parser
    parser_variant = subparsers.add_parser("variant", help="Searches database for given variant.", 
                                           parents=[shared_arguments])
    parser_variant.add_argument("-o", "--output", help="File to write variant query table to.", required=True)
    parser_variant.add_argument("-v", "--variant", help="variant to query", required=True)
    # Table parser
    parser_table = subparsers.add_parser("table", help="Returns a table containing given fields and  " \
                                                       "filtered using given filtering options.", 
                                         parents=[shared_arguments])
    parser_table.add_argument("-o", "--output", help="File to write output table to.", required=True)
    # Info parser
    parser_info = subparsers.add_parser("info", help="Prints the fields present in the database", 
                                        parents=[shared_arguments])

    arguments = vars(parser.parse_args()) # Parsing the arguments and storing as a dictionary

    options = classes.Options()  # Setting up the options class with a number of defaults
    options.update_with_arguments(arguments)  # Updating the program options based on the passed arguments

    gemini_db = GeminiQuery.GeminiQuery(arguments["input"])  # Creating the gemini database object 

    # Calling relevant function depending on the chosen mode
    if arguments["mode"] == "sample":
        output_table = get_sample_variants(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "variant":
        pass
    elif arguments["mode"] == "table":
        output_table = get_table(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "info":
        print_comprehension = [print(field) for field in get_fields(gemini_db).split('\t')]


if __name__ == "__main__":
    main()

