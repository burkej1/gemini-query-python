import re


class Options(object):
    """A container to hold various default values and incorporate any values passed as arguments."""
    def __init__(self):
        self.fields = ["gene", 
                       "impact", 
                       "is_lof", 
                       "chrom", 
                       "start", 
                       "end", 
                       "ref", 
                       "alt", 
                       "filter", 
                       "qual_depth", 
                       "vep_pick",   # TEMP
                       "transcript", # TEMP 
                       "vep_hgvsc", 
                       "vep_hgvsp", 
                       "vep_brcaex_hgvs_cdna", 
                       "vep_brcaex_hgvs_protein", 
                       "vep_brcaex_clinical_significance_enigma", 
                       "vep_brcaex_date_last_evaluated_enigma", 
                       "num_het", 
                       "num_hom_alt"]
        self.where_filters = "(vep_pick = 1 AND filter IS NULL)"
        self.transcripts = ["BRCA1:NM_007294.3",  # BRCA1 transcript (vep gets this one wrong). Format like this
                            "BRCA2:NM_000059.3"]

    def update_with_arguments(self, args):
        """Updates internal values based on passed arguments"""
        specified_filter_given = False
        if args["fields"] is not None:
            # Replace default fields with user supplied fields if given
            self.fields = args["fields"].split(',')
        if args["where"] is not None:
            # Replace filtering thresholds with a user supplied string, disables simple_filter
            specified_filter_given = True
            self.where_filters = args["where"]
            pass
        if args["simple_filter"] is not None and not specified_filter_given:  
            # Updates filters based on simple arguments
            self.translate_update_where(args["simple_filter"])

    def translate_update_where(self, where_argument):
        """Translates simple arguments to predefined where queries and updates the where_filter option
        accordingly."""
        # # Each query is designed as a block so each block can be combined with an AND or OR
        # Standard filtering criteria, primary annotation blocks and variants that passed filters
        standard = ("(vep_pick = 1 AND filter = None)")

        # Primary transcripts passing filters and variants in requested transcripts passing filters
        genes_to_exclude = [transcript.split(':')[0] for transcript in self.transcripts]
        genes_to_exclude = " AND ".join(["gene != '" + gene + "'" for gene in genes_to_exclude])
        transcripts_to_include = [transcript.split(':')[1] for transcript in self.transcripts]
        transcripts_to_include = " OR ".join(["transcript = '" + transcript + "'" for transcript in transcripts_to_include])
        standard_transcripts = "((vep_pick = 1 AND filter IS NULL AND ( {exclude} )) " \
                               "OR " \
                               "(( {include} ) AND filter IS NULL))".format(transcriptlist=self.transcripts, 
                                                                            exclude=genes_to_exclude, 
                                                                            include=transcripts_to_include)

        # As above but including variants that didn't pass filters
        standard_transcripts_nofilter = re.sub("AND filter IS NULL", "", standard_transcripts)

        # # Extra filtering thresholds that can be combined with the above
        # LoF variants
        lof = "(impact = 'frameshift_variant' OR  " \
              "impact = 'stop_gained' OR  " \
              "impact = 'splice_donor_variant' OR  " \
              "impact = 'splice_acceptor_variant' OR  " \
              "is_lof = 1)"

        # Pathogenic (BRCA exchange) and LoF variants
        lof_pathogenic = "(impact = 'frameshift_variant' OR  " \
                         "impact = 'stop_gained' OR  " \
                         "impact = 'splice_donor_variant' OR  " \
                         "impact = 'splice_acceptor_variant' OR  " \
                         "is_lof = 1 OR " \
                         "vep_brcaex_clinical_significance_enigma = 'Pathogenic')"
        
        # Instantiating the dictionary
        translation_dictionary = {"standard": standard, 
                                  "standard_transcripts": standard_transcripts, 
                                  "standard_transcripts_nofilter": standard_transcripts_nofilter, 
                                  "lof": lof, 
                                  "lof_pathogenic": lof_pathogenic}

        # Checking to see if one or two filter setting where supplied
        if ',' in where_argument:
            split_plaintext = where_argument.split(',')
            where_filter_one = translation_dictionary[split_plaintext[0]]
            where_filter_two = translation_dictionary[split_plaintext[1]]
            where_filter = "{one} AND {two}".format(one=where_filter_one, 
                                                    two=where_filter_two)
        else:
            where_filter = translation_dictionary[where_argument]

        # Translating the request and updating the where filter option
        self.where_filters = where_filter

