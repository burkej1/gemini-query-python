# Contains some useful classes

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
                       "transcript", 
                       "vep_hgvsc", 
                       "vep_hgvsp", 
                       "vep_brcaex_hgvs_cdna", 
                       "vep_brcaex_hgvs_protein", 
                       "vep_brcaex_clinical_significance_enigma", 
                       "vep_brcaex_date_last_evaluated_enigma", 
                       "num_het", 
                       "num_hom_alt"]
        self.where_filters = "vep_pick = 1 AND filter IS NULL"
        self.transcripts = ["BRCA1:NM_007294.3",  # BRCA1 transcript (vep gets this one wrong). Format like this
                            "BRCA2:NM_000059.3"]

    def update_with_arguments(self, args):
        """Updates internal values based on passed arguments"""
        pass

    def translate_where(self, plaintext_where):
        """Translates plain text arguments to specific where queries"""
        # Formatting more complex where queries here

        # # Primary transcripts passing filters and variants in requested transcripts passing filters
        # Exclude the primary annotation blocks for genes where transcripts where specified
        genes_to_exclude = [transcript.split(':')[0] for transcript in self.transcripts]
        genes_to_exclude = " AND ".join(["gene != '" + gene + "'" for gene in genes_to_exclude])
        # Include specified transcripts
        transcripts_to_include = [transcript.split(':')[1] for transcript in self.transcripts]
        transcripts_to_include = " OR ".join(["transcript = '" + transcript + "'" for transcript in transcripts_to_include])
        standard_transcripts = "(vep_pick = 1 AND filter IS NULL AND ( {exclude} )) " \
                               "OR " \
                               "(( {include} ) AND filter IS NULL)".format(transcriptlist=self.transcripts, 
                                                                        exclude=genes_to_exclude, 
                                                                        include=transcripts_to_include)

        # Instantiating the dictionary
        translation_dictionary = {"standard": "vep_pick = 1 AND filter = None", 
                                  "standard_transcripts": standard_transcripts}

        # Translating the request
        return translation_dictionary[plaintext_where]
