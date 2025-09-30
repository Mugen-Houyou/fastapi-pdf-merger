# Concurrency model

이 문서는 현재 FastAPI 기반 PDF 병합 웹앱이 동시성을 어떻게 처리하는지를 요약합니다.

## 요청 단위 동작
- `/merge` 엔드포인트는 `async def merge_pdf`로 선언되어 있어 비동기 요청 처리를 지원합니다.【F:app/api/routes/merge.py†L13-L38】
- 각 요청마다 새로운 `PdfMergerService` 인스턴스를 생성하고, 업로드된 파일을 순차적으로 처리합니다.【F:app/api/routes/merge.py†L33-L38】
- `PdfMergerService.append_files`는 업로드된 파일을 비동기적으로 읽어 메모리에 담은 뒤, 페이지 병합 로직을 스레드 풀에서 실행합니다.【F:app/services/pdf_merger.py†L18-L66】
- PDF 파싱과 작성(`PdfReader`, `PdfWriter`)은 CPU 바운드이지만, 별도 스레드에서 수행되기 때문에 이벤트 루프는 다음 요청을 계속 처리할 수 있습니다.【F:app/services/pdf_merger.py†L44-L66】
## 다중 요청 처리
- FastAPI 애플리케이션은 ASGI 서버(Uvicorn 등) 위에서 실행되며, 서버의 이벤트 루프가 동시에 여러 요청을 스케줄링합니다.
- 각 요청은 독립적인 `PdfMergerService` 인스턴스를 사용하므로 공유 상태로 인한 동시성 문제는 없습니다.【F:app/api/routes/merge.py†L33-L38】
- PDF 병합 로직은 `anyio.to_thread`를 사용해 전용 스레드 풀에서 실행되며, 이벤트 루프는 I/O 작업(파일 업로드 수신 등)에 집중할 수 있습니다.【F:app/services/pdf_merger.py†L18-L69】
- 동시에 수행 가능한 병합 스레드 수는 루트 디렉터리의 `.env` 파일에 정의된 `PDF_MERGE_MAX_PARALLEL` 값으로 제한할 수 있으며, 값이 없으면 CPU 코어 수를 기준으로 자동 설정됩니다.【F:app/core/concurrency.py†L1-L27】【F:app/services/pdf_merger.py†L60-L69】

## 운영 시 고려 사항
- 스레드 풀에서 CPU 바운드 병합 작업을 실행하므로 단일 워커 환경에서도 다른 요청에 대한 응답 지연이 완화됩니다.【F:app/services/pdf_merger.py†L18-L69】
- `.env` 파일의 `PDF_MERGE_MAX_PARALLEL` 설정을 통해 스레드 풀 동시 실행 수를 조정하여, 서버 자원과 예상 동시 요청량에 맞춰 안정적으로 운영할 수 있습니다.【F:app/core/concurrency.py†L1-L27】
- 여전히 CPU 사용량이 높은 작업이므로, 대규모 트래픽 환경에서는 Uvicorn/Gunicorn 워커 수 확장이나 별도의 작업 큐 도입을 고려하는 것이 좋습니다.
