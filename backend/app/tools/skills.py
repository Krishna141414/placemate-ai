"""Skill vocabulary and extraction.

A skill has a canonical name (the form used in company files), a set of
patterns that recognise it in free text, and optionally skills it implies
("MySQL" implies "SQL"). Extraction is plain pattern matching: predictable,
explainable, and the same every time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Skill:
    name: str
    patterns: tuple[str, ...]
    implies: tuple[str, ...] = field(default_factory=tuple)


def _word(term: str) -> str:
    """Pattern for a term with word boundaries that respect +, # and dots."""
    return rf"(?<![\w+#.]){term}(?![\w+#])"


SKILLS: tuple[Skill, ...] = (
    # Languages
    Skill("python", (_word("python"),)),
    Skill("java", (_word("java"),)),
    Skill("javascript", (_word("javascript"), _word("js"), _word("ecmascript"))),
    Skill("typescript", (_word("typescript"), _word("ts")), ("javascript",)),
    Skill("c", (_word("c"), r"(?<![\w+#.])c programming")),
    Skill("c++", (r"(?<![\w+#.])c\+\+(?![\w+#])", _word("cpp"))),
    Skill("embedded c", (r"embedded\s+c(?![\w+#])",), ("c",)),
    Skill("go", (_word("golang"),)),
    Skill("kotlin", (_word("kotlin"),)),
    Skill("bash", (_word("bash"), r"shell scripting")),
    Skill("matlab", (_word("matlab"),)),
    # Web and backend
    Skill("html", (_word("html5?"),)),
    Skill("css", (_word("css3?"), _word("tailwind"))),
    Skill("react", (_word("react(?:\\.js|js)?"),), ("javascript",)),
    Skill("django", (_word("django"),), ("python",)),
    Skill("flask", (_word("flask"),), ("python",)),
    Skill("spring boot", (r"spring\s*boot",), ("java",)),
    Skill("node.js", (r"(?<![\w.])node(?:\.js|js)?(?![\w])",), ("javascript",)),
    Skill("rest api", (r"rest(?:ful)?\s*api", r"(?<![\w])restful(?![\w])", r"rest\s+services?")),
    Skill("microservices", (r"micro-?services?",)),
    Skill("redis", (_word("redis"),)),
    # Data
    Skill("sql", (_word("sql"), r"window functions?")),
    Skill("mysql", (_word("mysql"),), ("sql",)),
    Skill("postgresql", (_word("postgres(?:ql)?"),), ("sql",)),
    Skill("sqlite", (_word("sqlite"),), ("sql",)),
    Skill("mongodb", (_word("mongo(?:db)?"),)),
    Skill("dbms", (_word("dbms"), r"database management", r"normali[sz]ation", r"acid propert")),
    Skill("excel", (_word("excel"), r"vlookup", r"pivot tables?")),
    Skill("power bi", (r"power\s*bi",)),
    Skill("tableau", (_word("tableau"),)),
    Skill("pandas", (_word("pandas"),), ("python",)),
    Skill("numpy", (_word("numpy"),), ("python",)),
    Skill("statistics", (_word("statistics"), _word("statistical"), r"probability")),
    Skill("machine learning", (r"machine learning", _word("ml"), r"scikit-?learn", _word("sklearn"))),
    Skill("pytorch", (_word("pytorch"), _word("torch")), ("machine learning",)),
    Skill("tensorflow", (_word("tensorflow"), _word("keras")), ("machine learning",)),
    # CS fundamentals
    Skill("data structures", (r"data\s+structures?", _word("dsa"))),
    Skill("algorithms", (_word("algorithms?"), _word("dsa"), r"dynamic programming", r"dijkstra")),
    Skill("object oriented programming", (r"object[\s-]+oriented", _word("oops?"))),
    Skill("operating systems", (r"operating systems?",)),
    Skill("system design", (r"system design", r"low[\s-]level design", r"high[\s-]level design")),
    # Infra and tools
    Skill("git", (_word("git"), _word("github"), _word("gitlab"))),
    Skill("linux", (_word("linux"), _word("ubuntu"), r"unix")),
    Skill("networking", (_word("networking"), r"computer networks?", r"tcp/ip", _word("subnetting"))),
    Skill("aws", (_word("aws"), r"amazon web services", _word("ec2"))),
    Skill("docker", (_word("docker"), r"containeri[sz]")),
    Skill("kubernetes", (_word("kubernetes"), _word("k8s"))),
    Skill("web security", (r"web security", r"application security", r"owasp")),
    Skill("owasp", (_word("owasp"),)),
    # Electronics and embedded
    Skill("microcontrollers", (r"micro-?controllers?", _word("arduino"), _word("esp32"), _word("8051"), r"arm cortex")),
    Skill("digital electronics", (r"digital electronics", r"digital circuits?", r"logic gates?")),
    Skill("iot", (_word("iot"), r"internet of things")),
    Skill("mqtt", (_word("mqtt"),)),
    Skill("rtos", (_word("rtos"), _word("freertos"))),
    Skill("i2c", (_word("i2c"),)),
    Skill("spi", (_word("spi"),)),
    Skill("uart", (_word("uart"),)),
    # Mechanical and civil
    Skill("autocad", (_word("autocad"),)),
    Skill("solidworks", (_word("solidworks"),)),
    Skill("ansys", (_word("ansys"),)),
    Skill("thermodynamics", (_word("thermodynamics"),)),
    Skill("manufacturing processes", (r"manufacturing process(?:es)?", r"manufacturing")),
    Skill("six sigma", (r"six\s+sigma", r"lean manufacturing")),
    # General
    Skill("aptitude", (_word("aptitude"), r"quantitative", r"logical reasoning")),
    # Not the branch name "Electronics and Communication (Engineering)".
    Skill("communication", (r"(?<!and )(?<!& )\bcommunication\b(?! engineering)", r"public speaking", r"presentation skills")),
)

_BY_NAME = {skill.name: skill for skill in SKILLS}
_COMPILED = [(skill, [re.compile(pattern, re.IGNORECASE) for pattern in skill.patterns]) for skill in SKILLS]


def known_skill(name: str) -> bool:
    return name in _BY_NAME


def extract_skills(text: str) -> set[str]:
    """Canonical names of every skill mentioned in the text."""
    if not text:
        return set()
    found = {skill.name for skill, patterns in _COMPILED if any(p.search(text) for p in patterns)}
    # Close over implications ("react" -> "javascript").
    queue = list(found)
    while queue:
        for implied in _BY_NAME[queue.pop()].implies:
            if implied not in found:
                found.add(implied)
                queue.append(implied)
    return found
