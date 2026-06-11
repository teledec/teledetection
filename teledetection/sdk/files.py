"""Work on files to update signed HREFs that may have expired."""

import os
import tempfile
import shutil
import re
import glob
from .logger import get_logger_for
from .signing import sign_string


log = get_logger_for(__name__)


URL_RE = (
    r"(?:http[s]?:\/\/.)?(?:www\.)?[-a-zA-Z0-9@%._\+~#=]"
    r"{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?;&\/\/=]*)"
)
AMP_STR_E = "&amp;"
AMP_STR = "&"


def update_href_in_string(contents: str, amp: bool) -> str:
    """Return the string with HREFs updated (signed)."""
    log.debug("Original contents: %s, ampersand: %s", contents, amp)

    def _sign_url(_in: str) -> str:
        """Sign an URL."""
        # QGIS typically save signed URLs replacing "&" with "&amp;"
        log.debug("signing URL %s", _in)
        _out = sign_string(url=_in.replace(AMP_STR_E, AMP_STR) if amp else _in)
        ret = _out.replace(AMP_STR, AMP_STR_E) if amp else _out
        log.debug("signed URL %s", _out)

        return ret

    return re.sub(URL_RE, lambda x: _sign_url(x.group()), contents)


def update_hrefs_in_file(filepath: str, amp: bool = False):
    """Sign all HREFs in the provided file (modified in place)."""
    log.debug("Reading file %s as text data", filepath)
    with open(filepath, "r", encoding="utf8") as file_handle:
        contents = update_href_in_string(contents=file_handle.read(), amp=amp)
        log.debug("Updated contents: %s", contents)
    log.debug("Writing file %s as text data", filepath)
    with open(filepath, "w", encoding="utf8") as file_handle:
        file_handle.write(contents)


def update_hrefs_in_qgz(filepath: str):
    """Sign all HREFs in the QGIS project file (modified in place)."""
    assert filepath.lower().endswith(".qgz"), "The QGIS project must be a .qgz file"

    with tempfile.TemporaryDirectory() as tmpdir:
        log.debug("Using temporary directory %s", tmpdir)
        log.debug("Decompressing QGIS project %s to %s", filepath, tmpdir)
        shutil.unpack_archive(filename=filepath, extract_dir=tmpdir, format="zip")
        extracted = glob.glob(os.path.join(tmpdir, "**/*"), recursive=True)
        log.debug("Extracted files: %s", "\n\t- ".join([] + extracted))
        matches = [file for file in extracted if file.lower().endswith(".qgs")]
        assert len(matches) == 1, f"Unable to read the QGIS project {filepath}"
        update_hrefs_in_file(filepath=matches[0], amp=True)
        log.debug("Replacing original QGIS project file")
        shutil.make_archive(filepath, format="zip", root_dir=tmpdir)
        shutil.move(f"{filepath}.zip", filepath)
