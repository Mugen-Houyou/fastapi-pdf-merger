"""Utility helpers for simple server- and client-side translations."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Request


# Supported locale codes for the application.
SUPPORTED_LOCALES = ("en", "ko")


# Translation catalogues. Keep template-facing strings under the ``template`` key
# and strings that must be available to client-side code under ``client``.
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    "en": {
        "template": {
            "page_title": "PDF Merger",
            "hero_title": "PDF Merger",
            "hero_description": "Combine multiple PDF documents and JPG images into a single file and control the order and page ranges with ease.",
            "drop_instruction": "Drop PDF or JPG files here or click to browse",
            "drop_detail": "Your files will stay on this device until you choose to merge them.",
            "upload_limit_note": "You can upload up to {limit} MB in total.",
            "empty_state": "No files added yet. Add files above to configure their ranges.",
            "output_label": "Output filename",
            "api_key_label": "API key",
            "api_key_placeholder": "Optional - only if required",
            "engine_label": "Processing engine",
            "engine_pypdf": "PyPDF (pure Python)",
            "engine_pikepdf": "pikepdf (fast C++ backend)",
            "paper_size_label": "Paper size",
            "paper_size_auto": "Auto",
            "paper_size_a4": "A4",
            "paper_size_letter": "U.S. Letter",
            "orientation_label": "Orientation",
            "orientation_auto": "Auto",
            "orientation_portrait": "Portrait",
            "orientation_landscape": "Landscape",
            "orientation_rotate90": "Rotate 90°",
            "orientation_rotate180": "Rotate 180°",
            "orientation_rotate270": "Rotate 270°",
            "scale_mode_label": "Scale mode",
            "scale_mode_auto": "Auto",
            "scale_mode_letterbox": "Letterbox (contain)",
            "scale_mode_crop": "Crop (cover)",
            "global_controls_title": "Apply to all files",
            "global_controls_description": "Changes here update every uploaded file. You can still fine-tune each one below.",
            "merge_button": "💕 Merge to PDF",
            "reverse_button": "Reverse order",
            "clear_button": "Clear files",
            "range_hint_html": "Page range example: <code>1-3,5</code> (leave empty for entire file)",
            "range_placeholder": "Page ranges e.g. 1-3,5",
        },
        "client": {
            "buttons": {
                "merge": "💕 Merge to PDF",
                "merging": "Merging…",
                "clear": "Clear files",
                "remove": "Remove",
                "reverse": "Reverse order",
            },
            "messages": {
                "empty": "No files added yet. Add files above to configure their ranges.",
                "pdf_only": "Only PDF or JPG files are supported.",
                "cleared": "Cleared selected files.",
                "select_one": "Select at least one file.",
                "merging": "Merging files…",
                "merging_progress": "Merging files… {size}",
                "merged": "Merged successfully! Your download should begin automatically.",
                "merge_failed": "Failed to merge files.",
                "failed_prefix": "Failed: {message}",
                "reordered": "Reversed file order.",
                "confirm_remove": "Are you sure you want to remove this file?",
                "confirm_clear": "Are you sure you want to clear all files?",
            },
            "aria": {
                "drag_handle": "Drag {name} to reorder",
                "remove": "Remove {name}",
            },
            "placeholders": {
                "range": "Page ranges e.g. 1-3,5",
            },
            "labels": {
                "range": "Page ranges",
                "paper_size": "Paper size",
                "orientation": "Orientation",
                "fit_mode": "Scale mode",
            },
            "options": {
                "paper_size": {
                    "auto": "Auto",
                    "A4": "A4",
                    "Letter": "Letter",
                },
                "orientation": {
                    "auto": "Auto",
                    "portrait": "Portrait",
                    "landscape": "Landscape",
                    "rotate90": "Rotate 90°",
                    "rotate180": "Rotate 180°",
                    "rotate270": "Rotate 270°",
                },
                "fit_mode": {
                    "auto": "Auto",
                    "letterbox": "Letterbox (contain)",
                    "crop": "Crop (cover)",
                },
            },
        },
    },
    "ko": {
        "template": {
            "page_title": "PDF 병합기",
            "hero_title": "PDF 병합기",
            "drop_instruction": "PDF 또는 JPG 파일을 드래그앤드롭하거나 클릭하여 업로드하세요.",
            "upload_limit_note": "총 {limit}MB까지 업로드할 수 있습니다.",
            "empty_state": "아직 추가된 파일이 없습니다. 위에서 파일을 추가하세요.",
            "output_label": "출력 파일 이름",
            "api_key_label": "API 키",
            "api_key_placeholder": "필요한 경우에만 입력",
            "engine_label": "처리 엔진",
            "engine_pypdf": "PyPDF (순수 파이썬)",
            "engine_pikepdf": "pikepdf (고속 C++ 백엔드)",
            "paper_size_label": "용지 크기",
            "paper_size_auto": "자동",
            "paper_size_a4": "A4",
            "paper_size_letter": "U.S. 레터",
            "orientation_label": "방향",
            "orientation_auto": "자동",
            "orientation_portrait": "세로",
            "orientation_landscape": "가로",
            "orientation_rotate90": "90도 회전",
            "orientation_rotate180": "180도 회전",
            "orientation_rotate270": "270도 회전",
            "scale_mode_label": "배치 방식",
            "scale_mode_auto": "자동",
            "scale_mode_letterbox": "레터박스(전체 보기)",
            "scale_mode_crop": "크롭(채우기)",
            "global_controls_title": "전체 파일 일괄 적용",
            "global_controls_description": "업로드된 모든 파일에 일괄적으로 적용됩니다. ",
            "merge_button": "💕 PDF로 병합",
            "reverse_button": "순서 거꾸로",
            "clear_button": "전체 목록 지우기",
            "range_hint_html": "페이지 범위 예시: <code>1-3,5</code> (비워두면 전체 페이지)",
            "range_placeholder": "페이지 범위 예: 1-3,5",
        },
        "client": {
            "buttons": {
                "merge": "💕 PDF로 병합",
                "merging": "병합 중…",
                "clear": "전체 목록 지우기",
                "remove": "삭제",
                "reverse": "순서 거꾸로",
            },
            "messages": {
                "empty": "아직 추가된 파일이 없습니다. 위에서 파일을 추가하세요.",
                "pdf_only": "PDF 또는 JPG 파일만 지원합니다.",
                "cleared": "선택한 파일을 지웠습니다.",
                "select_one": "최소 한 개의 파일을 선택하세요.",
                "merging": "파일 병합 중…",
                "merging_progress": "파일 병합 중… {size}",
                "merged": "병합이 완료되었습니다! 다운로드가 자동으로 시작됩니다.",
                "merge_failed": "파일 병합에 실패했습니다!",
                "failed_prefix": "실패: {message}",
                "reordered": "파일 순서를 거꾸로 정렬했습니다.",
                "confirm_remove": "이 파일을 삭제하시겠습니까?",
                "confirm_clear": "전체 목록을 지우시겠습니까?",
            },
            "aria": {
                "drag_handle": "{name}를 드래그하여 순서를 변경",
                "remove": "{name} 삭제",
            },
            "placeholders": {
                "range": "페이지 범위 예: 1-3,5",
            },
            "labels": {
                "range": "페이지 범위",
                "paper_size": "용지 크기",
                "orientation": "방향",
                "fit_mode": "배치 방식",
            },
            "options": {
                "paper_size": {
                    "auto": "자동",
                    "A4": "A4",
                    "Letter": "U.S. 레터",
                },
                "orientation": {
                    "auto": "자동",
                    "portrait": "세로",
                    "landscape": "가로",
                    "rotate90": "90도 회전",
                    "rotate180": "180도 회전",
                    "rotate270": "270도 회전",
                },
                "fit_mode": {
                    "auto": "자동",
                    "letterbox": "레터박스(전체 보기)",
                    "crop": "크롭(채우기)",
                },
            },
        },
    },
}


def detect_locale(request: Request) -> str:
    """Determine the preferred locale based on the ``Accept-Language`` header."""

    accept_language = request.headers.get("accept-language", "")
    for item in accept_language.split(","):
        lang = item.split(";")[0].strip().lower()
        if not lang:
            continue
        for locale in SUPPORTED_LOCALES:
            if lang.startswith(locale):
                return locale
    return "en"


def get_translations(locale: str) -> Dict[str, Any]:
    """Return translation dictionaries for the requested locale with fallback."""

    if locale not in TRANSLATIONS:
        locale = "en"
    return TRANSLATIONS.get(locale, TRANSLATIONS["en"])

