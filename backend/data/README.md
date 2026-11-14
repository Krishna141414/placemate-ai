# Sample data

**Everything in this folder is fictional sample data written for this project.** The college (Kaveri Ridge Institute of Technology), every company, every student, every interview write-up, and every phone number, email and address are invented. Any resemblance to a real organisation or person is accidental.

| Path | Contents | Indexed for search |
|---|---|---|
| `placement_policy.md` | Placement policy of the fictional college | yes |
| `companies/` | 12 company profiles with job descriptions. The YAML block at the top of each file holds the criteria that the eligibility and resume tools read. | yes |
| `interviews/` | 15 interview experiences written as if by seniors | yes |
| `guides/` | 6 preparation guides | yes |
| `students_seed.json` | Demo student profiles used by the seed script | no |
| `resumes/` | Demo resumes as plain text (they contain fake contact details on purpose, so PII redaction has something to remove) | no |
| `fixtures/` | A document with a planted instruction line, used only by the prompt-injection tests and the Security page demo | no |

## Front matter

Company files:

```yaml
id: nimbusware                  # unique slug
name: Nimbusware Technologies
doc_type: company
role: Software Engineer Trainee
ctc_lpa: [6.5, 8.0]             # min, max in lakh per annum
min_cgpa: 7.0
max_active_backlogs: 1
allowed_branches: [CSE, IT, ECE]
batch: 2027
required_skills: [python, sql, data structures]
preferred_skills: [django, git, rest api]
rounds: [Online Assessment, Technical Interview, HR Interview]
apply_by: 2026-12-05
```

Interview files use `doc_type: interview`, `title`, `company_id`. Guides use `doc_type: guide`, `title`. The policy uses `doc_type: policy`, `title`.
