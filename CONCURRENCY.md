# Concurrency model

이 문서는 현재 FastAPI 기반 PDF 병합 웹앱이 동시성을 어떻게 처리하는지를 요약합니다.

## 요청 단위 동작
- `/merge` 엔드포인트는 `async def merge_pdf`로 선언되어 있어 비동기 요청 처리를 지원합니다.【F:app/api/routes/merge.py†L13-L38】
- 각 요청마다 새로운 `PdfMergerService` 인스턴스를 생성하고, 업로드된 파일을 순차적으로 처리합니다.【F:app/api/routes/merge.py†L33-L38】
- `PdfMergerService.append_files`는 업로드된 파일들을 for 루프 안에서 하나씩 `await upload.read()`로 읽어들인 다음, `pypdf`를 사용해 페이지를 합치는 동기 로직을 수행합니다.【F:app/services/pdf_merger.py†L16-L35】
- PDF 파싱과 작성(`PdfReader`, `PdfWriter`)은 CPU 바운드이며 비동기화되어 있지 않으므로, 단일 병합 작업은 이벤트 루프에서 순차적으로 실행됩니다.【F:app/services/pdf_merger.py†L16-L39】

정리하면, 하나의 병합 작업은 내부적으로 멀티쓰레드/멀티프로세스를 사용하지 않고 단일 이벤트 루프에서 순차적으로 수행됩니다.

## 다중 요청 처리
- FastAPI 애플리케이션은 ASGI 서버(Uvicorn 등) 위에서 실행되며, 서버의 이벤트 루프가 동시에 여러 요청을 스케줄링합니다. 다만 이 레포지토리에서는 멀티프로세스 워커 설정이나 백그라운드 큐를 직접 구성하지 않았습니다.
- 각 요청은 독립적인 `PdfMergerService` 인스턴스를 사용하므로 공유 상태로 인한 동시성 문제는 없습니다.【F:app/api/routes/merge.py†L33-L38】
- 그러나 개별 요청의 PDF 병합 로직은 CPU 바운드 동기 코드이기 때문에, 단일 Uvicorn 워커 환경에서는 긴 병합 작업이 이벤트 루프를 점유하여 다른 요청의 처리 지연을 유발할 수 있습니다.

## 운영 시 고려 사항
- 동시에 많은 병합 작업을 처리해야 한다면 Uvicorn/Gunicorn과 같은 ASGI 서버에서 워커(프로세스) 수를 늘리거나, CPU 바운드 작업을 별도의 작업 큐/백그라운드 워커로 이동하는 것이 필요합니다.
- 또는 `PdfMergerService` 내부 로직을 멀티스레드/프로세스 풀에 위임하여 이벤트 루프가 블로킹되지 않도록 개선할 수 있습니다.
