"""Contains classes for handling the presets.config yaml file and constructing
gemini queries."""
from __future__ import print_function
import re
import yaml
import config

class Presets(object):
    """Reads preset options from the supplied config file"""
    def __init__(self, presets_config):
        if presets_config:
            with open(presets_config, 'r') as presets_input:
                try:
                    presets = yaml.load(presets_input)
                except yaml.YAMLError, exc:
                    print("Error loading presets config file.")
                    raise exc
        else:
            presets = config.DEFAULT_PRESETS
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
        transcripts = " OR ".join(["transcript == '" + transcript + "'"
            for transcript in transcripts])
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
        if self.args_dict["genes"]:
            genefilter = "(" + "' OR ".join("gene == '" + gene for gene in self.args_dict["genes"].split(',')) + "')"
            returnfilter += " AND {}".format(genefilter)
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
        if self.args_dict["check_undrrover"]:
            # If the check undrrover flag is set add the UR fields
            returnfields += ", vep_undrrover_sample, vep_undrrover_pct, " \
                            "vep_undrrover_nv, vep_undrrover_np"
        return returnfields

    def get_predefined_filter(self):
        """Translates simple arguments to predefined where queries."""
        # Filter blocks
        # SQL filter blocks that can be combined to build query filters
        # Transcripts to include and genes to ignore the vep_pick for (those with given transcripts)
        exclude = self.presets_o.format_transcripts("genes")
        include = self.presets_o.format_transcripts("transcripts")
        # Variant filter block
        variant_filter = "(filter IS NULL)"
        # Vep pick block
        vep_pick = "(vep_pick == 1)"
        # LoF block
        lof = "(impact = 'frameshift_variant' OR  " \
              "impact = 'stop_gained' OR  " \
              "impact = 'splice_donor_variant' OR  " \
              "impact = 'splice_acceptor_variant' OR  " \
              "is_lof = 1)"
        # BRCA Exchange pathogenic block
        brcaex_pathogenic = "(vep_brcaex_clinical_significance_enigma == 'Pathogenic')"
        # ATM c.7271T>G block
        atm_7271 = "(vep_hgvsc == 'NM_000051.3:c.7271T>G')"
        # Clinically reportable genes / ATM c.7271T>G
        reportable_genes = "(gene == 'BRCA1' OR gene == 'BRCA2' OR gene == 'TP53' OR " \
                           "vep_hgvsc == 'NM_000051.3:c.7271T>G' OR gene == 'PALB2')"

        # Combining blocks to create filters (make sure they're surrounded by brackets so
        # they play nice with user filters)
        standard = "((({exclude} AND {vep_pick}) OR {include}))".format(
            include=include,
            exclude=exclude,
            vep_pick=vep_pick)
        lof = "({std} AND {lof})".format(
            std=standard,
            lof=lof)
        lof_pathogenic = "({std} AND ({lof} OR {brcaex}))".format(
            std=standard,
            lof=lof,
            brcaex=brcaex_pathogenic)
        reportable = "({std} AND {rep_genes} AND ({lof_path} OR {atm_7271}))".format(
            std=standard,
            rep_genes=reportable_genes,
            lof_path=lof_pathogenic,
            atm_7271=atm_7271)

        # Instantiating the dictionary
        translation_dictionary = {
            "standard": standard,
            "lof": lof,
            "lof_pathogenic": lof_pathogenic,
            "reportable": reportable
        }
        where_filter = translation_dictionary[self.args_dict["presetfilter"]]
        # Returning the preset filter string
        return where_filter


class QueryProcessing(object):
    """Takes the output of a gemini query and processes it for output"""
    def __init__(self, gq):
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

    def flattened_lines_ur(self):
        """Flattens the output to one line per sample and appends sample genotype info
        and UNDRROVER concordance info"""
        flat_hdr = '\t'.join(self.header.split('\t')[:-7]) + \
            "\tSample\tGT Filter\tAlt Frequency\tRef Depth\tAlt Depth\t" \
            "IN UNDRROVER\tUR PCT\tUR NP\tUR PASS"
        table_lines = [flat_hdr]
        for row in self.gq:
            samples = row["variant_samples"]  # Getting the variant samples as a list
            conc_samples, conc_pct, ur_dict = self.check_undrrover(row) # Getting undr rover info
            for sample in samples:
                ur_sample = re.sub(r'_S\d+', '', sample)
                ur_pct = ur_dict[ur_sample]["pct"] if ur_sample in ur_dict else 0.0
                ur_np = ur_dict[ur_sample]["np"] if ur_sample in ur_dict else 0
                ur_pass = "TRUE" if ur_sample in ur_dict and ur_dict[ur_sample]["PASS"] else "FALSE"
                in_ur = "TRUE" if ur_sample in ur_dict else "FALSE"
                smpidx = self.smptoidx[sample]
                sampleline = '\t'.join(str(row).split('\t')[:-7]) + \
                    "\t{SMP}\t{FT}\t{FREQ}\t{REFDP}\t{ALTDP}\t{IUR}\t{URPCT}\t{URNP}\t{URPASS}" \
                        .format(SMP=sample,
                                FT=row["gt_filters"][smpidx],
                                FREQ=row["gt_alt_freqs"][smpidx],
                                REFDP=row["gt_ref_depths"][smpidx],
                                ALTDP=row["gt_alt_depths"][smpidx],
                                IUR=in_ur,
                                URPCT=ur_pct,
                                URNP=ur_np,
                                URPASS=ur_pass)
                table_lines.append(sampleline)
        return table_lines

    def regular_lines(self):
        """Returns the lines with no changes"""
        table_lines = [self.header]
        for row in self.gq:
            output_line = str(row)
            table_lines.append(output_line)
        return table_lines

    def regular_lines_ur(self):
        """Returns the lines with no changes, UNDR ROVER concordance added"""
        # Deleting UNDR ROVER columns by index
        header = self.header.split('\t')
        del header[-7:-3]
        header = '\t'.join(header)
        table_lines = [header + "\tUNDR-ROVER Concordance\tConcordant Samples"]
        for row in self.gq:
            output_line = str(row).split('\t')
            del output_line[-7:-3]
            output_line = '\t'.join(output_line)
            conc_samples, conc_pct, ur_dict = self.check_undrrover(row)
            output_line += "\t{pct}\t{smpl}".format(pct=conc_pct, smpl=', '.join(conc_samples))
            table_lines.append(output_line)
        return table_lines

    def check_undrrover(self, row):
        """Takes a gemini line containing UNDR ROVER and sample information and returns concordance
        metrics"""
        # GATK samplelist (removing _S123 to match UNDR ROVER)
        gatk_samples = [re.sub(r'_S\d+', '', s) for s in row["variant_samples"]]
        # Getting UNDR ROVER information
        ur_samples = row["vep_undrrover_sample"].split('&')
        # Check for empty sample list (if empty the first element will be an empty string)
        if not ur_samples[0]:
            return [], 0.00, {}
        ur_pct = row["vep_undrrover_pct"].split('&')
        ur_nv = row["vep_undrrover_nv"].split('&')
        ur_np = row["vep_undrrover_np"].split('&')
        # Storing the UR metrics for each UR sample (assuming ordered lists)
        ur_dict = {}
        for n in range(0, len(ur_samples)):
            # Checking to see if the call passes in this sample
            # Currently (greater than 25% and minimum 25 pairs coverage (DP of 50))
            if float(ur_pct[n]) > 25.0 and int(ur_np[n]) > 25:
                PASS = True
            else:
                PASS = False
            ur_dict[ur_samples[n]] = {
                "pct": float(ur_pct[n]),
                "nv": int(ur_nv[n]),
                "np": int(ur_np[n]),
                "PASS": PASS
            }
        # Calculating metrics
        gatk_set = set(gatk_samples)
        ur_pass_set = set([s for s in ur_dict if ur_dict[s]["PASS"]])
        conc_samples = gatk_set.intersection(ur_pass_set) if ur_pass_set else set()
        conc_pct = float(len(conc_samples)) / float(len(gatk_set))
        # Returning concordant samples (high confidence) the percentage and the metrics dictionary
        return conc_samples, conc_pct, ur_dict
