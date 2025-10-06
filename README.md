# FastAPI PDF 병합기

[English README](README.EN.md)

FastAPI PDF 병합기는 여러 개의 PDF 문서와 JPG/PNG 이미지를 하나의 PDF 파일로 합치는 웹 애플리케이션이자 API입니다. 드래그 앤 드롭이 가능한 브라우저 UI, 파일별 페이지 범위와 레이아웃 옵션을 지원하는 `/merge` 엔드포인트, 자체 호스팅 환경에 적합한 업로드 제한 설정 기능을 제공합니다.

## 주요 기능

- **반응형 웹 UI**: Jinja2 템플릿으로 제공되는 홈 화면(`/`)에서 PDF와 JPG/PNG 이미지를 함께 병합할 수 있습니다.
- **REST API**: `POST /merge` 엔드포인트는 여러 PDF, JPG 또는 PNG 파일을 받고, 파일별 페이지 범위와 레이아웃 옵션(용지 크기, 방향, 맞춤 방식, 회전)을 JSON으로 지정할 수 있습니다.
- **업로드 안전장치**: 총 업로드 용량 제한, 파일 확장자 및 빈 파일 검사, 암호화 여부 확인, 잘못된 JSON 입력 검증 등을 통해 안정적인 요청 처리를 보장합니다.
- **API 키 보호**: `PDF_MERGER_API_KEY`(또는 호환되는 별칭)가 설정된 경우 `/merge` 엔드포인트 접근을 제한합니다.
- **상태 확인**: `/health` 엔드포인트로 모니터링 시스템과 연동할 수 있습니다.
- **동시성 제어**: AnyIO capacity limiter를 사용하여 대용량 문서 병합 시 CPU 급증을 방지합니다.

## 시작하기

### 요구 사항

- Python 3.11 이상
- [PyPDF](https://pypdf.readthedocs.io/) 및 선택적으로 [pikepdf](https://pikepdf.readthedocs.io/)가 필요로 하는 시스템 패키지

Python 의존성을 설치하려면 다음 명령을 실행하세요.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 환경 변수 구성

필수는 아니지만 다음 환경 변수를 통해 동작을 조정할 수 있습니다.

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `PDF_MERGER_API_KEY` | `/merge` 엔드포인트 접근에 필요한 API 키. 별칭: `API_KEY`. | _없음_ (키 요구 비활성화) |
| `PDF_MERGER_MAX_TOTAL_UPLOAD_MB` | 요청당 허용되는 총 업로드 용량(MB). 별칭: `MAX_MB`. | `200` |
| `PDF_MERGE_MAX_PARALLEL` | 백그라운드 병합 작업의 최대 동시 실행 개수. 별칭: `MERGE_MAX_PARALLEL`. | _제한 없음_ |

이 변수들은 프로젝트 루트의 `.env` 파일에 정의해도 됩니다.

### 서버 실행

Uvicorn으로 FastAPI 애플리케이션을 로컬에서 실행하려면 다음 명령을 사용하세요.

```bash
uvicorn app.main:app --reload
```

Reverse proxy 등 구성 시 아래와 같은 식으로 실행할 수도 있습니다.
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
```

기본적으로 UI는 <http://127.0.0.1:8000/> 에서, API 엔드포인트는 `/merge`, 헬스 체크는 `/health`에서 이용할 수 있습니다.

## API 사용법

`POST /merge`

- **files**: 하나 이상의 PDF, JPG 또는 PNG 파일을 `files` 멀티파트 필드로 전송합니다. 파일은 비어 있거나 암호화되어서는 안 됩니다.
- **ranges**: (선택) 각 파일에 대응하는 페이지 범위를 문자열 목록(JSON)으로 전달합니다. 예: `["1-3,5",""]`
- **options**: (선택) 파일별 레이아웃을 지정하는 객체 목록(JSON). `paper_size`, `orientation`, `fit_mode`, `rotation`(`rotate90`, `rotate180`, `rotate270`)을 지원합니다.
- **output_name**: (선택) 결과 PDF 파일 이름. 기본값은 `merged.pdf`입니다.
- **engine**: (선택) 처리 백엔드. 기본은 `pypdf`, 설치되어 있다면 `pikepdf`를 사용할 수 있습니다.

엔드포인트는 병합된 PDF를 스트리밍 응답으로 반환하며, 검증 실패 시 명확한 HTTP 상태 코드와 함께 오류를 제공합니다.

## 개발 참고

- 정적 자산은 `app/static/`, 템플릿은 `app/templates/`에 위치합니다.
- 병합 로직은 `app/services/pdf_merger.py`에 구현되어 있습니다.
- API 라우트는 `app/api/routes/` 아래에 정리되어 있습니다.

필요에 따라 타입 검사나 테스트를 실행할 수 있습니다. (기본 제공되는 자동화 테스트 스위트는 없습니다.)

## 라이선스

이 프로젝트는 [GNU Affero General Public License v3.0 (AGPLv3)](https://www.gnu.org/licenses/agpl-3.0.html)의 적용을 받습니다. 네트워크를 통해 이 애플리케이션을 제공하는 경우 라이선스가 요구하는 대로 동일한 소스 코드를 제공해야 합니다.
