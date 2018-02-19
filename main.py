from __future__ import print_function
from gemini import GeminiQuery  # Importing the gemini query class
import argparse  # For parsing arguments
import classes


def print_fields(db):
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



def main():
    """Main function which parses arguments and calls relevant functions"""

    # Defining the argument parser
    parser = argparse.ArgumentParser(description="Python wrapper for interacting with GEMINI databases.")
    parser.add_argument("-M", "--mode", help="Mode to run in. " \
                                             "sample - returns all variants in a given sample; " \
                                             "variant - search for a given variant; " \
                                             "table - returns a table of variants from given criteria; " \
                                             "info - print the fields present in the database.")
    parser.add_argument("-i", "--input", help="Input database to query.", required=True)
    parser.add_argument("-o", "--output", help="File to write query results to.", required=True)
    parser.add_argument("-sf", "--simple_filter", help="Preset filter options.", default=None)
    # Below are more manual options that will override defaults
    parser.add_argument("-f", "--fields", help="Comma separated list of fields to pull.", default=None)
    parser.add_argument("-w", "--where", help="Filter string in SQL WHERE structure.", default=None)
    # Need to add a an argument for transcript lists, not sure whether to take a file or string as input #
    arguments = vars(parser.parse_args()) # Parsing the arguments and storing as a dictionary

    options = classes.Options()  # Setting up the options class with a number of defaults
    options.update_with_arguments(arguments)  # Updating the program options based on the passed arguments

    gemini_db = GeminiQuery.GeminiQuery(arguments["input"])  # Creating the gemini database object 

    # Calling relevant function depending on the chosen mode
    if arguments["mode"] == "sample":
        pass
    elif arguments["mode"] == "variant":
        pass
    elif arguments["mode"] == "table":
        output_table = get_table(gemini_db, arguments, options)
        with open(arguments["output"], 'w') as outputfile:
            outputfile.write('\n'.join(output_table))
    elif arguments["mode"] == "info":
        print_comprehension = [print(field) for field in print_fields(gemini_db).split('\t')]


if __name__ == "__main__":
    main()

