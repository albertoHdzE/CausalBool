"""Frozen explicit quadratic-row contract; no gadget semantics here."""
from dataclasses import dataclass, field
import hashlib
import json
import re
from . import FIELD_PRIME

@dataclass(frozen=True)
class LinearExpression:
    constant: int = 0
    terms: dict[str, int] = field(default_factory=dict)

    def to_dict(self):
        if type(self.constant) is not int or any(type(v) is not int for v in self.terms.values()):
            raise ValueError('integer coefficients required')
        return {'constant': str(self.constant), 'terms': {k: str(v) for k,v in sorted(self.terms.items()) if v}}

@dataclass(frozen=True)
class QuadraticConstraint:
    A: LinearExpression
    B: LinearExpression
    C: LinearExpression
    label: str

    def to_dict(self):
        return {**{k: getattr(self,k).to_dict() for k in ('A','B','C')}, 'label': self.label}

@dataclass
class ConstraintSystem:
    prime: int = FIELD_PRIME
    public_inputs: list[str] = field(default_factory=list)
    private_inputs: list[str] = field(default_factory=list)
    auxiliary_signals: list[str] = field(default_factory=list)
    constraints: list[QuadraticConstraint] = field(default_factory=list)

    @property
    def signals(self):
        return self.public_inputs + self.private_inputs + self.auxiliary_signals

    def validate(self):
        if self.prime != FIELD_PRIME:
            raise ValueError('challenge constraint field required')
        if len(set(self.signals)) != len(self.signals) or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',s) for s in self.signals):
            raise ValueError('unique valid signal names required')
        names=set(self.signals)
        for row in self.constraints:
            for e in (row.A,row.B,row.C):
                if not set(e.terms)<=names:
                    raise ValueError('unknown signal')
                e.to_dict()
        return self

    def to_dict(self):
        self.validate()
        return {'version':'oxparc-r1cs-v1','prime':str(self.prime), 'public_inputs':self.public_inputs,
                'private_inputs':self.private_inputs, 'auxiliary_signals':self.auxiliary_signals,
                'constraints':[r.to_dict() for r in self.constraints]}

    def to_json(self):
        return json.dumps(self.to_dict(),sort_keys=True,separators=(',',':'))

    def structural_hash(self):
        return hashlib.sha256(self.to_json().encode()).hexdigest()


def canonical(value, prime=FIELD_PRIME):
    if type(value) is not int or not 0 <= value < prime:
        raise ValueError('canonical integer field representative required')
    return value
