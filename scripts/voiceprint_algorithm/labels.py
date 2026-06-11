"""Label registry for the 9-class voiceprint demo dataset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabelInfo:
    folder: str
    label: str
    is_fault: bool
    fault_type: str


CLASS_INFOS: tuple[LabelInfo, ...] = (
    LabelInfo("供水管道泄漏声纹", "供水管道泄漏声纹", True, "管廊供水管路泄漏"),
    LabelInfo("供气管道泄漏声纹", "供气管道泄漏声纹", True, "管廊输气线路泄漏"),
    LabelInfo("供电线路泄漏声纹", "供电线路泄漏声纹", True, "管廊供电线路失效"),
    LabelInfo("脚步声纹", "巡检脚步声纹", False, "现场环境声"),
    LabelInfo("排风机声纹", "排风机声纹", False, "现场环境声"),
    LabelInfo(
        "供水管道泄漏与供气管道泄漏组合声纹",
        "供水管道泄漏与供气管道泄漏组合声纹",
        True,
        "管廊供水管路泄漏与输气线路泄漏组合",
    ),
    LabelInfo(
        "供水管道泄漏与供电线路泄漏组合声纹",
        "供水管道泄漏与供电线路泄漏组合声纹",
        True,
        "管廊供水管路泄漏与供电线路失效组合",
    ),
    LabelInfo(
        "供气管道泄漏和供电线路泄漏组合声纹",
        "供气管道泄漏与供电线路泄漏组合声纹",
        True,
        "管廊输气线路泄漏与供电线路失效组合",
    ),
    LabelInfo(
        "供水管道泄漏&供气管道泄漏和供电线路泄漏组合声纹",
        "供水管道泄漏与供气管道泄漏与供电线路泄漏组合声纹",
        True,
        "管廊供水管路泄漏与输气线路泄漏与供电线路失效组合",
    ),
)

CLASS_FOLDERS: tuple[str, ...] = tuple(info.folder for info in CLASS_INFOS)
CLASS_LABELS: tuple[str, ...] = tuple(info.label for info in CLASS_INFOS)

_BY_FOLDER = {info.folder: info for info in CLASS_INFOS}
_BY_LABEL = {info.label: info for info in CLASS_INFOS}


def canonical_label(folder_or_label: str) -> str:
    """Return the display label for a dataset folder name or label."""

    if folder_or_label in _BY_FOLDER:
        return _BY_FOLDER[folder_or_label].label
    if folder_or_label in _BY_LABEL:
        return folder_or_label
    raise KeyError(f"Unknown voiceprint class: {folder_or_label}")


def label_info(label: str) -> LabelInfo:
    """Return metadata for a canonical label."""

    canonical = canonical_label(label)
    return _BY_LABEL[canonical]
