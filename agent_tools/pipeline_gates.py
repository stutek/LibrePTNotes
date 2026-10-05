"""`python -m agent_tools.pipeline_gates` — vsak CI posel res zapira objavo.

Zakaj: posel GitHub Actions, na katerega nič ne čaka (`needs`), še vedno teče in še vedno javi rdeče,
objavo pa ne ustavi. To je najslabša oblika kontrole: videti je zaupanja vrednejša kot nobena, rdeči
križec na strani teka pa se pokaže, medtem ko se izdaja zgodi. Ker delo teče neposredno na
`main`, je prav ta pot edino, kar prepreči, da bi pokvarjen potisk prišel na javno stran.

Invariante, ki jih preveri:

  1. **Natanko en končni posel**, vsi drugi v njegovem tranzitivnem `needs`: drugi končni posel je
     po definiciji tisti, na katerega nihče ne čaka.
  2. **Vsaka kontrola stopnje 1 teče v CI.** Zrcalna slika prvega: lokalna vrata brez koraka v poteku
     ustavijo commit, objave pa ne.
  3. **Vrstni red stopenj je tak kot v `build check`**, prebran iz `build/__init__.py`
     (`PIPELINE_STAGES`), da je deklariran enkrat, ne vzdrževan v dveh datotekah: posel, ki teče
     kontrole stopnje N, mora imeti vse posle stopnje N-1 v tranzitivnem `needs`.
  4. **Ime posla navaja stopnjo, ki jo res teče** (`Stage 2 · …`); posel brez stopnjnih kontrol ne
     sme trditi nobene.
  5. **Lokalno dejanje (`uses: ./…`) ne pred `actions/checkout`**: dejanje se bere iz delovnega
     prostora, zato ga checkout ne more vsebovati, in celotna napaka se pokaže šele na strežniku.

`build/__init__.py` se bere kot besedilo, ne uvozi: kontrola mora delovati na golem tolmaču in je ne
sme odvisna od tistega, kar preverja.
"""

import re
import sys
from pathlib import Path

import yaml

from agent_tools._tree import ROOT

STAGE_1_TABLE = re.compile(r"tasks = \{(.*?)\n    \}", re.S)
STAGE_1_TASK = re.compile(r'"[^"]+":\s*(run_[a-z_0-9]+)')
PIPELINE_STAGES_TABLE = re.compile(r"PIPELINE_STAGES = \((.*?)\n\)", re.S)
PIPELINE_STAGE_ROW = re.compile(r"\((\d+),\s*run_stage_[a-z_0-9]+,\s*\(([^)]*)\)\)")
STAGE_LABEL = re.compile(r"\s*Stage\s+(\d+)\s*[·:-]")


def load_workflow(path):
    """{posel: {needs, commands, name, steps}} za en potek."""
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    jobs = {}
    for name, body in (document.get("jobs") or {}).items():
        body = body or {}
        needs = body.get("needs") or []
        steps = body.get("steps") or []
        jobs[name] = {
            "needs": [needs] if isinstance(needs, str) else list(needs),
            "commands": " ".join(str(step.get("run", "")) for step in steps),
            "name": str(body.get("name", "")),
            "steps": steps,
        }
    return jobs


def closure_of(job, needs, seen=None):
    """Vsak posel, ki mora uspeti pred `job`."""
    seen = seen if seen is not None else set()
    for dependency in needs.get(job, []):
        if dependency not in seen:
            seen.add(dependency)
            closure_of(dependency, needs, seen)
    return seen


def orphans(needs):
    """(posli, ki ničesar ne zapirajo; vsi končni posli). Končni: nanje nihče ne čaka."""
    required = {dep for deps in needs.values() for dep in deps}
    terminals = sorted(set(needs) - required)
    if not terminals:
        return [], terminals
    primary = max(terminals, key=lambda job: len(closure_of(job, needs)))
    gated = closure_of(primary, needs) | {primary}
    return sorted(set(needs) - gated), terminals


def stage_1_tasks(build_text):
    """Funkcije `run_*`, iz katerih lokalna stopnja 1 sestavi svojo sodbo."""
    table = STAGE_1_TABLE.search(build_text)
    return set(STAGE_1_TASK.findall(table.group(1))) if table else set()


def stage_leaves(build_text):
    """{številka stopnje: kontrole `run_*`, ki jih drži}, iz `PIPELINE_STAGES`.

    Vrstica stopnje 1 je namenoma prazna (njene kontrole so v `tasks` tabeli); prazna vrstica ne sme
    prepisati prebranega, sicer stopnja 1 izgine iz urejanja in stopnja 2 se ne primerja z ničimer.
    """
    stages = {1: stage_1_tasks(build_text)}
    table = PIPELINE_STAGES_TABLE.search(build_text)
    if table:
        for number, tasks in PIPELINE_STAGE_ROW.findall(table.group(1)):
            declared = set(re.findall(r'"(run_[a-z_0-9]+)"', tasks))
            if declared:
                stages[int(number)] = declared
    return {number: tasks for number, tasks in stages.items() if tasks}


def stage_of_job(jobs, leaves):
    """{posel: najvišja stopnja, katere kontrole teče}."""
    found = {}
    for job, body in jobs.items():
        actual = [
            n
            for n, tasks in leaves.items()
            if any(re.search(rf"\b{t}\b", body["commands"]) for t in tasks)
        ]
        if actual:
            found[job] = max(actual)
    return found


def mislabelled_stages(jobs, leaves):
    """Posli, katerih prikazana stopnja ni stopnja, ki jo res tečejo."""
    actual_stage = stage_of_job(jobs, leaves)
    problems = []
    for job, body in sorted(jobs.items()):
        actual = actual_stage.get(job)
        label = STAGE_LABEL.match(body["name"])
        declared = int(label.group(1)) if label else None
        if actual is None and declared is not None:
            problems.append(
                f"'{job}' se imenuje Stage {declared}, a ne teče kontrol nobene stopnje"
            )
        elif actual is not None and declared is None:
            problems.append(
                f"'{job}' teče kontrole stopnje {actual}, a v imenu ni stopnje"
            )
        elif actual is not None and declared != actual:
            problems.append(
                f"'{job}' se imenuje Stage {declared}, a teče kontrole stopnje {actual}"
            )
    return problems


def out_of_order_stages(jobs, leaves):
    """Posli, katerih `needs` ne ponovi lokalnega vrstnega reda stopenj."""
    needs = {job: body["needs"] for job, body in jobs.items()}
    staged = stage_of_job(jobs, leaves)
    problems = []
    for job, stage in sorted(staged.items()):
        if stage <= 1:
            continue
        gated_by = closure_of(job, needs)
        for earlier, earlier_stage in sorted(staged.items()):
            if earlier_stage < stage and earlier not in gated_by:
                problems.append(
                    f"'{job}' (stopnja {stage}) ne počaka na '{earlier}' (stopnja {earlier_stage})"
                )
    return problems


def locally_gated_only(workflow_texts, build_text):
    """Kontrole stopnje 1, ki jih noben CI posel ne požene: vrata za commit, ne za objavo."""
    invoked = " ".join(workflow_texts)
    return sorted(task for task in stage_1_tasks(build_text) if task not in invoked)


def local_actions_before_checkout(jobs):
    """Posli, ki uporabijo lokalno `./` dejanje, preden se repozitorij prenese."""
    problems = []
    for name, body in jobs.items():
        checked_out = False
        for step in body["steps"]:
            uses = str(step.get("uses", ""))
            if uses.startswith("actions/checkout"):
                checked_out = True
            elif uses.startswith("./") and not checked_out:
                problems.append(f"posel '{name}' uporabi {uses} pred actions/checkout")
    return problems


def workflow_failures(rel, jobs, leaves):
    """Vsaka težava enega poteka, s potjo spredaj."""
    if not jobs:
        return []
    needs = {job: body["needs"] for job, body in jobs.items()}
    ungated, terminals = orphans(needs)
    failures = []
    if len(terminals) > 1:
        failures.append(
            f"{rel}: {len(terminals)} končnih poslov: {', '.join(terminals)}"
        )
    failures += [
        f"{rel}: posel '{job}' ničesar ne zapira (nihče ga ne našteje v `needs`)"
        for job in ungated
    ]
    failures += [
        f"{rel}: vrstni red stopenj ni zagotovljen: {p}"
        for p in out_of_order_stages(jobs, leaves)
    ]
    failures += [
        f"{rel}: napačna stopnja v imenu: {p}" for p in mislabelled_stages(jobs, leaves)
    ]
    failures += [
        f"{rel}: lokalno dejanje ni dosegljivo: {p}"
        for p in local_actions_before_checkout(jobs)
    ]
    return failures


def find_all(root=None):
    """(težave, število poslov, število kontrol stopnje 1, število stopenj)."""
    root = Path(root if root is not None else ROOT)
    build = root / "build" / "__init__.py"
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted([*workflow_dir.glob("*.yml"), *workflow_dir.glob("*.yaml")])
    if not build.exists():
        return (
            [
                "build/__init__.py ne obstaja: ni PIPELINE_STAGES, s katerim bi primerjali potek"
            ],
            0,
            0,
            0,
        )
    build_text = build.read_text(encoding="utf-8")
    leaves = stage_leaves(build_text)
    failures, job_count = [], 0
    for workflow in workflows:
        jobs = load_workflow(workflow)
        job_count += len(jobs)
        failures += workflow_failures(
            workflow.relative_to(root).as_posix(), jobs, leaves
        )
    if not failures:
        missing = locally_gated_only(
            [w.read_text(encoding="utf-8") for w in workflows], build_text
        )
        failures += [
            f"build.{task} zapira commit, objave pa ne: noben CI posel je ne požene"
            for task in missing
        ]
    if not workflows:
        failures.append(".github/workflows/ nima nobenega poteka")
    return failures, job_count, len(stage_1_tasks(build_text)), len(leaves)


def main(root=None):
    failures, jobs, stage_1, stages = find_all(root)
    if failures:
        print(f"\n  ✗ Vrata poteka: {len(failures)} težav\n")
        for failure in failures:
            print(f"    {failure}")
        print(
            "\n    Posel dodaj v `needs:` tistemu, kar mora nanj počakati. Kontrola, ki teče in ničesar ne\n"
            "    ustavi, je slabša od nobene: kaže rdeče, objava pa gre naprej. Lokalno dejanje potrebuje\n"
            "    `actions/checkout` kot prvi korak. Kontrola stopnje 1 brez koraka v CI pa je vrata, mimo\n"
            "    katerih se da potisniti."
        )
        return 1
    print(
        f"  ✓ Vrata poteka: {jobs} poslov, vsak zapira objavo; vseh {stage_1} kontrol stopnje 1 teče v CI; "
        f"{stages} stopenj je urejenih in poimenovanih kot lokalno."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
