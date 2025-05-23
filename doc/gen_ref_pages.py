"""Generate the code reference pages."""

from pathlib import Path

import mkdocs_gen_files

for path in sorted(Path("teledetection").rglob("*.py")):  #
    module_path = path.relative_to(".").with_suffix("")  #
    doc_path = path.relative_to(".").with_suffix(".md")  #
    full_doc_path = Path("reference", doc_path)  #

    parts = list(module_path.parts)

    if parts[-1] == "__init__":  #
        parts = parts[:-1]
    elif parts[-1] == "__main__":
        continue

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:  #
        IDENTIFIER = ".".join(parts)  #
        print("::: " + IDENTIFIER)
        print("::: " + IDENTIFIER, file=fd)  #

    mkdocs_gen_files.set_edit_path(full_doc_path, path)
