"""Contains classes for handling the presets.config yaml file and constructing
gemini queries."""
from __future__ import print_function
import re
import yaml

class Presets(object):
    """Reads preset options from the supplied config file"""
    def __init__(self, presets_config):
        with open(presets_config, 'r') as presets_input:
            try:
                presets = yaml.load(presets_input)
            except yaml.YAMLError, exc:
                print("Error loading presets config file.")
                raise exc
        self.presets = presets

    def get_preset(self, key):
        """Gets a preset from the config file using the given key"""
        return self.presets[key]

    def format_transcripts(self, t_or_g):
        """Formats the supplied list of transcripts. Can return a list of genes or
        transcripts depending on the t_or_g argument value."""
        genes = [transcript.split(':')[0] for transcript in self.get_preset("transcripts")]
        genes = " AND ".join(["gene != '" + gene + "'" for gene in genes])
        transcripts = [transcript.split(':')[1] for transcript in self.get_preset("transcripts")]
        transcripts = " OR ".join([
            "transcript = '" + transcript + "'"
            for transcript in transcripts
        ])
        if t_or_g == "transcripts":
            return transcripts
        elif t_or_g == "genes":
            return genes


class QueryConstructor(object):
    """Contains variables and methods for constructing gemini queries from arguments
    and/or the presets.config file. Takes the arguments dictionary from argparse and
    the presets object when created. Methods use these and return specific gemini
    queries when called. The values could be supplied to the functions when called but
    this way makes the calls a bit cleaner."""

    def __init__(self, arguments, presets):
        self.args_dict = arguments
        self.presets_o = presets

    def query_filter(self):
        """Returns the query filter constructed from arguments and presets"""
        # Getting the preset filter as a string
        presetfilter = self.get_predefined_filter()
        userfilter_extra = self.args_dict["extrafilter"]
        userfilter_manual = self.args_dict["filter"]
        if userfilter_manual is not None:
            # If filter is manually defined return as is
            returnfilter = userfilter_manual
        elif userfilter_extra is not None:
            # If an extra filter is supplied, combine with the preset
            returnfilter = "{presetfilter} AND {userfilter}" \
                .format(presetfilter=presetfilter,
                        userfilter=userfilter_extra)
        else:
            # Otherwise return just the preset filter
            returnfilter = presetfilter
        if self.args_dict["nofilter"]:
            # If the nofilter flag is set remove the filter part of the filter
            returnfilter = re.sub("AND filter IS NULL", "", returnfilter)
        return returnfilter

    def query_fields(self):
        """Returns a formatted list of fields for the GEMINI query"""
        # Using the preset field arg to pull a list of fields from the config
        presetfields = self.presets_o.get_preset(self.args_dict["presetfields"])
        # Directly extracting extra and manually defined fields from args
        userfields_extra = self.args_dict["extrafields"]
        userfields_manual = self.args_dict["fields"]
        if userfields_manual is not None:
            # If fields are manually specified return only those fields
            returnfields = ', '.join(userfields_manual)
        elif userfields_extra is not None:
            # If extra fields are specified return those combined with the chosen (or default)
            # preset.
            returnfields = ', '.join(presetfields + userfields_extra.split(','))
        else:
            # If there are no extra fields and no fields are manually defined return the presets
            returnfields = ', '.join(presetfields)
        # if self.args_dict["check_undrrover"]:
        #     # If the check undrrover flag is set add the UR fields
        #     returnfields += ", vep_undrrover_sample, vep_undrrover_pct, " \
        #                     "vep_undrrover_nv, vep_undrrover_np"
        return returnfields

    def get_predefined_filter(self):
        """Translates simple arguments to predefined where queries."""
        # # Each query is designed as a block so each block can be combined with an AND or OR
        # Standard filtering criteria, primary annotation blocks and variants that passed filters
        standard = "(vep_pick = 1 AND filter = None)"

        # Variants in primary transcript blocks and in requested transcripts
        standard_transcripts = "((vep_pick = 1 AND filter IS NULL AND ( {exclude} )) " \
                               "OR (( {include} ) AND filter IS NULL))" \
                                   .format(exclude=self.presets_o.format_transcripts("genes"),
                                           include=self.presets_o.format_transcripts("transcripts"))

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
        if ',' in self.args_dict["presetfilter"]:
            split_plaintext = self.args_dict["presetfilter"].split(',')
            where_filter_one = translation_dictionary[split_plaintext[0]]
            where_filter_two = translation_dictionary[split_plaintext[1]]
            where_filter = "{one} AND {two}".format(
                one=where_filter_one, two=where_filter_two)
        else:
            where_filter = translation_dictionary[self.args_dict["presetfilter"]]

        # Returning the preset filter string
        return where_filter


class QueryProcessing(object):
    """Takes the output of a gemini query and processes it for output"""
    def __init__(self, gq, UR=False):
        self.gq = gq
        self.smptoidx = gq.sample_to_idx
        self.header = str(gq.header)

    def flattened_lines(self):
        """Flattens the output to one line per sample and appends sample genotype info"""
        flat_hdr = '\t'.join(self.header.split('\t')[:-3]) + "{\tSample\tGT Filter\tAlt Frequency\tRef Depth\tAlt Depth"
        table_lines = [flat_hdr]
        for row in self.gq:
            samples = row["variant_samples"]  # Getting the variant samples as a list
            for sample in samples:
                smpidx = self.smptoidx[sample]
                sampleline = '\t'.join(str(row).split('\t')[:-3]) + \
                    "\t{SMP}\t{FT}\t{FREQ}\t{REFDP}\t{ALTDP}" \
                        .format(SMP=sample,
                                FT=row["gt_filters"][smpidx],
                                FREQ=row["gt_alt_freqs"][smpidx],
                                REFDP=row["gt_ref_depths"][smpidx],
                                ALTDP=row["gt_alt_depths"][smpidx])
                table_lines.append(sampleline)
        return table_lines

    def regular_lines(self):
        """Returns the lines with no changes"""
        table_lines = [self.header]
        for row in self.gq:
            table_lines.append(str(row))
        return table_lines
