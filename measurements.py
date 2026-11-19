"""Original Excel column definitions. All dates refer to the source's 2013 headers.

Data only: no claim about site replicates, experimental blocks or genetics.
"""
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class Measurement:
    column: str
    disease: str
    site: str
    stage: str
    series: str
    date: str
    label: str
    date_source: str = "source header"

# Explicit mapping prevents confusing seedling 0–9 scores with adult 0–100% severity.
MEASUREMENTS = [
    Measurement('F','Yellow rust','KALRO-Njoro','seedling','KALRO-Njoro seedlings','2013-03-26','Mar 26','Excel serial 41359'),
    Measurement('G','Yellow rust','KALRO-Njoro','seedling','KALRO-Njoro seedlings','2013-09-12','Sep 12','Excel serial 41529'),
    Measurement('I','Yellow rust','KARI-Njoro','adult','Njoro Apr–May','2013-04-21','Apr 21'),
    Measurement('J','Yellow rust','KARI-Njoro','adult','Njoro Apr–May','2013-04-30','Apr 30'),
    Measurement('K','Yellow rust','KARI-Njoro','adult','Njoro Apr–May','2013-05-07','May 7'),
    Measurement('L','Yellow rust','KARI-Njoro','adult','Njoro Sep–Oct','2013-09-25','Sep 25'),
    Measurement('M','Yellow rust','KARI-Njoro','adult','Njoro Sep–Oct','2013-10-03','Oct 3'),
    Measurement('O','Yellow rust','Meraro','adult','Meraro Aug–Nov','2013-08-10','Aug 10'),
    Measurement('P','Yellow rust','Meraro','adult','Meraro Aug–Nov','2013-10-18','Oct 18'),
    Measurement('Q','Yellow rust','Meraro','adult','Meraro Aug–Nov','2013-10-28','Oct 28'),
    Measurement('R','Yellow rust','Meraro','adult','Meraro Aug–Nov','2013-11-09','Nov 9'),
    Measurement('T','Yellow rust','Jeldu','adult','Jeldu Aug–Dec','2013-08-13','Aug 13'),
    Measurement('U','Yellow rust','Jeldu','adult','Jeldu Aug–Dec','2013-11-20','Nov 20'),
    Measurement('V','Yellow rust','Jeldu','adult','Jeldu Aug–Dec','2013-12-16','Dec 16'),
    Measurement('Y','Stem rust','KARI-Njoro','seedling','Njoro stem seedlings','2013-03-26','Mar 26','Excel serial 41359'),
    Measurement('Z','Stem rust','KARI-Njoro','seedling','Njoro stem seedlings','2013-09-12','Sep 12','Excel serial 41529'),
    Measurement('AA','Stem rust','KARI-Njoro','adult','Njoro stem Apr–May','2013-04-21','Apr 21'),
    Measurement('AB','Stem rust','KARI-Njoro','adult','Njoro stem Apr–May','2013-04-30','Apr 30'),
    Measurement('AC','Stem rust','KARI-Njoro','adult','Njoro stem Apr–May','2013-05-07','May 7'),
    Measurement('AD','Stem rust','EIAR-Debre Zeit','adult','Debre Zeit stem Apr–Jun','2013-04-26','Apr 26','Excel serial 41390'),
    Measurement('AE','Stem rust','EIAR-Debre Zeit','adult','Debre Zeit stem Apr–Jun','2013-05-10','May 10','Excel serial 41404'),
    Measurement('AF','Stem rust','EIAR-Debre Zeit','adult','Debre Zeit stem Apr–Jun','2013-06-03','Jun 3','Excel serial 41428'),
    Measurement('AG','Stem rust','Jeldu','adult','Jeldu stem Dec','2013-12-16','Dec 16'),
    Measurement('AH','Leaf rust','Jeldu','adult','Jeldu leaf Dec','2013-12-16','Dec 16'),
    Measurement('AK','Leaf rust','KARI-Njoro','adult','Njoro leaf Apr–May','2013-04-21','Apr 21'),
    Measurement('AL','Leaf rust','KARI-Njoro','adult','Njoro leaf Apr–May','2013-04-30','Apr 30'),
    Measurement('AM','Leaf rust','KARI-Njoro','adult','Njoro leaf Apr–May','2013-05-07','May 7'),
    Measurement('AN','Leaf rust','EIAR-Debre Zeit','adult','Debre Zeit leaf Apr–May','2013-04-26','Apr 26','Excel serial 41390'),
    Measurement('AO','Leaf rust','EIAR-Debre Zeit','adult','Debre Zeit leaf Apr–May','2013-05-10','May 10','Excel serial 41404'),
]

def as_records():
    return [asdict(m) for m in MEASUREMENTS]
