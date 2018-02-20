"""This primarily contains the options class with some of useful methods"""
import re


class Options(object):
    """A container to hold various default values and incorporate any values passed
    as arguments."""

    def __init__(self):
        self.base_fields = [  # Basic fields
            "gene",
            "impact",
            "is_lof",
            "chrom",
            "start",
            "end",
            "ref",
            "alt",
            "filter",
            "vep_pick",  # TEMP
            "transcript",  # TEMP
            "vep_hgvsc",
            "vep_hgvsp",
            "vep_brcaex_hgvs_cdna",
            "vep_brcaex_hgvs_protein",
            "vep_brcaex_clinical_significance_enigma",
            "vep_brcaex_date_last_evaluated_enigma",
            "num_het",
            "num_hom_alt"
        ]
        self.explore_fields = self.base_fields + [ 
            # Population frequencies
            "vep_exac_af",
            "vep_exac_af_nfe",
            "vep_gnomad_af_nfe",
            # Effect prediction
            "vep_cadd_phred",
            "vep_cadd_raw",
            "vep_rvl",
            "vep_rvl_revel_score",
            "polyphen_pred",
            "polyphen_score",
            "sift_pred",
            "sift_score",
            # Splicing
            "vep_ada_score",
            "vep_rf_score",
            "vep_maxentscan_alt",
            "vep_maxentscan_diff",
            "vep_maxentscan_ref",
        ]
        self.user_fields = [  # User supplied fields
        ]
        self.where_filters = "(vep_pick = 1 AND filter IS NULL)"  # Default filter
        self.user_filters = [  # User supplied filters
        ]
        self.transcripts = [
            "BRCA1:NM_007294.3",  # BRCA1 transcript (vep gets this one wrong).
            "BRCA2:NM_000059.3"
        ]
        self.overwrite_fields = False
        self.overwrite_filters = False
        self.exclude_filtered = True  # Exclude filtered variants
        # To be populated at the end of argument incorporation and subsequently
        # used by all table-producing functions
        self.final_filter = None
        self.final_fields = None

    def update_with_arguments(self, args):
        """Updates internal values based on passed arguments"""
        # Arguments that overwrite defaults/presets
        if args["fields"] is not None:
            # Replace default fields with user supplied fields if given
            self.user_fields = args["fields"].split(',')
            self.overwrite_fields = True
        if args["filters"] is not None:
            # Replace filtering thresholds with a user supplied string, disables presetfilter
            self.overwrite_filters = True
            self.where_filters = args["filters"]
        # Non-overwriting arguments
        if args["presetfilter"] is not None and not self.overwrite_filters:
            self.where_filters = self.get_predefined_filter(args["presetfilter"])
        if args["extrafilter"] is not None and not self.overwrite_fields:
            self.user_filters = args["extrafilter"]
        if args["extrafields"] is not None and not self.overwrite_fields:
            self.user_fields = args["extrafields"].split(',')
        # Populating final filter and field variables
        if not self.overwrite_fields:
            if args["presetfields"] == "base":
                self.final_fields = self.base_fields + self.user_fields
            elif args["presetfields"] == "explore":
                self.final_fields = self.base_fields + self.explore_fields + self.user_fields
            else:
                self.final_fields = self.base_fields + self.user_fields
        else:
            self.final_fields = self.user_fields
        if not self.overwrite_filters:
            self.final_filter = "({presetf} AND {userf})".format(presetf=self.where_filters,
                                                                 userf=self.user_filters)
        else:
            self.final_filter = self.user_filters

    def get_predefined_filter(self, where_argument):
        """Translates simple arguments to predefined where queries."""
        # # Each query is designed as a block so each block can be combined with an AND or OR
        # Standard filtering criteria, primary annotation blocks and variants that passed filters
        standard = "(vep_pick = 1 AND filter = None)"

        # Variants in primary transcript blocks and in requested transcripts
        genes_to_exclude = [
            transcript.split(':')[0] for transcript in self.transcripts
        ]
        genes_to_exclude = " AND ".join(
            ["gene != '" + gene + "'" for gene in genes_to_exclude])
        transcripts_to_include = [
            transcript.split(':')[1] for transcript in self.transcripts
        ]
        transcripts_to_include = " OR ".join([
            "transcript = '" + transcript + "'"
            for transcript in transcripts_to_include
        ])
        standard_transcripts = "((vep_pick = 1 AND filter IS NULL AND ( {exclude} )) " \
                               "OR ( {include} ) AND filter IS NULL))" \
                                   .format(exclude=genes_to_exclude,
                                           include=transcripts_to_include)

        # As above but including variants that didn't pass filters
        standard_transcripts_nofilter = re.sub("AND filter IS NULL", "",
                                               standard_transcripts)

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
        translation_dictionary = {
            "standard": standard,
            "standard_transcripts": standard_transcripts,
            "standard_transcripts_nofilter": standard_transcripts_nofilter,
            "lof": lof,
            "lof_pathogenic": lof_pathogenic
        }

        # Checking to see if one or two filter settings where supplied
        if ',' in where_argument:
            split_plaintext = where_argument.split(',')
            where_filter_one = translation_dictionary[split_plaintext[0]]
            where_filter_two = translation_dictionary[split_plaintext[1]]
            where_filter = "{one} AND {two}".format(
                one=where_filter_one, two=where_filter_two)
        else:
            where_filter = translation_dictionary[where_argument]

        # Translating the request and updating the where filter option
        return where_filter




