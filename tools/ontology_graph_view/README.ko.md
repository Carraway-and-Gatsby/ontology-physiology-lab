# 온톨로지 그래프 탐색기

`site/index.html`을 파일 탐색기에서 브라우저로 열면 오프라인으로 사용할 수 있다. 검색, 관계 필터, 보기 전환, 노드/간선 선택, 확대/축소, 초기화와 JSON 내보내기를 지원한다. 선택한 노드의 직접 이웃이 강조된다. 작은 화면에서는 노드 목록과 가로 스크롤로 접근할 수 있다.

재생성 (표준 라이브러리만 필요):

```sh
python build_graph.py --input-dir inputs --output-dir site
```

입력은 `inputs/anatomy_nodes_v2.json`, `inputs/applied_sidecar.json`, `inputs/m1_manifest.json`, 영수증은 `input-sha256.json`이다. 프로젝트 원본 리비전은 `680bd29650d97957256dd05fd3281ee8403f6aed`; 각 검사 항목에서 원본 레코드 및 JSON 위치를 확인할 수 있다. 이는 기존 기록의 읽기 전용 투영이며 새로운 매핑 검증이 아니다.

입력 생성: `anatomy_nodes_v2.json`은 `src/physiosim/ontology/anatomy_nodes_v2.json`의 복사본, `applied_sidecar.json`은 `build_applied_sidecar()` 결과(applied 데모의 `applied_sidecar.json`과 같은 직렬화), `m1_manifest.json`은 `scripts/run_four_chamber_m1.py` 출력의 `manifest.json`이다. [redacted: host] 초안은 `6f684b8` 기준 입력을 썼고, PR #4가 `anatomy_nodes_v2.json`의 `status` 문장을 고친 뒤 위 리비전에서 세 파일을 다시 생성했다(바뀐 것은 그 문장과 그에 따른 해시뿐이다). `m1_manifest.json`의 `run` 부분은 실행 환경의 의존성 버전과 출력 해시를 담으므로 실행한 컴퓨터마다 다르며, 그래프가 쓰는 `semantic_contract`는 같은 리비전에서 결정적으로 생성된다.

배치: 간선의 대상 노드를 출발 노드보다 위에 두는 계층 배치다(전체 위에 부분, 의존 대상 위에 입력). 화면 정렬용일 뿐 새로운 관계나 순서를 뜻하지 않는다. 순환하는 의존성(예: `Q_mitral` → `V_la` → `P_la` → `Q_mitral`)은 배치 계산에서만 한 간선을 뒤집고, 화면에는 원래 방향으로 그린다. 여러 층을 건너는 간선은 각 층에 꺾임점을 두어 다른 노드를 피해 간다. 간선 레이블은 다른 노드와 레이블을 가리지 않는 위치에 놓고, 그런 위치가 없으면 숨겼다가 간선에 마우스를 올리거나 선택하면 보인다. 레이블은 predicate IRI의 마지막 부분을 그대로 쓴다(예: `BFO_0000050`); 프로젝트 문서가 `RO_0002572`를 해석 없이 IRI로 유지하므로 사람이 읽는 이름을 덧붙이지 않았다. 해당 보기에서 간선이 없는 노드는 그래프 아래 별도 묶음에 놓고, 카탈로그는 `node_class`별로 묶는다.

검사: `tests/test_graph.py`는 데이터 투영, `tests/test_layout.py`는 node로 배치를 실행해 간선이 다른 노드를 지나지 않음, 노드·레이블 겹침 없음, 간선이 출발 노드에서 대상 노드로 이어짐, 원본 주장 보기의 교차 0개와 결정성을 확인한다. `tests/test_layout.py`에는 `node`가 필요하다.

실선 화살표는 원본 sourceTemplate → targetTemplate 주장과 원본 predicate다. 원본 ACCEPT/REVIEW는 대상 매핑 승인이 아니다. 점선은 모델 역할, 포트 참조, 의존성이며 의존성은 on → dependent이다. 해부학 관계나 수치 연결로 해석하지 않는다. 카탈로그에는 구조 간선이 없으며 31개 항목은 전체 Uberon/FMA나 OWL 추론 결과가 아니다. `role_in_smith`는 참조 모델 역할이며 M1 고유 기능의 증거가 아니다.

대상 crosswalk는 PROPOSED, 외부 수치 사용은 NONE, G3는 CLOSED다. C5는 USER_DECISION_RUNTIME_DEFERRED 및 applied false이고 기계적 bearer는 선택되지 않았다. 승모판 REVIEW/REVISE와 DRAFT 경계를 유지한다. 법칙/버전 계약 선언은 수치 무결성 증명이 아니다. 원문, 추출 사실, 해석 및 미결 충돌은 범위와 검사 패널의 원본 필드로 구분한다. 이 뷰어는 3D 형상, 시뮬레이션 또는 추론 검증을 제공하지 않는다.
