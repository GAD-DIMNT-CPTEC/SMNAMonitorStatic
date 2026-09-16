"""Public names and stable storage IDs; old CLI/index names remain compatible."""
ALIASES = {'SMNA-FN': 'SMNA-FNCEP', 'SMNA-FC': 'SMNA-FINPE',
           'SMNA-FNCEP': 'SMNA-FNCEP', 'SMNA-FINPE': 'SMNA-FINPE'}
STORAGE_IDS = {'SMNA-FNCEP': 'smna-fn', 'SMNA-FINPE': 'smna-fc'}

def canonical_environment(value):
    try:
        return ALIASES[value]
    except KeyError:
        raise ValueError('Ambiente deve ser SMNA-FNCEP ou SMNA-FINPE') from None
