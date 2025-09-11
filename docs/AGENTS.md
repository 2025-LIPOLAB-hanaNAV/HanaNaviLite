---

# 0) 큰 그림

* **레이어**

  1. UI: Home, Chat, (옵션) Board, Docs, Admin
  2. BFF/API: `/files`, `/conversations`, `/chat/stream`, `/board/*`
  3. 파이프라인: Parse → Chunk → Embed → Index (Vector/Hybrid)
  4. Retriever: attachments / library / org 스코프 + BM25+Dense 하이브리드
  5. LLM Orchestrator: 컨텍스트 구성, 출처 강제, 스트리밍 토큰

* **전개 전략**

  * **Phase 1**: 게시판 없이 **단일 RAG 챗봇**(첨부 업로드 → 파싱/색인 → 대화)
  * **Phase 2**: 게시판 컴포넌트 연동(리스트/상세/작성/수정) + **게시글/첨부 자동 수집**
  * **Phase 3**: 관리/관측(헬스/잡/로그), 권한/RBAC, 개인 라이브러리 고도화

---

# 1) 라우팅 & 페이지(프론트)

* **필수**

  * `/` **Home**: 프리셋/검색 → `/chat` 이동
  * `/chat` **Chat**: 메시지, 첨부(여러 파일), 스트리밍 응답, Evidence 패널
  * `/docs/:docId` **Document Viewer**: evidence 클릭 시 원문 미리보기
* **옵션(게시판 준비 전 컴포넌트만)**

  * `/board` **BoardList** (목업 API 연동)
  * `/board/:postId` **BoardView**
  * `/board/new|:postId/edit` **BoardForm**
* **운영**

  * `/admin` **Admin**: 헬스·잡 목록(파싱/색인 작업), 간단 로그

> 게시판은 **컴포넌트/라우트만 우선 배치**하고, 데이터는 목업(MSW) 또는 임시 JSON으로 연결 → 나중에 실제 포털 API/크롤러가 완성되면 data source만 교체.

---

# 2) 컴포넌트 계약(프론트)

* **ChatComposer**

  * props: `conversationId`
  * emits: `onSend(text, attachmentIds[])`
  * 내부: `useAttachments(convId)` 훅(로컬 상태 유지 + `/files/{id}/status` 폴링)
* **MessageList**

  * props: `messages[]` (stream delta 반영)
* **EvidencePanel**

  * props: `evidences[]` (`{docId, fileId, title, page, score}`)
  * 클릭 → `/docs/:docId?page=...`
* **DocumentViewer**

  * props: `docId, page?` → 서버에서 텍스트/미리보기 URL 로드
* **Board*(List/View/Form)* (스텁)\*\*

  * 데이터 소스 분리: `BoardDataProvider`(mock/real 교체)
* **Admin/Jobs**

  * `/admin/jobs` 목록에 parse/embed/index 작업 상태 표시

---

# 3) API 계약(백엔드/BFF)

## Capabilities

```
GET /capabilities
→ { chat:{stream:true}, upload:{maxSizeMB:20, accept:["pdf","docx","png","jpg"]}, limits:{filesPerMessage:5} }
```

## Files (첨부 & 파이프라인 상태)

```
POST /files?scope=session|library&conversationId=...
(form-data: file)
→ { fileId, name, size, mime, scope, status:"UPLOADED" }

GET /files/{fileId}/status
→ { fileId, status:"UPLOADED|PARSING|INDEXED|FAILED", pages?, error? }

POST /files/{fileId}/promote
{ scope:"library" } → { ok:true }
```

## Conversations & Messages

```
POST /conversations
{ title? } → { conversationId }

POST /conversations/{id}/messages
{
  role:"user",
  text:string,
  attachmentFileIds?: string[],
  options?: { retrievalScope?: "attachments"|"library"|"all", topK?: number }
}
→ { messageId, text, evidences:[{docId,fileId,title,page,score}] }
```

## Streaming

```
GET /chat/stream?conversationId=...&messageId=...
data: {"delta":"..."}     # 토큰
data: {"evidences":[...]} # 완료 직전 1회
data: [DONE]
```

## Board (스텁 → 실제로 대체)

```
GET /board/posts?query=&page=
GET /board/posts/:postId
POST /board/posts
PUT  /board/posts/:postId
DELETE /board/posts/:postId

# 게시글 첨부(있다면)
GET /board/posts/:postId/attachments
```

## Admin

```
GET /admin/health → { ok, services:{llm,retriever,indexer,storage}, latencyMs:{...} }
GET /admin/jobs   → { items:[{id,type:"parse|embed|index",status,fileId,startedAt,endedAt}] }
```

---

# 4) 데이터 모델(요지)

* **files**: `file_id`, `user_id`, `scope(session|library)`, `conversation_id?`, `name`, `mime`, `size`, `status`, `hash_sha256`, `created_at`
* **documents**: `doc_id`, `file_id`, `page_count`, `meta(json)`
* **chunks**: `chunk_id`, `doc_id`, `page`, `text`, `offset`, `meta(json)`
* **embeddings**: `chunk_id`, `vector`, `index_name`
* **conversations**: `conversation_id`, `user_id`, `title`, `created_at`
* **messages**: `message_id`, `conversation_id`, `role`, `text`, `attachment_file_ids(json)`, `created_at`

**Vector Collections**

* `conversation:{convId}` (대화 첨부 전용, 휘발/TTL)
* `user:{userId}:library` (개인 보관, 비휘발)
* `org:{orgId}:public` (공지/정책 등 공용)

---

# 5) 파이프라인 & 검색

1. **업로드 큐 → 파싱 → 청크 → 임베딩 → 색인**

   * PDF/이미지 OCR, 표 슬라이싱(표 인식 시 셀 단위 청크 별도)
   * 중복 방지: SHA-256 기준 dedupe → 이미 존재 시 색인 스킵/alias

2. **Retrieval 스코프**

   * 기본 `attachments`: `conversation:{convId}`만
   * `library`: 개인 라이브러리
   * `all`: attachments + library (+ org 공용)

3. **랭킹**

   * BM25(문서 텍스트) + Dense(임베딩) **late fusion**
   * 카테고리/게시판(나중에) 신뢰도 가중치 부여 가능

4. **LLM 컨텍스트 구성**

   * 상위 k 청크 + 메타(문서명·페이지·원문 링크)
   * 프롬프트에 “반드시 출처(docId/page) 포함” 명시

---

# 6) 게시판 연동 설계(나중에 바로 붙도록)

* **Board Ingestor**(별도 워커):

  1. `GET /board/posts`로 목록 수집(또는 사내 API/크롤러)
  2. 각 `postId` 세부 + 첨부 목록 로드
  3. 첨부는 파일 처리 파이프라인으로 **재사용**(files → documents → chunks → embeddings)
  4. “게시글 본문 텍스트”도 문서로 색인(게시판 컬렉션 태그: `board:{boardId}`)

* **스키마 정합**: 게시판이 완성되면 **BoardDataProvider**만 실제 API로 교체

* **권한**: 게시판 ACL을 가져와 문서 스코프에 반영(유저/조직/팀 단위)

---

# 7) 프런트 개발 팁(버그 회피)

* **첨부 유지 버그 해결**:

  * 첨부 리스트는 **로컬 상태**로 유지하고 메시지 전송 후 지우지 않음
  * 파일 상태만 `/files/{id}/status`로 주기 동기화
  * 동일 대화에서 **재질의** 시 기존 첨부를 그대로 사용

* **폼/업로드 UX**:

  * 다중 업로드, 진행률(가능하면), 상태 배지(UPLOADED/PARSING/INDEXED)
  * 실패(FAILED) 시 재시도 버튼 노출 → `/admin/jobs`에도 보임

* **스트리밍**:

  * `EventSource`로 토큰 누적 표시
  * 완료 직전에 `evidences` 1회 수신 → EvidencePanel 갱신

---

# 8) “단일 RAG 챗봇” 독립 동작 체크(게시판 없이)

* 파일 업로드 → 상태 `INDEXED`
* 질문 전송(스코프: `attachments`) → 스트리밍 응답
* EvidencePanel에서 문서 클릭 → `/docs/:docId` 미리보기
* `/admin/health` 정상, `/admin/jobs`에 파싱/색인 기록 보임

> 이 4단계가 돌아가면 **게시판 없이도 MVP 완성**. 이후 Board Ingestor만 붙이면 “게시판 + 첨부 RAG”가 자동 확장.

---

# 9) 테스트 플로우(필수 6가지)

1. **단일 파일 RAG**: 업로드→색인→질문→evidence에 해당 파일/페이지가 포함되는가
2. **여러 파일**: 특정 파일 내용만 묻기 → 그 파일이 우선 검색되는가
3. **전송 후 첨부 보존**: 메시지 전송 후 첨부 UI가 사라지지 않는가
4. **OCR/표**: 이미지/PDF 표 캡처에서도 텍스트/셀 추출이 되는가(최소 샘플)
5. **스코프 전환**: attachments vs library vs all 결과 차이가 명확한가
6. **에러/재시도**: FAILED → 재시도 후 INDEXED로 전환되는가(워커/잡 동작)

---

# 10) 마이그레이션 & 운영

* **기존 API 재사용**:

  * `/chat`에 `attachmentFileIds[]` 추가 → 스코프 제한 검색 적용
  * 기존 업로드 API는 응답에 `fileId/status`만 추가해도 프론트 즉시 대응 가능
* **관측성**: `/admin/health`·`/admin/jobs`·간단 로그(요청/지연/토큰)
* **보안/RBAC**: 사용자/조직 스코프, 서명 URL(다운로드), 데이터 보존 정책

---

원하면 위 지침을 **코드 스캐폴드**(FastAPI 라우트/워커 스텁, React 라우팅/훅)까지 바로 풀어 쓸게.
특정 선택지(예: pgvector vs FAISS, Celery vs RQ/Arq, React Router 여부)가 정해져 있다면 알려줘—그에 맞춰 구체 코드로 내릴게!


아래 지침은 **기존 프론트/백엔드를 활용**하면서,

* 게시판 기능은 아직 완성되지 않았지만 **컴포넌트만 먼저 만들어 두고**,
* 게시판 없이도 **단일 RAG 챗봇**으로 동작할 수 있도록 설계하는 방법을 제시합니다.

---

## 🔧 1. 아키텍처 개요

### 핵심 모듈

* **챗 UI / API** – 사용자가 질문을 입력하고, 답변을 스트리밍으로 받으며, 근거(evidence)를 확인.
* **첨부파일 파이프라인** – 업로드된 파일을 저장 → 텍스트 추출(OCR 포함) → 청크 분할 → 임베딩 생성 → 벡터DB에 저장.
* **게시판 인제스터(Board Ingestor)** – 게시판이 완료되면 게시글과 첨부를 주기적으로 수집하여 파이프라인으로 전달.
* **하이브리드 검색** – 첨부파일, 개인 라이브러리, 게시판 문서 중 적절한 스코프에서 BM25 + 벡터 검색을 결합.

### 단계별 전개

1. **MVP**: 게시판 없이 첨부파일 업로드 → RAG 검색 → 답변 스트리밍.
   게시판 UI는 모킹 데이터로 컴포넌트만 구현해 두고, 실제 API 연결은 나중에.
2. **게시판 완성 후**: Board Ingestor로 실제 게시글/첨부를 수집·색인하고, 검색 스코프에 게시판을 추가.
3. **고도화**: 관리 콘솔/권한 관리, 조직별 스코프, 추가 검색 옵션 등을 확장.

---

## 🧱 2. 백엔드 지침 (FastAPI 예시)

1. **파일 업로드 및 상태 확인**

   ```http
   POST /files?scope=session|library&conversationId=...
     └ form-data: file → { fileId, status:"UPLOADED" }
   GET  /files/{fileId}/status → { status:"UPLOADED|PARSING|INDEXED|FAILED" }
   ```

   * 업로드 후 파싱/색인을 비동기 워커로 처리하고 상태를 갱신합니다.
   * `scope=session`은 대화 한정, `library`는 개인 라이브러리로 저장.

2. **대화 관리**

   ```http
   POST /conversations → { conversationId }
   POST /conversations/{id}/messages
     └ { role:"user", text, attachmentFileIds:[...], options:{retrievalScope:"attachments|library|all"} }
     → { messageId, text, evidences:[{docId,fileId,page,score}] }
   ```

   * `attachmentFileIds` 목록을 넘기면 지정된 파일의 청크만 우선 검색합니다.
   * 답변은 스트리밍(`/chat/stream?conversationId=...&messageId=...`)으로 전달할 수 있습니다.

3. **게시판 API(선개발용 모킹)**

   ```http
   GET /board/posts?query=&page=…        # 리스트
   GET /board/posts/{postId}             # 상세
   POST /board/posts                     # 새 게시글 작성
   PUT /board/posts/{postId}             # 수정
   DELETE /board/posts/{postId}          # 삭제
   GET /board/posts/{postId}/attachments # 게시글 첨부
   ```

   * 실제 게시판 백엔드가 준비되기 전에는 목업 데이터 제공자(`BoardDataProvider`)로 대체합니다.
   * 게시판 완성 후에는 API 경로만 실제 포털 API로 교체합니다.

4. **게시판 인제스터**

   * 정해진 인터벌로 `/board/posts` 목록과 상세를 가져와, 첨부파일은 기존 파일 파이프라인으로 전송하고, 본문은 텍스트 문서로 저장·색인합니다.
   * 게시글과 첨부파일을 수집할 때 게시글의 접근 권한(사내 보안)을 반영하여 저장 스코프를 설정합니다.

5. **검색 스코프**

   * 기본: `attachments` – 현재 대화에 업로드한 파일에서 검색
   * `library`: 사용자의 개인 라이브러리
   * `board:{boardId}` – 특정 게시판 문서만
   * `all`: 첨부 + 라이브러리 + 게시판 + 조직 공용
   * BM25와 Dense 임베딩의 late fusion 랭킹을 적용해 최종 후보를 선택합니다.

---

## 🎨 3. 프론트엔드 지침 (React 예시)

1. **라우팅**

   * `/` → **Home** (프리셋/검색)
   * `/chat` → **Chat**
   * `/docs/:docId` → **Document Viewer**
   * `/board` 및 `/board/:postId` → 게시판 컴포넌트 (목업 데이터 사용)
   * `/admin` → 관리 콘솔(옵션)

2. **첨부파일 UI**

   * 텍스트 입력창 옆에 파일 아이콘을 두어 여러 파일을 선택할 수 있게 합니다.
   * 업로드된 파일 리스트와 상태(`UPLOADED/PARSING/INDEXED/FAILED`)를 표시하고, 메시지 전송 후에도 리스트를 유지합니다.
   * 프론트에서는 로컬 state로 파일 목록을 저장하고 `/files/{id}/status`를 폴링하여 서버 상태를 갱신합니다.

3. **게시판 컴포넌트**

   * `BoardList`는 목업 API로 게시글 목록을 보여주고, 검색·필터·페이지네이션을 제공합니다.
   * `BoardView`는 제목·본문·작성자·날짜·첨부파일 링크를 표시하고, 첨부를 다운로드/미리보기하는 기능을 추가합니다.
   * 게시판 완성 후에는 `BoardDataProvider`의 URL만 실제 API로 바꿔도 동작합니다.

4. **Evidence Panel & Document Viewer**

   * 챗 페이지에서 답변에 사용된 문서 리스트(evidence)를 우측 패널로 표시합니다.
   * 클릭하면 문서 뷰어(`/docs/:docId?page=X`)가 열려 원문을 확인할 수 있습니다.
   * PDF/이미지 문서는 OCR/표 추출이 완료된 후 미리보기나 텍스트 탭으로 표시합니다.

5. **관리 콘솔(옵션)**

   * `/admin` 페이지에서 백엔드 `/admin/health`와 `/admin/jobs`를 호출하여 LLM, 파서, 인덱서 등의 상태와 지연 시간을 모니터링합니다.

---

## 🚀 4. 게시판 미완성 상태에서의 동작

* 게시판 모듈을 아직 완성하지 않아도 챗봇과 첨부파일 파이프라인은 독립적으로 동작합니다.
* 첨부파일 파싱/색인/검색 → LLM 생성/스트리밍 → Evidence 확인까지 기본 RAG 챗봇 시나리오를 검증한 후,
  게시판이 준비되면 Board Ingestor만 붙여 “글 + 첨부”를 색인하도록 확장하면 됩니다.
* 이렇게 하면 개발 초기에는 **단일 RAG 챗봇**으로 MVP를 빠르게 검증하고, 나중에 게시판 기능을 추가해도 큰 구조 변경 없이 확장이 가능합니다.

---
