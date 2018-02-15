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
    db.run(query)
    table_lines = [str(db.header)]
    for row in db:
        table_lines.append(str(row))
    return table_lines



def main():
    """Main function which parses arguments and calls relevant functions"""
    # Pulling various default options and setting up the options class
    options = classes.Options()

    # Defining the argument parser
    parser = argparse.ArgumentParser(description="Python wrapper for interacting with GEMINI databases.")
    parser.add_argument("mode", help="Mode to run in. " \
                                     "sample - returns all variants in a given sample; " \
                                     "variant - search for a given variant; " \
                                     "table - returns a table of all variants with sample lists filtered " \
                                     "using given criteria; " \
                                     "info - print the fields present in the database.")
    parser.add_argument("-i", "--input", help="Input database to query.", required=True)
    parser.add_argument("-o", "--output", help="File to write query results to.", required=True)
    parser.add_argument("-f", "--fields", help="List of fields to pull.", default=options.fields)
    parser.add_argument("-w", "--where", help="List of filters in SQL WHERE structure.", 
                        default=options.where_filters)
    # Parsing the arguments and storing as a dictionary
    arguments = vars(parser.parse_args())

    # Updating the program options based on the passed arguments
    options.update_with_arguments(arguments)

    # Creating the gemini database object from the input database
    gemini_db = GeminiQuery.GeminiQuery(arguments["input"])

    # Calling relevant function depending on the mode option
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

