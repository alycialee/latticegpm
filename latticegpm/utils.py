import itertools as it
# ------------------------------------------------------------
# Jesse Bloom's Lattice Model imports
# ------------------------------------------------------------
from latticeproteins.sequences import HammingDistance, RandomSequence

def search_conformation_space(Conformations, temperature, threshold, max_iter=1000):
    """ Randomly search the conformations landscape for two sequences that 
        fold with energy below some threshold and differ at all sites. 
        
        Args:
        ----
        Conformations: latticeproteins.conformations.Conformations object
            object that holds all the possible conformations to search.
        temperature: float
            Temperature parameter (ratio to kT)
        threshold: float
            Maximum allowed binding energy for landscape
        
        Returns:
        -------
        sequences: list of two strings
            List of two sequences that differ at all sites and fold.
    """
    length = Conformations.Length()
    counter = 0
    sequences = list()
    while len(sequences) < 2 and counter < max_iter:
        sequence = RandomSequence(length)
        output = Conformations.FoldSequence(sequence, temperature)
        energy = output[0]
        # Check that fitness value is above the threshold
        if energy < threshold:
            # Check Hamming distance once sequences list contains more than 2 sequences.
            if len(sequences) > 0:
                if HammingDistance(sequences[0], sequence) is length:
                    sequences.append("".join(sequence))
            else:
                sequences.append("".join(sequence))   
        counter +=1
    
    # Raise error if random search reaches maximum iterations
    if counter == max_iter:
        raise Exception("Random search reached max iterations before finding satisfying sequences.")
        
    return sequences

def search_fitness_landscape(Fitness, threshold, max_iter=1000):
    """ Randomly search the Fitness landscape for two sequences that 
        have non-zero fitnesses above threshold and differ at all sites. 
        
        Args:
        ----
        Conformations: latticeproteins.conformations.Conformations object
            object that holds all the possible conformations to search.
        temperature: float
            Temperature parameter (ratio to kT)
        threshold: float
            Maximum allowed binding energy for landscape
        
        Returns:
        -------
        sequences: list of two strings
            List of two sequences that differ at all sites and fold.
    """
    length = Fitness.Length()
    counter = 0
    sequences = list()
    while len(sequences) < 2 and counter < max_iter:
        sequence = RandomSequence(length)
        fitness = Fitness.Fitness(sequence)
        # Check that fitness value is above the threshold
        if fitness > threshold:
            # Check Hamming distance once sequences list contains more than 2 sequences.
            if len(sequences) > 0:
                if HammingDistance(sequences[0], sequence) is length:
                    sequences.append("".join(sequence))
            else:
                sequences.append("".join(sequence))   
        counter +=1
    
    # Raise error if random search reaches maximum iterations
    if counter == max_iter:
        raise Exception("Random search reached max iterations before finding satisfying sequences.")
        
    return sequences

def generate_binary_space(wildtype, mutant):
    """ Build a list of sequences that represent all binary combinations of the wildtype 
        and mutant sequence. Systematically flips all sites in the wildtype sequence, 
        mutating towards the mutant.
    
        Args:
        ----
        wildtype: str
            Wildtype sequence
        mutant: str
            Mutant sequence that differs at all sites from wildtype
    """
    
    # Check that wildtype and mutant are the same length
    if len(wildtype) != len(mutant):
        raise IndexError("ancestor_sequence and derived sequence must be the same length.")
    
    # Check that sequences differ at all sites.    
    if HammingDistance(wildtype, mutant) != len(wildtype):
        raise Exception("Wildtype and mutant must differ at all sites.")

    # Build a binary representation
    binaries = sorted(["".join(list(s)) for s in it.product('01', repeat=len(wildtype))])
    sequence_space = list()
    for b in binaries:
        binary = list(b)
        sequence = list()
        # Use binary representation to build all binary-mutants 
        for i in range(len(wildtype)):
            if b[i] == '0':
                sequence.append(wildtype[i])
            else:
                sequence.append(mutant[i])
        sequence_space.append(''.join(sequence))
    return sequence_space
