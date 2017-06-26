import json
import numpy as np
from latticeproteins.interactions import miyazawa_jernigan
from latticegpm.utils import ConformationError
from latticegpm.thermo import fold_energy
from . import search

# use space enumeration
from gpmap.gpm import GenotypePhenotypeMap
from gpmap.binary import BinaryMap
from gpmap.utils import binary_mutations_map, mutations_to_genotypes

# ------------------------------------------------------
# Build a binary protein lattice model sequence space
# with fitness defined by function in Jesse Blooms'
# latticeproteins python package.
# ------------------------------------------------------

class LatticeGenotypePhenotypeMap(GenotypePhenotypeMap):
    """Construct a genotype-phenotype map from 2d protein lattice models. Genotypes
    are represented by

    Parameters
    ----------
    wildtype : str
        Wildtype sequence
    mutant : str
        Mutant sequence
    target_conf : str (optional)
        String that describes the target conformation to fold each sequence to.
    temperature : float
        temperature parameter for calculating folding stability.
    n_conformations : int
        number of conformations that should be in space (raise error if more)
    conformations : latticeproteins.conformations.Conformations object
        latticeproteins.conformations object for all conformations for
        strings with len(wildtype)

    Attributes
    ----------
    temperature : float
        temperature of the system
    target_conf : string
        target conformation for all sequences
    interaction_energies : dictionary
        mapping all contact pairs to their corresponding energies
    energies : array of floats
        native energies of all sequences
    stabilities : array of floats
        stabilities of native states for all sequences
    fitnesses : array of floats
        fitnesses of all sequences
    conformations : array of strings
        native conformations of all sequences
    partition_sum : array of float
        boltzmann weighted sum of all conformation/energies
    fold : boolean
        folded or not?

    For more attributes, see GenotypePhenotypeMap in `gpmap` package.
    """
    def __init__(self, wildtype,
        mutations,
        target_conf=None,
        temperature=1.0,
        phenotype_type="stabilities",
        interaction_energies=miyazawa_jernigan,
        **kwargs):
        # Construct a mutational mapping dictionary
        self.wildtype = wildtype
        self.mutations = mutations
        # Set initial properties of sequence space.
        self.interaction_energies = miyazawa_jernigan
        self.temperature = temperature
        self.target_conf = target_conf
        self.phenotype_type = phenotype_type
        # Initialize a phenotypes array.
        self.genotypes = mutations_to_genotypes(wildtype, mutations)
        # construct space.
        self._build()

    def fold(self, conf_list=None, Conformations=None):
        """Fold all genotypes and store info."""
        # Check if a custom partition function is given.
        self._nativeEs = np.empty(self.n, dtype=float)
        self._confs = np.empty(self.n, dtype="U" + str(self.length - 1))
        self._partition_sum = np.empty(self.n, dtype=float)
        self._folded = np.empty(self.n, dtype=bool)
        if conf_list is not None:
            self.recalculate_partition_sum(conf_list)
        elif Conformations is not None:
            # The slow step.
            self.Conformations = Conformations
            for i, g in enumerate(self.genotypes):
                output = self.Conformations.fold_sequence(g, self.temperature)
                self._nativeEs[i] = output[0]
                self._confs[i] = output[1]
                self._partition_sum[i] = output[2]
                self._folded[i] = output[3]
        else:
            raise Exception("Not to give conf_list or Conformations object")
        # Set the target conf if its given.
        if self.target_conf is not None:
            self.set_target_conf(self.target_conf)

    def _build(self):
        """Initialize attributes in space. useful for manual construction.
        """
        # Set some gpmap attrs
        self.log_transform = False
        self.n_replicates = None
        self.stdeviations = None
        # Construct a binary map for the lattice genotype-phenotype map.
        self.binary = BinaryMap(self, self.wildtype)

    def set_partition_confs(self, confs):
        """Manually set the conformations in the partition function. This is the
        same as manually defining the free energy landscape.
        """
        self.partition_confs_ = confs
        self.recalculate_partition_sum(confs)

    def set_target_conf(self, target_conf):
        """Set a target conformation as the native state for all genotypes in the
        maps. Recalculates nativeEs.
        """
        self.target_conf = target_conf
        for i in range(self.n):
            self._nativeEs[i] = fold_energy(self.genotypes[i], self.target_conf, self.interaction_energies)
            self.confs[i] = self.target_conf

    @property
    def phenotypes(self):
        """Get phenotypes specified by phenotype_type."""
        return getattr(self, self.phenotype_type)

    @property
    def confs(self):
        """Native conformations of lattice proteins in map."""
        return self._confs

    @property
    def folded(self):
        """Booleans stating the each genotype as folded or not."""
        return self._folded

    @property
    def partition_sum(self):
        """Partition sum for all lattice proteins in map."""
        return self._partition_sum

    @property
    def nativeEs(self):
        """Native energies for all lattice proteins in map."""
        return self._nativeEs

    @property
    def stabilities(self):
        """Folding stability for all lattice proteins in map."""
        return self.nativeEs + self.temperature * np.log(
            self._partition_sum - np.exp(-self.nativeEs/self.temperature))

    @property
    def fracfolded(self):
        """Fraction folded for all lattice proteins in map."""
        return 1 / (1 + np.exp(self.stabilities/self.temperature))

    @classmethod
    def from_length(cls, length, Conformations, target_conf=None, **kwargs):
        """Searches regions of sequences space for a lattice proteins
        with the given length on calculates their fitness.
        """
        seq1, seq2 = search.sequence_space(length, **kwargs)
        return cls.from_mutant(seq1, seq2, Conformations, target_conf=target_conf, **kwargs)

    @classmethod
    def from_mutant(cls, wildtype, mutant, Conformations, target_conf=None, **kwargs):
        """Create a binary genotype-phenotype map between a wildtype and mutant
        """
        mutations = binary_mutations_map(wildtype, mutant)
        self = cls(wildtype, mutations, target_conf=target_conf, **kwargs)
        self.fold(Conformations=Conformations)
        return self

    @classmethod
    def from_Lattice(cls, wt_lattice, mut_lattice, **kwargs):
        """Takes two ThermodynamicLattice proteins and constructs a genotype-phenotype map
        between them.
        """
        wildtype = wt_lattice.sequence
        mutant = mut_lattice.sequence
        # Construct a mutational mapping dictionary
        mutations = binary_mutations_map(wildtype, mutant)
        self = cls(wildtype, mutations, **kwargs)
        # construct space.
        self._build()
        self.fold(wt_lattice.conf_list)
        return self

    @classmethod
    def from_json(cls, filename, **kwargs):
        """Read a lattice genotype-phenotype map from json file.

        Keyword arguments will manually override elements in the json file.
        """
        # Open, json load, and close a json file
        f = open(filename, "r")
        data = json.load(f)
        f.close()
        # Grab all properties from data-structure
        necessary_args = ["wildtype","genotypes","nativeEs","partition_sum",
            "confs","folded","phenotype_type","temperature","mutations"]
        # check arguments
        for arg in necessary_args:
            if arg not in data:
                raise Exception(arg + " not in json.")
        # Update data with kwargs overridded by user
        data.update(**kwargs)
        # Create an instance
        gpm = cls.__new__(cls)
        for key, val in data.items():
            if type(val) == list:
                val = np.array(val)
            setattr(gpm, key, val)
        gpm._build()
        return gpm

    def to_json(self, filename):
        """Write lattice genotype-phenotype map to json file.
        """
        data = dict(
            wildtype=self.wildtype,
            genotypes=list(self.genotypes),
            nativeEs=list(self.nativeEs),
            partition_sum=list(self.partition_sum),
            confs=list(self.confs),
            folded=list([bool(f) for f in self.folded]),
            phenotype_type=self.phenotype_type,
            temperature=self.temperature,
            mutations=self.mutations
        )
        with open(filename, "w") as f:
            json.dump(data, f)

    @property
    def phenotype_type(self):
        """Set phenotype type. will be 'energies'|'stabilities'|'fitnesses'"""
        return self._phenotype_type

    @nativeEs.setter
    def nativeEs(self, nativeEs):
        """Set the native energies."""
        self._nativeEs = nativeEs

    @partition_sum.setter
    def partition_sum(self, partition_sum):
        """Set the partition sum."""
        self._partition_sum = partition_sum

    @confs.setter
    def confs(self, confs):
        """Set the conformations of each sequence."""
        self._confs = confs

    @folded.setter
    def folded(self, folded):
        """Set boolean for folded or not."""
        self._folded = folded

    @phenotype_type.setter
    def phenotype_type(self, phenotype_type):
        """Set phenotype type for this space. Must be 'energies'|'stabilities'|
        'fitnesses'
        """
        # Check for valid types
        types = ["nativeEs", "stabilities", "fracfolded"]
        if phenotype_type not in types:
            raise Exception(str(phenotype_type) + " is not a valid phenotype type.")
        else:
            self._phenotype_type = phenotype_type

    def recalculate_partition_sum(self, conf_list):
        """Recalculate the partition sum for all lattice proteins from a list of
        conformations. The conformation from the list with the lowest energy
        for each lattice protein is stored as its nativeE.

        Note that the partition conformations always include the E=0 state (unfolded).

        Parameters
        ----------
        conf_list : lists
            conformations to include in partition func for stability calculations.
        """
        # Set the partition function conformations as a attribute of the space.
        self.partition_confs = conf_list
        for i in range(self.n):
            # Sum over all conformations in z_conf for genotype i
            z = 0
            # The completely unfolded state is a possible configuration
            conf_energies = []
            min_conf = ""
            min_energy = 0
            fold = True
            for conf in conf_list:
                # Calculate folding energies of configuration
                fe = fold_energy(self.genotypes[i], conf, self.interaction_energies)
                # Add config to partition function
                z += np.exp(-fe/self.temperature)
                # Store this energie for latter
                conf_energies.append(fe)
                # Set the minimum energy.
                if fe < min_energy:
                    min_energy = fe
                    min_conf = conf
                    folded=True
                # If it's not a single lowest state, its nonnative.
                elif fe == min_energy:
                    folded=False
            self._partition_sum[i] = z
            # Set the native state if a target is not given
            if self.target_conf is None:
                # Set partition functions
                self._nativeEs[i] = min_energy
                self._folded[i] = folded
                self._confs[i] = min_conf

    def print_sequences(self, sequences):
        """ Print sequence conformation with/without ligand bound. """
        # Get the sequence to conformation mapping from `seqspace` machinery.
        seq2conf = self.get_map("genotypes", "confs")
        for s in sequences:
            PrintConformation(s, seq2conf[s])
