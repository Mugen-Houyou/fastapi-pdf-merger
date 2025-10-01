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
            "hero_description": "Combine multiple PDF files into a single document and control the order and page ranges with ease.",
            "drop_instruction": "Drop PDF files here or click to browse",
            "drop_detail": "Your files will stay on this device until you choose to merge them.",
            "upload_limit_note": "You can upload up to {limit} MB in total.",
            "empty_state": "No files added yet. Add PDFs above to configure their ranges.",
            "output_label": "Output filename",
            "api_key_label": "API key",
            "api_key_placeholder": "Optional - only if required",
            "engine_label": "Processing engine",
            "engine_pypdf": "PyPDF (pure Python)",
            "engine_pikepdf": "pikepdf (fast C++ backend)",
            "paper_size_label": "Paper size",
            "paper_size_a4": "A4",
            "paper_size_letter": "U.S. Letter",
            "orientation_label": "Orientation",
            "orientation_portrait": "Portrait",
            "orientation_landscape": "Landscape",
            "scale_mode_label": "Scale mode",
            "scale_mode_letterbox": "Letterbox (contain)",
            "scale_mode_crop": "Crop (cover)",
            "merge_button": "💕 Merge PDFs",
            "reverse_button": "Reverse order",
            "clear_button": "Clear files",
            "range_hint_html": "Page range example: <code>1-3,5</code> (leave empty for entire file)",
            "range_placeholder": "Page ranges e.g. 1-3,5",
        },
        "client": {
            "buttons": {
                "merge": "💕 Merge PDFs",
                "merging": "Merging…",
                "clear": "Clear files",
                "remove": "Remove",
                "reverse": "Reverse order",
            },
            "messages": {
                "empty": "No files added yet. Add PDFs above to configure their ranges.",
                "pdf_only": "Only PDF files are supported.",
                "cleared": "Cleared selected files.",
                "select_one": "Select at least one PDF.",
                "merging": "Merging PDFs…",
                "merging_progress": "Merging PDFs… {size}",
                "merged": "Merged successfully! Your download should begin automatically.",
                "merge_failed": "Failed to merge PDFs.",
                "failed_prefix": "Failed: {message}",
                "reordered": "Reversed file order.",
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
            "hero_description": "여러 PDF 파일을 자유롭게 커스터마이즈하여 하나의 문서로 합치세요.",
            "drop_instruction": "여기에 PDF 파일을 끌어오거나 클릭하여 선택하세요",
            "drop_detail": "파일은 병합을 선택할 때까지 이 기기에만 머무릅니다.",
            "upload_limit_note": "총 {limit}MB까지 업로드할 수 있습니다.",
            "empty_state": "아직 추가된 파일이 없습니다. 위에서 PDF를 추가해 범위를 설정하세요.",
            "output_label": "출력 파일 이름",
            "api_key_label": "API 키",
            "api_key_placeholder": "선택 사항 - 필요한 경우에만 입력",
            "engine_label": "처리 엔진",
            "engine_pypdf": "PyPDF (순수 파이썬)",
            "engine_pikepdf": "pikepdf (고속 C++ 백엔드)",
            "paper_size_label": "용지 크기",
            "paper_size_a4": "A4",
            "paper_size_letter": "U.S. 레터",
            "orientation_label": "방향",
            "orientation_portrait": "세로",
            "orientation_landscape": "가로",
            "scale_mode_label": "배치 방식",
            "scale_mode_letterbox": "레터박스(전체 보기)",
            "scale_mode_crop": "크롭(채우기)",
            "merge_button": "💕 PDF 병합",
            "reverse_button": "순서 거꾸로",
            "clear_button": "전체 목록 지우기",
            "range_hint_html": "페이지 범위 예시: <code>1-3,5</code> (비워두면 전체 페이지)",
            "range_placeholder": "페이지 범위 예: 1-3,5",
        },
        "client": {
            "buttons": {
                "merge": "💕 PDF 병합",
                "merging": "병합 중…",
                "clear": "전체 목록 지우기",
                "remove": "삭제",
                "reverse": "순서 거꾸로",
            },
            "messages": {
                "empty": "아직 추가된 파일이 없습니다. 위에서 PDF를 추가해 범위를 설정하세요.",
                "pdf_only": "PDF 파일만 지원합니다.",
                "cleared": "선택한 파일을 지웠습니다.",
                "select_one": "최소 한 개의 PDF를 선택하세요.",
                "merging": "PDF 병합 중…",
                "merging_progress": "PDF 병합 중… {size}",
                "merged": "병합이 완료되었습니다! 다운로드가 자동으로 시작됩니다.",
                "merge_failed": "PDF 병합에 실패했습니다!",
                "failed_prefix": "실패: {message}",
                "reordered": "파일 순서를 거꾸로 정렬했습니다.",
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

